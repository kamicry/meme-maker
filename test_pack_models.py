#!/usr/bin/env python3
"""
Tests for sticker pack models and data validation.
Tests manifest and config model serialization and validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from meme_stickers.sticker_pack import (
    FileSource,
    StickerInfo,
    GridSettings,
    PackManifest,
    PackConfig,
    HubPackInfo,
)


def test_file_source_enum():
    """Test FileSource enum"""
    print("=" * 60)
    print("Test: FileSource Enum")
    print("=" * 60)
    
    assert FileSource.LOCAL.value == "local"
    assert FileSource.REMOTE.value == "remote"
    assert FileSource.BUILTIN.value == "builtin"
    
    # Test creating from string
    source = FileSource("local")
    assert source == FileSource.LOCAL
    
    print("✓ FileSource enum works correctly")


def test_sticker_info_model():
    """Test StickerInfo model"""
    print("=" * 60)
    print("Test: StickerInfo Model")
    print("=" * 60)
    
    sticker = StickerInfo(
        name="test_sticker",
        path="stickers/test_sticker.png",
        file_source=FileSource.LOCAL,
        created_at="2024-01-01T00:00:00",
    )
    
    assert sticker.name == "test_sticker"
    assert sticker.path == "stickers/test_sticker.png"
    assert sticker.file_source == FileSource.LOCAL
    assert sticker.created_at == "2024-01-01T00:00:00"
    
    print("✓ StickerInfo model works correctly")


def test_grid_settings_model():
    """Test GridSettings model"""
    print("=" * 60)
    print("Test: GridSettings Model")
    print("=" * 60)
    
    # Default values
    grid = GridSettings()
    assert grid.columns == 3
    assert grid.rows == 3
    assert grid.cell_width == 200
    assert grid.cell_height == 200
    assert grid.background_color == "#FFFFFF"
    assert grid.border_color == "#000000"
    assert grid.border_width == 1
    
    # Custom values
    grid_custom = GridSettings(
        columns=4,
        rows=2,
        cell_width=300,
        cell_height=250,
        background_color="#000000",
        border_color="#FFFFFF",
        border_width=2,
    )
    
    assert grid_custom.columns == 4
    assert grid_custom.rows == 2
    assert grid_custom.cell_width == 300
    
    print("✓ GridSettings model works correctly")


def test_pack_manifest_basic():
    """Test PackManifest basic creation and validation"""
    print("=" * 60)
    print("Test: PackManifest Basic")
    print("=" * 60)
    
    manifest_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "A test pack",
        "version": "1.0.0",
        "author": "Test Author",
        "enabled": True,
        "url": "https://example.com/test_pack.zip",
        "checksum": "abc123def456",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-02T00:00:00",
        "stickers": [],
    }
    
    manifest = PackManifest.from_dict(manifest_data)
    
    assert manifest.name == "test_pack"
    assert manifest.display_name == "Test Pack"
    assert manifest.description == "A test pack"
    assert manifest.version == "1.0.0"
    assert manifest.author == "Test Author"
    assert manifest.enabled is True
    assert manifest.url == "https://example.com/test_pack.zip"
    assert manifest.checksum == "abc123def456"
    
    print("✓ PackManifest creation and validation works")


def test_pack_manifest_serialization():
    """Test PackManifest serialization round-trip"""
    print("=" * 60)
    print("Test: PackManifest Serialization")
    print("=" * 60)
    
    original_data = {
        "name": "pack1",
        "display_name": "Pack 1",
        "description": "First pack",
        "version": "2.0.0",
        "author": "Author 1",
        "enabled": True,
        "url": "https://example.com/pack1.zip",
        "checksum": "checksum1",
        "stickers": [
            {
                "name": "sticker1",
                "path": "stickers/sticker1.png",
                "file_source": "local",
                "created_at": "2024-01-01T00:00:00",
            }
        ],
    }
    
    # Create from dict
    manifest = PackManifest.from_dict(original_data)
    
    # Convert back to dict
    output_data = manifest.to_dict()
    
    # Verify key fields
    assert output_data["name"] == "pack1"
    assert output_data["display_name"] == "Pack 1"
    assert output_data["version"] == "2.0.0"
    assert len(output_data["stickers"]) == 1
    assert output_data["stickers"][0]["name"] == "sticker1"
    
    print("✓ PackManifest serialization round-trip successful")


def test_pack_manifest_with_stickers():
    """Test PackManifest with multiple stickers"""
    print("=" * 60)
    print("Test: PackManifest With Stickers")
    print("=" * 60)
    
    manifest_data = {
        "name": "sticker_pack",
        "display_name": "Sticker Pack",
        "description": "Pack with stickers",
        "version": "1.0.0",
        "author": "Author",
        "enabled": True,
        "stickers": [
            {
                "name": "smile",
                "path": "stickers/smile.png",
                "file_source": "local",
            },
            {
                "name": "cry",
                "path": "stickers/cry.png",
                "file_source": "local",
            },
            {
                "name": "laugh",
                "path": "stickers/laugh.png",
                "file_source": "local",
            },
        ],
    }
    
    manifest = PackManifest.from_dict(manifest_data)
    
    assert len(manifest.stickers) == 3
    assert manifest.stickers[0].name == "smile"
    assert manifest.stickers[1].name == "cry"
    assert manifest.stickers[2].name == "laugh"
    
    print("✓ PackManifest with multiple stickers works")


def test_pack_config_basic():
    """Test PackConfig basic creation"""
    print("=" * 60)
    print("Test: PackConfig Basic")
    print("=" * 60)
    
    config_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "A test pack",
        "enabled": True,
        "shortcuts": [
            {"name": "cmd1", "enabled": True},
            {"name": "cmd2", "enabled": False},
        ],
    }
    
    config = PackConfig.from_dict(config_data)
    
    assert config.name == "test_pack"
    assert config.display_name == "Test Pack"
    assert config.enabled is True
    assert len(config.shortcuts) == 2
    
    print("✓ PackConfig creation works")


def test_pack_config_with_grid_settings():
    """Test PackConfig with grid settings"""
    print("=" * 60)
    print("Test: PackConfig With Grid Settings")
    print("=" * 60)
    
    config_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "A test pack",
        "enabled": True,
        "grid_settings": {
            "columns": 4,
            "rows": 3,
            "cell_width": 300,
            "cell_height": 250,
            "background_color": "#F0F0F0",
            "border_color": "#333333",
            "border_width": 2,
        },
    }
    
    config = PackConfig.from_dict(config_data)
    
    assert config.grid_settings is not None
    assert config.grid_settings.columns == 4
    assert config.grid_settings.rows == 3
    assert config.grid_settings.cell_width == 300
    assert config.grid_settings.background_color == "#F0F0F0"
    
    print("✓ PackConfig with grid settings works")


def test_pack_config_serialization():
    """Test PackConfig serialization"""
    print("=" * 60)
    print("Test: PackConfig Serialization")
    print("=" * 60)
    
    config_data = {
        "name": "test_pack",
        "display_name": "Test Pack",
        "description": "Description",
        "enabled": True,
        "grid_settings": {
            "columns": 3,
            "rows": 2,
        },
    }
    
    config = PackConfig.from_dict(config_data)
    output_data = config.to_dict()
    
    assert output_data["name"] == "test_pack"
    assert output_data["grid_settings"]["columns"] == 3
    assert output_data["grid_settings"]["rows"] == 2
    
    print("✓ PackConfig serialization works")


def test_hub_pack_info_basic():
    """Test HubPackInfo basic creation"""
    print("=" * 60)
    print("Test: HubPackInfo Basic")
    print("=" * 60)
    
    hub_pack_data = {
        "name": "online_pack",
        "display_name": "Online Pack",
        "description": "A pack from hub",
        "url": "https://example.com/online_pack.zip",
        "version": "1.5.0",
        "author": "Hub Author",
        "size": 2048576,
        "preview_url": "https://example.com/preview.jpg",
        "downloads": 1250,
        "checksum": "hub_checksum",
    }
    
    hub_pack = HubPackInfo.from_dict(hub_pack_data)
    
    assert hub_pack.name == "online_pack"
    assert hub_pack.display_name == "Online Pack"
    assert hub_pack.url == "https://example.com/online_pack.zip"
    assert hub_pack.size == 2048576
    assert hub_pack.downloads == 1250
    
    print("✓ HubPackInfo creation works")


def test_hub_pack_info_serialization():
    """Test HubPackInfo serialization"""
    print("=" * 60)
    print("Test: HubPackInfo Serialization")
    print("=" * 60)
    
    hub_pack_data = {
        "name": "pack1",
        "display_name": "Pack 1",
        "description": "First pack",
        "url": "https://example.com/pack1.zip",
        "version": "1.0.0",
        "author": "Author 1",
        "size": 1024000,
    }
    
    hub_pack = HubPackInfo.from_dict(hub_pack_data)
    output_data = hub_pack.to_dict()
    
    assert output_data["name"] == "pack1"
    assert output_data["url"] == "https://example.com/pack1.zip"
    assert output_data["size"] == 1024000
    
    print("✓ HubPackInfo serialization works")


def test_model_field_defaults():
    """Test that model fields have correct defaults"""
    print("=" * 60)
    print("Test: Model Field Defaults")
    print("=" * 60)
    
    # PackManifest with minimal data
    manifest = PackManifest.from_dict({
        "name": "minimal",
        "display_name": "Minimal",
        "description": "Minimal pack",
        "version": "1.0.0",
        "author": "Author",
    })
    
    assert manifest.enabled is True
    assert manifest.url is None
    assert manifest.checksum is None
    assert len(manifest.stickers) == 0
    
    print("✓ Model field defaults work correctly")


def test_edge_cases():
    """Test edge cases in model handling"""
    print("=" * 60)
    print("Test: Edge Cases")
    print("=" * 60)
    
    # Empty sticker list
    manifest = PackManifest.from_dict({
        "name": "empty",
        "display_name": "Empty",
        "description": "Empty stickers",
        "version": "1.0.0",
        "author": "Author",
        "stickers": [],
    })
    assert len(manifest.stickers) == 0
    
    # Missing optional fields
    config = PackConfig.from_dict({
        "name": "minimal_config",
        "display_name": "Minimal Config",
        "description": "Minimal",
    })
    assert config.enabled is True
    assert config.grid_settings is None
    
    print("✓ Edge cases handled correctly")


def run_all_tests():
    """Run all model tests"""
    print("\n" + "=" * 60)
    print("STICKER PACK MODELS TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("FileSource Enum", test_file_source_enum),
        ("StickerInfo Model", test_sticker_info_model),
        ("GridSettings Model", test_grid_settings_model),
        ("PackManifest Basic", test_pack_manifest_basic),
        ("PackManifest Serialization", test_pack_manifest_serialization),
        ("PackManifest With Stickers", test_pack_manifest_with_stickers),
        ("PackConfig Basic", test_pack_config_basic),
        ("PackConfig With Grid Settings", test_pack_config_with_grid_settings),
        ("PackConfig Serialization", test_pack_config_serialization),
        ("HubPackInfo Basic", test_hub_pack_info_basic),
        ("HubPackInfo Serialization", test_hub_pack_info_serialization),
        ("Model Field Defaults", test_model_field_defaults),
        ("Edge Cases", test_edge_cases),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
