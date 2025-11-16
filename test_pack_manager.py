#!/usr/bin/env python3
"""
Integration tests for sticker pack manager.
Tests loading, installing, updating, and deleting packs using temporary directories.
"""

import sys
import asyncio
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Add meme_stickers to path
sys.path.insert(0, str(Path(__file__).parent))

from meme_stickers.sticker_pack import (
    StickerPackManager,
    PackManifest,
    PackConfig,
    HubPackInfo,
    PackState,
    PackEvent,
    Pack,
)


def create_test_manifest(
    name: str = "test_pack",
    display_name: str = "Test Pack",
    description: str = "A test pack",
    version: str = "1.0.0",
    author: str = "Test Author",
    enabled: bool = True,
) -> Dict[str, Any]:
    """Create a test manifest dictionary"""
    return {
        "name": name,
        "display_name": display_name,
        "description": description,
        "version": version,
        "author": author,
        "enabled": enabled,
        "stickers": [],
    }


def create_test_pack_directory(
    base_dir: Path,
    pack_name: str = "test_pack",
    num_stickers: int = 3,
    manifest_data: Dict[str, Any] = None,
) -> Path:
    """
    Create a test pack directory with metadata and stickers.
    
    Args:
        base_dir: Base directory to create pack in
        pack_name: Name of the pack
        num_stickers: Number of stickers to create
        manifest_data: Override manifest data
        
    Returns:
        Path to created pack directory
    """
    pack_dir = base_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Create metadata
    manifest = manifest_data or create_test_manifest(name=pack_name)
    with open(pack_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # Create stickers directory with dummy sticker files
    stickers_dir = pack_dir / "stickers"
    stickers_dir.mkdir(exist_ok=True)
    
    for i in range(num_stickers):
        sticker_file = stickers_dir / f"sticker_{i}.png"
        sticker_file.write_bytes(b"fake image data")
    
    return pack_dir


def create_test_pack_zip(
    temp_dir: Path,
    pack_name: str = "test_pack",
    num_stickers: int = 3,
) -> Path:
    """
    Create a test pack as a zip file.
    
    Args:
        temp_dir: Directory to create zip in
        pack_name: Name of the pack
        num_stickers: Number of stickers
        
    Returns:
        Path to created zip file
    """
    # Create pack directory
    pack_dir = create_test_pack_directory(
        temp_dir,
        pack_name,
        num_stickers,
    )
    
    # Create zip file
    zip_path = temp_dir / f"{pack_name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file_path in pack_dir.rglob("*"):
            if file_path.is_file():
                arc_name = file_path.relative_to(temp_dir)
                zf.write(file_path, arc_name)
    
    # Clean up directory
    import shutil
    shutil.rmtree(pack_dir)
    
    return zip_path


class MockHubClient:
    """Mock hub client for testing"""
    
    def __init__(self):
        self.packs: Dict[str, HubPackInfo] = {}
        self.should_fail = False
    
    async def fetch_packs(self, force_refresh: bool = False) -> List[HubPackInfo]:
        if self.should_fail:
            raise Exception("Hub fetch failed")
        return list(self.packs.values())
    
    async def fetch_pack_info(self, pack_name: str, force_refresh: bool = False):
        if self.should_fail:
            raise Exception("Hub fetch failed")
        return self.packs.get(pack_name)
    
    async def download_pack(self, url: str, output_path: str) -> str:
        # Copy test zip if available
        if Path(url).exists():
            import shutil
            shutil.copy(url, output_path)
        return output_path
    
    def calculate_checksum(self, file_path: str, algorithm: str = "md5") -> str:
        return "test_checksum"
    
    def clear_cache(self) -> None:
        pass


async def test_pack_loading():
    """Test loading packs from disk"""
    print("=" * 60)
    print("Test: Pack Loading")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test packs
        pack1_dir = create_test_pack_directory(temp_path / "packs", "pack1", 3)
        pack2_dir = create_test_pack_directory(temp_path / "packs", "pack2", 2)
        
        # Create manager
        manager = StickerPackManager(temp_path)
        
        # Reload packs
        await manager.reload()
        
        # Verify packs loaded
        packs = manager.list_packs()
        assert len(packs) == 2, f"Expected 2 packs, got {len(packs)}"
        assert "pack1" in packs, "pack1 not found"
        assert "pack2" in packs, "pack2 not found"
        
        # Verify manifests
        manifest1 = manager.get_manifest("pack1")
        assert manifest1 is not None, "manifest1 not found"
        assert manifest1.name == "pack1", f"Expected pack1, got {manifest1.name}"
        assert len(manifest1.stickers) == 3, f"Expected 3 stickers, got {len(manifest1.stickers)}"
        
        print("✓ Packs loaded successfully")
        print(f"  - Found {len(packs)} packs: {', '.join(packs)}")
        print(f"  - pack1: {len(manifest1.stickers)} stickers")


async def test_pack_validation():
    """Test pack validation"""
    print("=" * 60)
    print("Test: Pack Validation")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Valid pack
        pack_dir = create_test_pack_directory(temp_path, "valid_pack", 2)
        pack = Pack(pack_dir)
        is_valid = await pack.validate()
        assert is_valid, "Valid pack failed validation"
        print("✓ Valid pack passed validation")
        
        # Invalid pack (no stickers)
        invalid_dir = temp_path / "invalid_pack"
        invalid_dir.mkdir()
        (invalid_dir / "metadata.json").write_text(
            json.dumps(create_test_manifest(name="invalid_pack"))
        )
        
        invalid_pack = Pack(invalid_dir)
        is_valid = await invalid_pack.validate()
        assert not is_valid, "Invalid pack passed validation"
        print("✓ Invalid pack failed validation as expected")


async def test_pack_event_callbacks():
    """Test pack state change callbacks"""
    print("=" * 60)
    print("Test: Pack Event Callbacks")
    print("=" * 60)
    
    events_captured = []
    
    def capture_event(event: PackEvent):
        events_captured.append(event)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create manager and register callback
        manager = StickerPackManager(temp_path)
        manager.on_pack_state_change(capture_event)
        
        # Create test pack
        create_test_pack_directory(temp_path / "packs", "test_pack", 2)
        
        # Reload packs (should trigger events)
        await manager.reload()
        
        # Verify events were captured
        assert len(events_captured) > 0, "No events captured"
        
        # Check for LOADING and LOADED events
        states = [e.state for e in events_captured]
        assert PackState.LOADING in states, "LOADING event not found"
        assert PackState.LOADED in states, "LOADED event not found"
        
        print("✓ Pack events captured successfully")
        print(f"  - Total events: {len(events_captured)}")
        print(f"  - Event states: {set(s.value for s in states)}")


async def test_manifest_serialization():
    """Test manifest serialization and deserialization"""
    print("=" * 60)
    print("Test: Manifest Serialization")
    print("=" * 60)
    
    # Create manifest
    manifest_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "A test pack",
        "version": "1.2.3",
        "author": "Test Author",
        "enabled": True,
        "url": "https://example.com/test_pack.zip",
        "checksum": "abc123def456",
        "stickers": [
            {
                "name": "sticker1",
                "path": "stickers/sticker1.png",
                "file_source": "local",
            }
        ],
    }
    
    # Create from dict
    manifest = PackManifest.from_dict(manifest_data)
    assert manifest.name == "test_pack", "Name mismatch"
    assert manifest.version == "1.2.3", "Version mismatch"
    assert len(manifest.stickers) == 1, "Sticker count mismatch"
    
    print("✓ Manifest deserialization successful")
    
    # Convert back to dict
    output_data = manifest.to_dict()
    assert output_data["name"] == "test_pack", "Round-trip name mismatch"
    assert output_data["version"] == "1.2.3", "Round-trip version mismatch"
    
    print("✓ Manifest serialization successful")


async def test_config_serialization():
    """Test config serialization"""
    print("=" * 60)
    print("Test: Config Serialization")
    print("=" * 60)
    
    config_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "A test pack",
        "enabled": True,
        "shortcuts": [
            {"name": "cmd1", "enabled": True}
        ],
        "grid_settings": {
            "columns": 4,
            "rows": 3,
            "cell_width": 250,
        },
    }
    
    config = PackConfig.from_dict(config_data)
    assert config.name == "test_pack"
    assert config.grid_settings is not None
    assert config.grid_settings.columns == 4
    
    print("✓ Config deserialization successful")
    
    output_data = config.to_dict()
    assert output_data["grid_settings"]["columns"] == 4
    
    print("✓ Config serialization successful")


async def test_install_pack():
    """Test pack installation"""
    print("=" * 60)
    print("Test: Pack Installation")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create manager
            manager = StickerPackManager(temp_path)
            
            # Create test zip
            pack_zip = create_test_pack_zip(temp_path, "new_pack", 3)
            
            # Create hub pack info
            hub_pack = HubPackInfo(
                name="new_pack",
                display_name="New Pack",
                description="A new pack",
                url=str(pack_zip),
                version="1.0.0",
                author="Test",
            )
            
            # Mock the downloader to use the actual file
            async def mock_download(url, output_path):
                import shutil
                shutil.copy(url, output_path)
                return output_path
            
            manager.hub_client.download_pack = mock_download
            
            # Install pack
            await manager.install_pack(hub_pack)
            
            # Verify pack installed
            packs = manager.list_packs()
            assert "new_pack" in packs, "Pack not installed"
            
            manifest = manager.get_manifest("new_pack")
            assert manifest is not None, "Manifest not found"
            assert manifest.name == "new_pack"
            assert len(manifest.stickers) == 3
            
            print("✓ Pack installed successfully")
        except Exception as e:
            import traceback
            print(f"✗ Install failed: {e}")
            traceback.print_exc()
            raise


async def test_delete_pack():
    """Test pack deletion"""
    print("=" * 60)
    print("Test: Pack Deletion")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create initial pack
        create_test_pack_directory(temp_path / "packs", "delete_me", 2)
        
        # Create manager and load
        manager = StickerPackManager(temp_path)
        await manager.reload()
        
        # Verify pack exists
        assert "delete_me" in manager.list_packs()
        
        # Delete pack
        await manager.delete_pack("delete_me")
        
        # Verify pack deleted
        assert "delete_me" not in manager.list_packs()
        assert not (temp_path / "packs" / "delete_me").exists()
        
        print("✓ Pack deleted successfully")


async def test_hub_pack_listing():
    """Test fetching packs from hub"""
    print("=" * 60)
    print("Test: Hub Pack Listing")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create manager
        manager = StickerPackManager(temp_path)
        
        # Mock hub client
        hub_packs = [
            HubPackInfo(
                name="pack1",
                display_name="Pack 1",
                description="First pack",
                url="https://example.com/pack1.zip",
                version="1.0.0",
                author="Author 1",
            ),
            HubPackInfo(
                name="pack2",
                display_name="Pack 2",
                description="Second pack",
                url="https://example.com/pack2.zip",
                version="2.0.0",
                author="Author 2",
            ),
        ]
        
        manager.hub_client.fetch_packs = AsyncMock(return_value=hub_packs)
        
        # Fetch packs
        packs = await manager.fetch_hub_packs()
        
        assert len(packs) == 2, f"Expected 2 packs, got {len(packs)}"
        assert packs[0].name == "pack1"
        assert packs[1].name == "pack2"
        
        print("✓ Hub packs fetched successfully")
        print(f"  - Found {len(packs)} packs")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PACK MANAGER INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("Manifest Serialization", test_manifest_serialization),
        ("Config Serialization", test_config_serialization),
        ("Pack Validation", test_pack_validation),
        ("Pack Loading", test_pack_loading),
        ("Pack Event Callbacks", test_pack_event_callbacks),
        ("Hub Pack Listing", test_hub_pack_listing),
        ("Pack Installation", test_install_pack),
        ("Pack Deletion", test_delete_pack),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    # Summary
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
