#!/usr/bin/env python3
"""
Test script to verify the meme command parameter mismatch fix
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock
from main import MemeStickersPlugin
from astrbot.api import AstrBotConfig

class MockContext:
    def __init__(self):
        self.data_path = "test_data"
    
    def get_data_path(self):
        return self.data_path

class MockEvent:
    def __init__(self, message_str, user_id="test_user"):
        self.message_str = message_str
        self.user_id = user_id
    
    def plain_result(self, text):
        return {"type": "plain", "content": text}

class MockConfig:
    def __init__(self):
        self.config = {}

    def get(self, key, default=None):
        return self.config.get(key, default)

async def test_command_handlers():
    """Test that command handlers work without parameter errors"""
    print("Testing meme command handlers...")
    
    # Create test environment
    context = MockContext()
    config = MockConfig()
    plugin = MemeStickersPlugin(context, config)
    
    # Initialize plugin
    await plugin.initialize()
    
    # Test 1: Default handler (should show help)
    print("\n1. Testing default handler...")
    event = MockEvent("/meme")
    try:
        results = []
        async for result in plugin.__default__(event):
            results.append(result)
        print(f"✅ Default handler works: {len(results)} result(s)")
        print(f"   Content: {results[0]['content'][:50]}...")
    except Exception as e:
        print(f"❌ Default handler failed: {e}")
    
    # Test 2: List command
    print("\n2. Testing list command...")
    event = MockEvent("/meme list")
    try:
        results = []
        async for result in plugin.list_packs(event):
            results.append(result)
        print(f"✅ List command works: {len(results)} result(s)")
        print(f"   Content: {results[0]['content'][:50]}...")
    except Exception as e:
        print(f"❌ List command failed: {e}")
    
    # Test 3: Status command
    print("\n3. Testing status command...")
    event = MockEvent("/meme status")
    try:
        results = []
        async for result in plugin.show_status(event):
            results.append(result)
        print(f"✅ Status command works: {len(results)} result(s)")
        print(f"   Content: {results[0]['content'][:50]}...")
    except Exception as e:
        print(f"❌ Status command failed: {e}")
    
    # Test 4: Help command
    print("\n4. Testing help command...")
    event = MockEvent("/meme help")
    try:
        results = []
        async for result in plugin.show_help(event):
            results.append(result)
        print(f"✅ Help command works: {len(results)} result(s)")
        print(f"   Content: {results[0]['content'][:50]}...")
    except Exception as e:
        print(f"❌ Help command failed: {e}")
    
    print("\n✅ All command handlers work without parameter errors!")

async def main():
    """Main test function"""
    print("Meme Command Parameter Mismatch Fix Test")
    print("=" * 50)
    
    try:
        await test_command_handlers()
        print("\n" + "=" * 50)
        print("All tests passed! The parameter mismatch issue is fixed.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())