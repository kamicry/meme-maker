#!/usr/bin/env python3
"""
测试表情包生成功能
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import MemeMakerPlugin, PackConfig, ShortcutConfig

class MockContext:
    def __init__(self):
        self.data_path = "data"
    
    def get_data_path(self):
        return self.data_path

class MockEvent:
    def __init__(self, message_str, user_id="test_user"):
        self.message_str = message_str
        self.user_id = user_id
    
    def plain_result(self, text):
        return {"type": "plain", "content": text}
    
    def image_result(self, path):
        return {"type": "image", "content": path}

async def test_generate_full_command():
    """测试完整的生成命令"""
    print("=" * 60)
    print("测试1: 完整命令 - /meme generate default doge 'Hello World'")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    event = MockEvent("/meme generate default doge 'Hello World'")
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    for result in results:
        if result['type'] == 'image':
            print(f"✅ 生成成功: {result['content']}")
            if Path(result['content']).exists():
                print(f"   文件存在，大小: {Path(result['content']).stat().st_size} 字节")
        else:
            print(f"   {result['content']}")
    
    print()

async def test_generate_with_options():
    """测试带选项的生成命令"""
    print("=" * 60)
    print("测试2: 带选项 - /meme generate default cat 'Meow!' -x 100 -y 50 -c red --stroke-color white --stroke-width 2")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    event = MockEvent("/meme generate default cat 'Meow!' -x 100 -y 50 -c red --stroke-color white --stroke-width 2")
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    for result in results:
        if result['type'] == 'image':
            print(f"✅ 生成成功: {result['content']}")
        else:
            print(f"   {result['content']}")
    
    print()

async def test_generate_interactive():
    """测试交互式生成流程"""
    print("=" * 60)
    print("测试3: 交互式流程")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 第一步：开始生成（没有参数）
    print("\n第1步: 发送 /meme generate")
    event = MockEvent("/meme generate", "interactive_user")
    async for result in plugin.meme_command(event):
        print(f"   {result['content'][:200]}...")
    
    # 第二步：选择包
    print("\n第2步: 回复 'default'")
    event = MockEvent("default", "interactive_user")
    async for result in plugin.handle_session_message(event):
        print(f"   {result['content'][:200]}...")
    
    # 第三步：选择贴纸
    print("\n第3步: 回复 'doge'")
    event = MockEvent("doge", "interactive_user")
    async for result in plugin.handle_session_message(event):
        print(f"   {result['content'][:200]}...")
    
    # 第四步：输入文本
    print("\n第4步: 回复 'Such interactive! Much wow!'")
    event = MockEvent("Such interactive! Much wow!", "interactive_user")
    results = []
    async for result in plugin.handle_session_message(event):
        results.append(result)
    
    for result in results:
        if result['type'] == 'image':
            print(f"   ✅ 生成成功: {result['content']}")
        else:
            print(f"   {result['content']}")
    
    print()

async def test_generate_exit():
    """测试退出交互流程"""
    print("=" * 60)
    print("测试4: 退出交互流程")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 第一步：开始生成
    print("\n第1步: 发送 /meme generate")
    event = MockEvent("/meme generate", "exit_user")
    async for result in plugin.meme_command(event):
        print(f"   {result['content'][:100]}...")
    
    # 第二步：退出
    print("\n第2步: 回复 'exit'")
    event = MockEvent("exit", "exit_user")
    async for result in plugin.handle_session_message(event):
        print(f"   {result['content']}")
    
    print()

async def test_relative_adjustments():
    """测试相对调整"""
    print("=" * 60)
    print("测试5: 相对调整 - /meme generate default think 'Thinking...' -x ^+50 -y ^-20")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    event = MockEvent("/meme generate default think 'Thinking...' -x ^+50 -y ^-20")
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    for result in results:
        if result['type'] == 'image':
            print(f"✅ 生成成功: {result['content']}")
        else:
            print(f"   {result['content']}")
    
    print()

async def test_alignment_options():
    """测试对齐选项"""
    print("=" * 60)
    print("测试6: 对齐选项")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    alignments = [
        ('left', 'top', 'Left-Top'),
        ('center', 'middle', 'Center-Middle'),
        ('right', 'bottom', 'Right-Bottom'),
    ]
    
    for align, valign, text in alignments:
        print(f"\n测试 {align}/{valign}:")
        event = MockEvent(f"/meme generate default cat '{text}' -a {align} -v {valign}")
        results = []
        async for result in plugin.meme_command(event):
            results.append(result)
        
        for result in results:
            if result['type'] == 'image':
                print(f"   ✅ 生成成功: {result['content']}")
    
    print()

async def test_debug_mode():
    """测试调试模式"""
    print("=" * 60)
    print("测试7: 调试模式 - /meme generate default doge 'Debug Mode' --debug")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    event = MockEvent("/meme generate default doge 'Debug Mode' --debug")
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    for result in results:
        if result['type'] == 'image':
            print(f"✅ 生成成功（调试模式）: {result['content']}")
        else:
            print(f"   {result['content']}")
    
    print()

async def test_error_handling():
    """测试错误处理"""
    print("=" * 60)
    print("测试8: 错误处理")
    print("=" * 60)
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 测试不存在的包
    print("\n测试不存在的包:")
    event = MockEvent("/meme generate nonexistent doge 'Test'")
    async for result in plugin.meme_command(event):
        print(f"   {result['content']}")
    
    # 测试不存在的贴纸
    print("\n测试不存在的贴纸:")
    event = MockEvent("/meme generate default nonexistent 'Test'")
    async for result in plugin.meme_command(event):
        print(f"   {result['content']}")
    
    print()

async def main():
    """主测试函数"""
    print("\n表情包生成功能测试")
    print("=" * 60)
    
    try:
        await test_generate_full_command()
        await test_generate_with_options()
        await test_generate_interactive()
        await test_generate_exit()
        await test_relative_adjustments()
        await test_alignment_options()
        await test_debug_mode()
        await test_error_handling()
        
        print("=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
