#!/usr/bin/env python3
"""
Test script to verify async generator handlers work correctly
"""

import asyncio
from unittest.mock import Mock
from main import MemeStickersPlugin


class MockContext:
    """Mock AstrBot context"""
    def __init__(self):
        self.data_path = "test_data"
    
    def get_data_path(self):
        return self.data_path


class MockAstrBotConfig:
    """Mock AstrBot configuration"""
    pass


class MockEvent:
    """Mock AstrBot message event"""
    def __init__(self, message_str):
        self.message_str = message_str
    
    def plain_result(self, text):
        """Return plain text result"""
        return {"type": "plain", "content": text}


async def test_list_command():
    """Test /meme list command (async generator)"""
    print("Testing /meme list command...")
    
    context = MockContext()
    config = MockAstrBotConfig()
    plugin = MemeStickersPlugin(context, config)
    
    # Initialize plugin
    await plugin.initialize()
    
    # Create event
    event = MockEvent("/meme list")
    
    # Test async generator iteration
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
        print(f"  Got result: {result['type']}")
    
    assert len(results) > 0, "Expected at least one result"
    print(f"✅ /meme list returned {len(results)} result(s)")
    return True


async def test_status_command():
    """Test /meme status command (async generator)"""
    print("\nTesting /meme status command...")
    
    context = MockContext()
    config = MockAstrBotConfig()
    plugin = MemeStickersPlugin(context, config)
    
    # Initialize plugin
    await plugin.initialize()
    
    # Create event
    event = MockEvent("/meme status")
    
    # Test async generator iteration
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
        print(f"  Got result: {result['type']}")
    
    assert len(results) > 0, "Expected at least one result"
    print(f"✅ /meme status returned {len(results)} result(s)")
    return True


async def test_help_command():
    """Test /meme help command"""
    print("\nTesting /meme help command...")
    
    context = MockContext()
    config = MockAstrBotConfig()
    plugin = MemeStickersPlugin(context, config)
    
    # Initialize plugin
    await plugin.initialize()
    
    # Create event
    event = MockEvent("/meme help")
    
    # Test async generator iteration
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
        print(f"  Got result: {result['type']}")
    
    assert len(results) > 0, "Expected at least one result"
    print(f"✅ /meme help returned {len(results)} result(s)")
    return True


async def test_no_subcommand():
    """Test /meme without subcommand"""
    print("\nTesting /meme without subcommand...")
    
    context = MockContext()
    config = MockAstrBotConfig()
    plugin = MemeStickersPlugin(context, config)
    
    # Initialize plugin
    await plugin.initialize()
    
    # Create event
    event = MockEvent("/meme")
    
    # Test async generator iteration
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
        print(f"  Got result: {result['type']}")
    
    assert len(results) > 0, "Expected at least one result"
    print(f"✅ /meme returned {len(results)} result(s)")
    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Async Generator Handlers Fix")
    print("=" * 60)
    
    try:
        await test_list_command()
        await test_status_command()
        await test_help_command()
        await test_no_subcommand()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
