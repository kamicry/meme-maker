#!/usr/bin/env python3
"""
简单测试脚本，用于验证表情包管理插件的功能
"""

import asyncio
import json
from pathlib import Path
from main import MemeMakerPlugin, PackConfig, ShortcutConfig, HubPack
from unittest.mock import Mock

class MockContext:
    def __init__(self):
        self.data_path = "test_data"
    
    def get_data_path(self):
        return self.data_path

class MockEvent:
    def __init__(self, message_str, user_id="test_user", is_superuser=False):
        self.message_str = message_str
        self.user_id = user_id
        self._is_superuser = is_superuser
    
    def is_superuser(self):
        return self._is_superuser
    
    def plain_result(self, text):
        return {"type": "plain", "content": text}
    
    def image_result(self, path):
        return {"type": "image", "content": path}

async def test_basic_functionality():
    """测试基本功能"""
    print("开始测试基本功能...")
    
    # 创建测试环境
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    
    # 初始化
    await plugin.initialize()
    
    # 创建测试事件
    event = MockEvent("/meme help")
    
    # 测试帮助命令
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    print(f"帮助命令结果: {len(results)} 个回复")
    for result in results:
        print(f"  {result}")
    
    # 测试列表命令
    event = MockEvent("/meme list")
    results = []
    async for result in plugin.meme_command(event):
        results.append(result)
    
    print(f"列表命令结果: {len(results)} 个回复")
    for result in results:
        print(f"  {result['type']}: {result['content'][:100]}...")
    
    print("基本功能测试完成")

async def test_permission_system():
    """测试权限系统"""
    print("\n开始测试权限系统...")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 测试普通用户
    normal_event = MockEvent("/meme list --online", "normal_user", False)
    results = []
    async for result in plugin.meme_command(normal_event):
        results.append(result)
    
    print(f"普通用户访问在线列表: {results[0]['content']}")
    
    # 测试超级用户
    admin_event = MockEvent("/meme list --online", "admin_user", True)
    admin_event.is_superuser = lambda: True
    results = []
    async for result in plugin.meme_command(admin_event):
        results.append(result)
    
    print(f"超级用户访问在线列表: {len(results)} 个回复")
    
    print("权限系统测试完成")

async def test_session_management():
    """测试会话管理"""
    print("\n开始测试会话管理...")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 创建测试包
    test_pack = PackConfig(
        name="test_pack",
        display_name="测试表情包",
        description="用于测试的表情包",
        enabled=True,
        shortcuts=[ShortcutConfig(name="test", command="test", description="测试命令")]
    )
    plugin.packs["test_pack"] = test_pack
    
    # 测试删除确认
    admin_event = MockEvent("/meme delete test_pack", "admin_user", True)
    admin_event.is_superuser = lambda: True
    
    results = []
    async for result in plugin.meme_command(admin_event):
        results.append(result)
    
    print(f"删除确认: {results[0]['content']}")
    
    # 检查会话
    session = await plugin.get_session("admin_user")
    print(f"会话创建: {session is not None}")
    print(f"会话类型: {session.session_type if session else 'None'}")
    
    # 测试确认
    confirm_event = MockEvent("yes", "admin_user", True)
    results = []
    async for result in plugin.meme_command(confirm_event):
        results.append(result)
    
    print(f"删除结果: {results[0]['content']}")
    
    print("会话管理测试完成")

async def test_image_generation():
    """测试图片生成"""
    print("\n开始测试图片生成...")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 创建测试包
    test_packs = [
        PackConfig(
            name="pack1",
            display_name="表情包1",
            description="第一个表情包",
            enabled=True,
            shortcuts=[ShortcutConfig(name="cmd1", command="cmd1", description="命令1")]
        ),
        PackConfig(
            name="pack2",
            display_name="表情包2",
            description="第二个表情包",
            enabled=False,
            shortcuts=[ShortcutConfig(name="cmd2", command="cmd2", description="命令2")]
        )
    ]
    
    # 测试网格图片生成
    image_path = plugin.create_pack_grid_image(test_packs, "测试表情包")
    print(f"网格图片生成: {image_path}")
    if image_path and Path(image_path).exists():
        print("✅ 网格图片生成成功")
    else:
        print("❌ 网格图片生成失败")
    
    # 测试帮助图片生成
    help_path = plugin.create_help_image()
    print(f"帮助图片生成: {help_path}")
    if help_path and Path(help_path).exists():
        print("✅ 帮助图片生成成功")
    else:
        print("❌ 帮助图片生成失败")
    
    print("图片生成测试完成")

async def main():
    """主测试函数"""
    print("表情包管理插件测试开始")
    print("=" * 50)
    
    try:
        await test_basic_functionality()
        await test_permission_system()
        await test_session_management()
        await test_image_generation()
        
        print("\n" + "=" * 50)
        print("所有测试完成")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())