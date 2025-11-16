#!/usr/bin/env python3
"""
表情包管理插件功能演示脚本
展示所有已实现的功能特性
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from main import MemeMakerPlugin, PackConfig, ShortcutConfig

class MockContext:
    def __init__(self):
        self.data_path = "demo_data"
    
    def get_data_path(self):
        return self.data_path

class MockEvent:
    def __init__(self, message_str, user_id="demo_user", is_superuser=False):
        self.message_str = message_str
        self.user_id = user_id
        self._is_superuser = is_superuser
        self.sender = MockSender()
    
    def is_superuser(self):
        return self._is_superuser
    
    def plain_result(self, text):
        return {"type": "plain", "content": text}
    
    def image_result(self, path):
        return {"type": "image", "content": path}

class MockSender:
    def __init__(self):
        self.role = "user"

def print_separator(title):
    """打印分隔符"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

async def demo_basic_commands():
    """演示基本命令"""
    print_separator("基本命令演示")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 添加一些测试包
    plugin.packs["default"] = PackConfig(
        name="default",
        display_name="默认表情包",
        description="系统默认表情包",
        enabled=True,
        shortcuts=[
            ShortcutConfig(name="doge", command="doge", description="Doge表情"),
            ShortcutConfig(name="cat", command="cat", description="猫咪表情")
        ]
    )
    
    plugin.packs["anime"] = PackConfig(
        name="anime",
        display_name="动漫表情包",
        description="动漫风格表情包",
        enabled=False,
        shortcuts=[
            ShortcutConfig(name="anime1", command="anime1", description="动漫表情1")
        ]
    )
    
    # 演示帮助命令
    print("1. 帮助命令 (/meme help)")
    event = MockEvent("/meme help")
    async for result in plugin.meme_command(event):
        if result["type"] == "plain":
            print(f"   文字回复: {result['content'][:100]}...")
        else:
            print(f"   图片回复: {result['content']}")
    
    # 演示列表命令
    print("\n2. 本地列表命令 (/meme list)")
    event = MockEvent("/meme list")
    async for result in plugin.meme_command(event):
        if result["type"] == "plain":
            print(f"   文字回复: {result['content'][:200]}...")
        else:
            print(f"   图片回复: {result['content']}")
    
    # 演示启用/禁用命令
    print("\n3. 启用表情包 (/meme enable anime)")
    event = MockEvent("/meme enable anime")
    async for result in plugin.meme_command(event):
        print(f"   回复: {result['content']}")
    
    print("\n4. 禁用表情包 (/meme disable default)")
    event = MockEvent("/meme disable default")
    async for result in plugin.meme_command(event):
        print(f"   回复: {result['content']}")
    
    # 演示状态命令
    print("\n5. 状态命令 (/meme status)")
    event = MockEvent("/meme status")
    async for result in plugin.meme_command(event):
        print(f"   回复: {result['content']}")

async def demo_permission_system():
    """演示权限系统"""
    print_separator("权限系统演示")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 普通用户尝试访问在线列表
    print("1. 普通用户访问在线表情包列表")
    normal_event = MockEvent("/meme list --online", "normal_user", False)
    async for result in plugin.meme_command(normal_event):
        print(f"   权限检查结果: {result['content']}")
    
    # 超级用户访问在线列表
    print("\n2. 超级用户访问在线表情包列表")
    admin_event = MockEvent("/meme list --online", "admin_user", True)
    async for result in plugin.meme_command(admin_event):
        if result["type"] == "plain":
            print(f"   回复: {result['content'][:200]}...")
        else:
            print(f"   图片回复: {result['content']}")

async def demo_session_management():
    """演示会话管理"""
    print_separator("会话管理演示")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 添加测试包
    plugin.packs["test_pack"] = PackConfig(
        name="test_pack",
        display_name="测试表情包",
        description="用于删除测试的表情包",
        enabled=True
    )
    
    # 启动删除流程
    print("1. 发起删除命令 (/meme delete test_pack)")
    admin_event = MockEvent("/meme delete test_pack", "admin_user", True)
    admin_event.is_superuser = lambda: True
    
    async for result in plugin.meme_command(admin_event):
        print(f"   确认提示: {result['content']}")
    
    # 检查会话状态
    session = await plugin.get_session("admin_user")
    print(f"   会话状态: {'已创建' if session else '未创建'}")
    if session:
        print(f"   会话类型: {session.session_type}")
        print(f"   会话数据: {session.data}")
    
    # 模拟用户确认
    print("\n2. 用户确认删除 (回复 'yes')")
    confirm_event = MockEvent("yes", "admin_user", True)
    async for result in plugin.meme_command(confirm_event):
        print(f"   删除结果: {result['content']}")
    
    # 检查会话是否已清理
    session_after = await plugin.get_session("admin_user")
    print(f"   会话清理: {'成功' if not session_after else '失败'}")

async def demo_image_generation():
    """演示图片生成功能"""
    print_separator("图片生成演示")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 创建测试包
    test_packs = [
        PackConfig(
            name="pack1",
            display_name="表情包1",
            description="第一个测试表情包",
            enabled=True,
            shortcuts=[
                ShortcutConfig(name="cmd1", command="cmd1", description="命令1"),
                ShortcutConfig(name="cmd2", command="cmd2", description="命令2")
            ]
        ),
        PackConfig(
            name="pack2",
            display_name="表情包2",
            description="第二个测试表情包",
            enabled=False,
            shortcuts=[
                ShortcutConfig(name="cmd3", command="cmd3", description="命令3")
            ]
        ),
        PackConfig(
            name="pack3",
            display_name="表情包3",
            description="第三个测试表情包",
            enabled=True,
            shortcuts=[]
        )
    ]
    
    # 生成网格图片
    print("1. 生成表情包网格图片")
    grid_path = plugin.create_pack_grid_image(test_packs, "测试表情包列表")
    if grid_path and Path(grid_path).exists():
        print(f"   ✅ 网格图片生成成功: {grid_path}")
        print(f"   文件大小: {Path(grid_path).stat().st_size} 字节")
    else:
        print("   ❌ 网格图片生成失败")
    
    # 生成帮助图片
    print("\n2. 生成帮助图片")
    help_path = plugin.create_help_image()
    if help_path and Path(help_path).exists():
        print(f"   ✅ 帮助图片生成成功: {help_path}")
        print(f"   文件大小: {Path(help_path).stat().st_size} 字节")
    else:
        print("   ❌ 帮助图片生成失败")

async def demo_pack_management():
    """演示包管理功能"""
    print_separator("包管理功能演示")
    
    context = MockContext()
    plugin = MemeMakerPlugin(context)
    await plugin.initialize()
    
    # 模拟在线包安装
    print("1. 模拟在线包安装功能")
    print("   注意: 这需要启动模拟服务器 (python mock_hub_server.py)")
    
    admin_event = MockEvent("/meme install anime_meme", "admin_user", True)
    admin_event.is_superuser = lambda: True
    
    async for result in plugin.meme_command(admin_event):
        print(f"   安装结果: {result['content']}")
    
    # 演示更新功能
    print("\n2. 模拟包更新功能")
    update_event = MockEvent("/meme update non_existent", "admin_user", True)
    update_event.is_superuser = lambda: True
    
    async for result in plugin.meme_command(update_event):
        print(f"   更新结果: {result['content']}")

async def main():
    """主演示函数"""
    print("表情包管理插件功能演示")
    print("基于 AstrBot 框架的表情包制作和管理系统")
    
    try:
        await demo_basic_commands()
        await demo_permission_system()
        await demo_session_management()
        await demo_image_generation()
        await demo_pack_management()
        
        print_separator("演示完成")
        print("✅ 所有功能演示完成")
        print("\n主要特性总结:")
        print("• 动态快捷方式注册和管理")
        print("• 完整的权限检查系统")
        print("• 会话管理和确认机制")
        print("• 图片网格预览生成")
        print("• 在线表情包中心集成")
        print("• 包的安装、更新、删除功能")
        print("• 异步操作和错误处理")
        print("• 配置热重载支持")
        
        print("\n使用说明:")
        print("1. 启动模拟服务器: python mock_hub_server.py")
        print("2. 运行测试脚本: python test_plugin.py")
        print("3. 在 AstrBot 中安装插件并使用 /meme 命令")
        
    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())