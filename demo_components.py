#!/usr/bin/env python3
"""
Demonstration script showing how ConfigWrapper and StickerPackManager work.
This script demonstrates the core components without requiring AstrBot runtime.
"""

import sys
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

# Mock astrbot modules
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

from main import ConfigWrapper, StickerPackManager, StickerPackMetadata


class FakeAstrBotConfig:
    """Minimal fake AstrBot config"""
    def __init__(self):
        self.data = {}


def create_demo_pack(base_dir: Path, pack_name: str, stickers: list):
    """Create a demo sticker pack"""
    pack_dir = base_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "name": pack_name,
        "display_name": f"Demo {pack_name.title()} Pack",
        "description": f"A demo pack with {len(stickers)} stickers",
        "version": "1.0.0",
        "author": "Demo Author",
        "enabled": True
    }
    
    with open(pack_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
        
    stickers_dir = pack_dir / "stickers"
    stickers_dir.mkdir(exist_ok=True)
    
    for sticker_name in stickers:
        (stickers_dir / f"{sticker_name}.png").write_text(f"Demo image: {sticker_name}")
        
    return pack_dir


async def demo_config_wrapper():
    """Demonstrate ConfigWrapper usage"""
    print("\n" + "=" * 60)
    print("ConfigWrapper Demo")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "config.json"
        
        # Create config wrapper
        fake_astrbot_config = FakeAstrBotConfig()
        config = ConfigWrapper(fake_astrbot_config, "demo_plugin")
        
        print("\n1. Loading configuration (will use defaults)...")
        config.load(config_file)
        
        print(f"   - Auto-update: {config.auto_update}")
        print(f"   - Force update: {config.force_update}")
        print(f"   - Hub URL: {config.hub_url}")
        
        print("\n2. Modifying configuration...")
        config.set("auto_update", True)
        config.set("hub_url", "https://my-hub.example.com")
        
        print(f"   - Auto-update: {config.auto_update}")
        print(f"   - Hub URL: {config.hub_url}")
        
        print("\n3. Saving configuration...")
        config.save(config_file)
        print(f"   - Saved to: {config_file}")
        
        print("\n4. Reloading configuration...")
        config2 = ConfigWrapper(fake_astrbot_config, "demo_plugin")
        config2.load(config_file)
        print(f"   - Auto-update: {config2.auto_update}")
        print(f"   - Hub URL: {config2.hub_url}")
        
    print("\n✓ ConfigWrapper demo complete")


async def demo_sticker_pack_manager():
    """Demonstrate StickerPackManager usage"""
    print("\n" + "=" * 60)
    print("StickerPackManager Demo")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        packs_dir = Path(temp_dir) / "packs"
        packs_dir.mkdir()
        
        print("\n1. Creating demo sticker packs...")
        
        # Create some demo packs
        create_demo_pack(packs_dir, "animals", ["dog", "cat", "bird", "fish"])
        create_demo_pack(packs_dir, "emotions", ["happy", "sad", "angry", "love"])
        create_demo_pack(packs_dir, "memes", ["doge", "stonks", "this_is_fine"])
        
        print("   - Created 3 demo packs")
        
        print("\n2. Initializing StickerPackManager...")
        fake_config = ConfigWrapper(FakeAstrBotConfig(), "demo")
        manager = StickerPackManager(packs_dir, fake_config)
        
        print("\n3. Loading packs...")
        await manager.reload()
        
        print("\n4. Listing all packs:")
        all_packs = manager.list_packs()
        for pack in all_packs:
            print(f"   - {pack.display_name} ({pack.name})")
            print(f"     Version: {pack.version}, Author: {pack.author}")
            print(f"     Stickers: {len(pack.stickers)}")
            
        print(f"\n5. Getting specific pack...")
        animals = manager.get_pack("animals")
        if animals:
            print(f"   - Found: {animals.display_name}")
            print(f"   - Stickers in pack: {', '.join(animals.stickers)}")
            
        print("\n6. Testing auto-update...")
        await manager.start_auto_update(force=False)
        print("   - Auto-update task started")
        
        await asyncio.sleep(0.2)
        
        await manager.stop_auto_update()
        print("   - Auto-update task stopped")
        
    print("\n✓ StickerPackManager demo complete")


async def demo_integration():
    """Demonstrate ConfigWrapper + StickerPackManager integration"""
    print("\n" + "=" * 60)
    print("Integration Demo")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "plugin_data"
        packs_dir = data_dir / "packs"
        config_file = data_dir / "config.json"
        
        data_dir.mkdir()
        packs_dir.mkdir()
        
        print("\n1. Setting up configuration...")
        config = ConfigWrapper(FakeAstrBotConfig(), "integrated_demo")
        config.set("auto_update", True)
        config.set("force_update", False)
        config.set("hub_url", "https://stickers.example.com")
        config.save(config_file)
        print("   - Configuration created and saved")
        
        print("\n2. Creating sticker packs...")
        create_demo_pack(packs_dir, "pack_alpha", ["sticker1", "sticker2"])
        create_demo_pack(packs_dir, "pack_beta", ["sticker3", "sticker4", "sticker5"])
        print("   - Created 2 packs")
        
        print("\n3. Initializing manager with configuration...")
        manager = StickerPackManager(packs_dir, config)
        await manager.reload()
        
        print("\n4. Showing integrated system status:")
        print(f"   - Config auto-update: {config.auto_update}")
        print(f"   - Config hub URL: {config.hub_url}")
        print(f"   - Loaded packs: {len(manager.packs)}")
        
        print("\n5. Pack details:")
        for pack in manager.list_packs():
            status = "✓ enabled" if pack.enabled else "✗ disabled"
            print(f"   - {pack.display_name} [{status}]")
            print(f"     {len(pack.stickers)} sticker(s)")
            
        print("\n6. Testing auto-update with config...")
        if config.auto_update:
            await manager.start_auto_update(config.force_update)
            print("   - Auto-update started (respecting config)")
            await asyncio.sleep(0.1)
            await manager.stop_auto_update()
            print("   - Auto-update stopped")
        
    print("\n✓ Integration demo complete")


async def demo_simulated_plugin_lifecycle():
    """Simulate plugin initialization and termination"""
    print("\n" + "=" * 60)
    print("Simulated Plugin Lifecycle Demo")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "plugin_data"
        packs_dir = data_dir / "packs"
        config_file = data_dir / "config.json"
        
        print("\n[INITIALIZATION PHASE]")
        
        print("\n1. Creating data directories...")
        data_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)
        print(f"   - Data dir: {data_dir}")
        print(f"   - Packs dir: {packs_dir}")
        
        print("\n2. Loading configuration...")
        config = ConfigWrapper(FakeAstrBotConfig(), "lifecycle_demo")
        config.load(config_file)
        print("   - Config loaded (using defaults)")
        
        print("\n3. Creating pack manager...")
        manager = StickerPackManager(packs_dir, config)
        
        print("\n4. Reloading packs...")
        await manager.reload()
        print(f"   - Loaded {len(manager.packs)} pack(s)")
        
        print("\n5. Starting auto-update (if enabled)...")
        if config.auto_update:
            await manager.start_auto_update(config.force_update)
            print("   - Auto-update started")
        else:
            print("   - Auto-update disabled in config")
            
        print("\n[RUNNING PHASE]")
        print("   - Plugin is now running and ready to handle commands")
        await asyncio.sleep(0.1)
        
        print("\n[TERMINATION PHASE]")
        
        print("\n1. Stopping auto-update...")
        await manager.stop_auto_update()
        print("   - Auto-update stopped")
        
        print("\n2. Cleanup complete")
        
    print("\n✓ Lifecycle demo complete")


async def main():
    """Run all demonstrations"""
    print("\n" + "=" * 60)
    print("MEME STICKERS PLUGIN - COMPONENT DEMONSTRATIONS")
    print("=" * 60)
    
    try:
        await demo_config_wrapper()
        await demo_sticker_pack_manager()
        await demo_integration()
        await demo_simulated_plugin_lifecycle()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        print("\nKey Takeaways:")
        print("  1. ConfigWrapper provides convenient access to plugin settings")
        print("  2. StickerPackManager handles pack discovery and loading")
        print("  3. Both components work together seamlessly")
        print("  4. Auto-update runs in background when enabled")
        print("  5. Lifecycle hooks ensure proper initialization and cleanup")
        
        print("\nThe plugin is ready for integration with AstrBot!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
