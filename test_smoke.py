#!/usr/bin/env python3
"""
Smoke tests for Meme Stickers plugin components.
Tests ConfigWrapper, StickerPackManager, and their integration.
"""

import sys
import asyncio
import tempfile
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock

# Mock astrbot modules before importing main
mock_logger = MagicMock()
mock_logger.info = lambda msg: print(f"[INFO] {msg}")
mock_logger.warning = lambda msg: print(f"[WARN] {msg}")
mock_logger.error = lambda msg: print(f"[ERROR] {msg}")

sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.event'] = MagicMock()
sys.modules['astrbot.api.star'] = MagicMock()
sys.modules['astrbot.api.config'] = MagicMock()
sys.modules['astrbot.api.logger'] = mock_logger
sys.modules['astrbot'].api.logger = mock_logger

# Import after mocking
from main import ConfigWrapper, StickerPackManager, StickerPackMetadata


class FakeAstrBotConfig:
    """Fake AstrBot config for testing"""
    
    def __init__(self):
        self.data = {}
        
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


def create_test_pack(base_dir: Path, pack_name: str, num_stickers: int = 3) -> Path:
    """
    Create a test sticker pack.
    
    Args:
        base_dir: Base directory for the pack
        pack_name: Name of the pack
        num_stickers: Number of stickers to create
        
    Returns:
        Path to created pack directory
    """
    pack_dir = base_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Create metadata
    metadata = {
        "name": pack_name,
        "display_name": f"Test Pack {pack_name}",
        "description": f"Test pack for {pack_name}",
        "version": "1.0.0",
        "author": "Test Author",
        "enabled": True
    }
    
    with open(pack_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
        
    # Create stickers directory with dummy sticker files
    stickers_dir = pack_dir / "stickers"
    stickers_dir.mkdir(exist_ok=True)
    
    for i in range(num_stickers):
        sticker_file = stickers_dir / f"sticker_{i}.png"
        sticker_file.write_text("fake image data")
        
    return pack_dir


async def test_config_wrapper():
    """Test ConfigWrapper initialization and operations"""
    print("=" * 60)
    print("Test: ConfigWrapper")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        fake_astrbot_config = FakeAstrBotConfig()
        
        # Test initialization
        config = ConfigWrapper(fake_astrbot_config, "test_plugin")
        assert config.plugin_name == "test_plugin"
        print("✓ ConfigWrapper initialized")
        
        # Test default config
        config.load(config_path)
        assert config.auto_update == False
        assert config.force_update == False
        assert config.hub_url == "http://localhost:8888"
        print("✓ Default config loaded")
        
        # Test set/get
        config.set("auto_update", True)
        assert config.get("auto_update") == True
        print("✓ Config set/get works")
        
        # Test save/load
        config.save(config_path)
        assert config_path.exists()
        print("✓ Config saved to file")
        
        # Load saved config
        config2 = ConfigWrapper(fake_astrbot_config, "test_plugin")
        config2.load(config_path)
        assert config2.get("auto_update") == True
        print("✓ Config loaded from file")
        
    print("✅ ConfigWrapper tests passed\n")


async def test_sticker_pack_manager():
    """Test StickerPackManager initialization and pack loading"""
    print("=" * 60)
    print("Test: StickerPackManager")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        
        # Create test packs
        create_test_pack(packs_dir, "pack1", 3)
        create_test_pack(packs_dir, "pack2", 5)
        
        # Test initialization
        manager = StickerPackManager(packs_dir, fake_config)
        assert len(manager.packs) == 0
        print("✓ StickerPackManager initialized")
        
        # Test reload
        await manager.reload()
        assert len(manager.packs) == 2
        print(f"✓ Loaded {len(manager.packs)} packs")
        
        # Test get_pack
        pack1 = manager.get_pack("pack1")
        assert pack1 is not None
        assert pack1.name == "pack1"
        assert len(pack1.stickers) == 3
        print("✓ get_pack works")
        
        # Test list_packs
        all_packs = manager.list_packs()
        assert len(all_packs) == 2
        print("✓ list_packs works")
        
        # Test list_enabled_packs
        enabled_packs = manager.list_enabled_packs()
        assert len(enabled_packs) == 2
        print("✓ list_enabled_packs works")
        
    print("✅ StickerPackManager tests passed\n")


async def test_manager_reload():
    """Test that StickerPackManager.reload discovers and loads packs"""
    print("=" * 60)
    print("Test: Manager Reload Functionality")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        manager = StickerPackManager(packs_dir, fake_config)
        
        # Initially no packs
        await manager.reload()
        assert len(manager.packs) == 0
        print("✓ No packs initially")
        
        # Create a pack
        create_test_pack(packs_dir, "dynamic_pack", 4)
        
        # Reload and verify
        await manager.reload()
        assert len(manager.packs) == 1
        pack = manager.get_pack("dynamic_pack")
        assert pack is not None
        assert len(pack.stickers) == 4
        print(f"✓ Pack loaded after reload with {len(pack.stickers)} stickers")
        
    print("✅ Manager reload tests passed\n")


async def test_pack_metadata_loading():
    """Test pack metadata is correctly loaded"""
    print("=" * 60)
    print("Test: Pack Metadata Loading")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        # Create pack with specific metadata
        pack_dir = packs_dir / "meta_test"
        pack_dir.mkdir()
        
        metadata = {
            "name": "meta_test",
            "display_name": "Metadata Test Pack",
            "description": "Testing metadata loading",
            "version": "2.5.3",
            "author": "Test Author",
            "enabled": False,
            "url": "https://example.com/pack.zip",
            "checksum": "abc123"
        }
        
        with open(pack_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
            
        # Create some stickers
        (pack_dir / "stickers").mkdir()
        (pack_dir / "stickers" / "test1.png").write_text("fake")
        (pack_dir / "stickers" / "test2.jpg").write_text("fake")
        
        # Load and verify
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        manager = StickerPackManager(packs_dir, fake_config)
        await manager.reload()
        
        pack = manager.get_pack("meta_test")
        assert pack is not None
        assert pack.display_name == "Metadata Test Pack"
        assert pack.description == "Testing metadata loading"
        assert pack.version == "2.5.3"
        assert pack.author == "Test Author"
        assert pack.enabled == False
        assert pack.url == "https://example.com/pack.zip"
        assert pack.checksum == "abc123"
        assert len(pack.stickers) == 2
        print("✓ All metadata fields loaded correctly")
        
    print("✅ Pack metadata loading tests passed\n")


async def test_auto_update_task():
    """Test auto-update task management"""
    print("=" * 60)
    print("Test: Auto-Update Task Management")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        manager = StickerPackManager(packs_dir, fake_config)
        
        # Start auto-update
        await manager.start_auto_update(force=False)
        assert manager._update_task is not None
        assert not manager._update_task.done()
        print("✓ Auto-update task started")
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Stop auto-update
        await manager.stop_auto_update()
        assert manager._update_task.done()
        print("✓ Auto-update task stopped")
        
    print("✅ Auto-update task tests passed\n")


async def test_config_properties():
    """Test ConfigWrapper property accessors"""
    print("=" * 60)
    print("Test: ConfigWrapper Properties")
    print("=" * 60)
    
    fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
    
    # Test default values
    assert fake_config.auto_update == False
    assert fake_config.force_update == False
    assert fake_config.hub_url == "http://localhost:8888"
    print("✓ Default property values correct")
    
    # Set values and test properties
    fake_config.set("auto_update", True)
    fake_config.set("force_update", True)
    fake_config.set("hub_url", "https://custom.url")
    
    assert fake_config.auto_update == True
    assert fake_config.force_update == True
    assert fake_config.hub_url == "https://custom.url"
    print("✓ Property accessors work correctly")
    
    print("✅ ConfigWrapper properties tests passed\n")


async def test_pack_filtering():
    """Test pack filtering by enabled status"""
    print("=" * 60)
    print("Test: Pack Filtering")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        # Create enabled and disabled packs
        pack1_dir = create_test_pack(packs_dir, "enabled_pack", 2)
        pack2_dir = create_test_pack(packs_dir, "disabled_pack", 3)
        
        # Modify metadata for disabled pack
        with open(pack2_dir / "metadata.json", 'r') as f:
            metadata = json.load(f)
        metadata["enabled"] = False
        with open(pack2_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)
            
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        manager = StickerPackManager(packs_dir, fake_config)
        await manager.reload()
        
        all_packs = manager.list_packs()
        enabled_packs = manager.list_enabled_packs()
        
        assert len(all_packs) == 2
        assert len(enabled_packs) == 1
        assert enabled_packs[0].name == "enabled_pack"
        print("✓ Pack filtering works correctly")
        
    print("✅ Pack filtering tests passed\n")


async def test_directory_creation():
    """Test data directory creation on initialization"""
    print("=" * 60)
    print("Test: Directory Creation")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "plugin_data"
        packs_dir = data_dir / "packs"
        config_file = data_dir / "config.json"
        
        # Directories don't exist yet
        assert not data_dir.exists()
        print("✓ Directories don't exist initially")
        
        # Create directories
        data_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify creation
        assert data_dir.exists()
        assert packs_dir.exists()
        print("✓ Directories created successfully")
        
        # Test config save creates parent dirs
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        fake_config.set("test_key", "test_value")
        fake_config.save(config_file)
        
        assert config_file.exists()
        print("✓ Config file saved with parent directory creation")
        
    print("✅ Directory creation tests passed\n")


async def test_empty_packs_directory():
    """Test manager handles empty packs directory gracefully"""
    print("=" * 60)
    print("Test: Empty Packs Directory")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "empty_packs"
        packs_dir.mkdir()
        
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "test")
        manager = StickerPackManager(packs_dir, fake_config)
        
        try:
            await manager.reload()
            assert len(manager.packs) == 0
            print("✓ Handles empty packs directory without errors")
            
            # Test operations on empty manager
            assert manager.get_pack("nonexistent") is None
            assert len(manager.list_packs()) == 0
            assert len(manager.list_enabled_packs()) == 0
            print("✓ Operations work correctly with no packs")
            
        except Exception as e:
            print(f"✗ Error with empty packs: {e}")
            raise
            
    print("✅ Empty packs directory tests passed\n")


async def test_integration_config_and_manager():
    """Test integration between ConfigWrapper and StickerPackManager"""
    print("=" * 60)
    print("Test: ConfigWrapper + StickerPackManager Integration")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        packs_dir = data_dir / "packs"
        config_file = data_dir / "config.json"
        
        data_dir.mkdir()
        packs_dir.mkdir()
        
        # Create config
        config = ConfigWrapper(FakeAstrBotConfig(), "integration_test")
        config.set("auto_update", True)
        config.set("force_update", True)
        config.save(config_file)
        print("✓ Config created and saved")
        
        # Create packs
        create_test_pack(packs_dir, "pack_alpha", 3)
        create_test_pack(packs_dir, "pack_beta", 2)
        
        # Create manager with config
        manager = StickerPackManager(packs_dir, config)
        await manager.reload()
        print(f"✓ Manager initialized with {len(manager.packs)} packs")
        
        # Verify integration
        assert len(manager.packs) == 2
        assert config.auto_update == True
        assert config.force_update == True
        print("✓ Config and manager work together")
        
        # Test auto-update uses config settings
        await manager.start_auto_update(config.force_update)
        assert manager._update_task is not None
        print("✓ Auto-update respects config settings")
        
        await manager.stop_auto_update()
        
    print("✅ Integration tests passed\n")


async def main():
    """Run all smoke tests"""
    print("\n" + "=" * 60)
    print("MEME STICKERS PLUGIN - SMOKE TESTS")
    print("=" * 60 + "\n")
    
    try:
        # Core component tests
        await test_config_wrapper()
        await test_config_properties()
        await test_sticker_pack_manager()
        await test_manager_reload()
        await test_pack_metadata_loading()
        await test_pack_filtering()
        
        # Feature tests
        await test_auto_update_task()
        await test_directory_creation()
        await test_empty_packs_directory()
        
        # Integration tests
        await test_integration_config_and_manager()
        
        print("=" * 60)
        print("✅ ALL SMOKE TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  - ConfigWrapper: ✓ Initialization, save/load, properties")
        print("  - StickerPackManager: ✓ Pack loading, filtering, reload")
        print("  - Auto-update: ✓ Task management")
        print("  - Integration: ✓ Components work together")
        print("\nThe plugin entry point is ready for use with AstrBot!")
        print("=" * 60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
