import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class ShortcutConfig:
    """快捷方式配置"""
    name: str
    command: str
    description: str
    enabled: bool = True

@dataclass
class PackConfig:
    """表情包配置"""
    name: str
    display_name: str
    description: str
    enabled: bool = True
    shortcuts: List[ShortcutConfig] = None
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.shortcuts is None:
            self.shortcuts = []

@register("meme-maker", "kamicry", "表情包制作插件，支持动态快捷方式注册", "1.3.0")
class MemeMakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = Path(context.get_data_path()) if hasattr(context, 'get_data_path') else Path("data")
        self.packs_dir = self.data_dir / "packs"
        self.config_file = self.data_dir / "config.json"
        self.packs: Dict[str, PackConfig] = {}
        self.registered_commands: Dict[str, str] = {}  # command -> pack_name
        
    async def initialize(self):
        """插件初始化"""
        logger.info("MemeMaker 插件初始化中...")
        
        # 创建数据目录
        self.data_dir.mkdir(exist_ok=True)
        self.packs_dir.mkdir(exist_ok=True)
        
        # 加载配置
        await self.load_config()
        
        # 注册所有启用的快捷方式
        await self.register_all_shortcuts()
        
        logger.info(f"MemeMaker 插件初始化完成，已加载 {len(self.packs)} 个表情包")
    
    async def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 加载每个包的配置
                for pack_name, pack_data in config_data.get('packs', {}).items():
                    shortcuts = []
                    for shortcut_data in pack_data.get('shortcuts', []):
                        shortcuts.append(ShortcutConfig(
                            name=shortcut_data['name'],
                            command=shortcut_data['command'],
                            description=shortcut_data['description'],
                            enabled=shortcut_data.get('enabled', True)
                        ))
                    
                    self.packs[pack_name] = PackConfig(
                        name=pack_name,
                        display_name=pack_data.get('display_name', pack_name),
                        description=pack_data.get('description', ''),
                        enabled=pack_data.get('enabled', True),
                        shortcuts=shortcuts,
                        checksum=pack_data.get('checksum')
                    )
                
                logger.info(f"成功加载配置，包含 {len(self.packs)} 个表情包")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        else:
            # 创建默认配置
            await self.create_default_config()
    
    async def create_default_config(self):
        """创建默认配置"""
        default_config = {
            "packs": {
                "default": {
                    "display_name": "默认表情包",
                    "description": "默认表情包集合",
                    "enabled": True,
                    "shortcuts": [
                        {
                            "name": "doge",
                            "command": "doge",
                            "description": "发送 doge 表情",
                            "enabled": True
                        },
                        {
                            "name": "cat",
                            "command": "cat",
                            "description": "发送猫咪表情",
                            "enabled": True
                        }
                    ],
                    "checksum": None
                }
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("创建默认配置文件成功")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")
    
    async def register_all_shortcuts(self):
        """注册所有启用的快捷方式"""
        for pack_name, pack in self.packs.items():
            if pack.enabled:
                await self.register_pack_shortcuts(pack_name, pack)
    
    async def register_pack_shortcuts(self, pack_name: str, pack: PackConfig):
        """注册单个包的快捷方式"""
        for shortcut in pack.shortcuts:
            if shortcut.enabled and shortcut.command not in self.registered_commands:
                await self.register_shortcut(pack_name, shortcut)
    
    async def register_shortcut(self, pack_name: str, shortcut: ShortcutConfig):
        """动态注册快捷方式"""
        try:
            # 创建动态命令处理器
            async def shortcut_handler(event: AstrMessageEvent):
                await self.handle_shortcut_command(event, pack_name, shortcut.command)
            
            # 注册命令
            handler_name = f"shortcut_{shortcut.command}"
            setattr(self, handler_name, shortcut_handler)
            
            # 使用装饰器注册命令
            decorator = filter.command(shortcut.command)
            decorated_handler = decorator(shortcut_handler)
            
            # 记录注册的命令
            self.registered_commands[shortcut.command] = pack_name
            logger.info(f"注册快捷方式: {shortcut.command} (包: {pack_name})")
            
        except Exception as e:
            logger.error(f"注册快捷方式失败 {shortcut.command}: {e}")
    
    async def unregister_pack_shortcuts(self, pack_name: str):
        """注销包的所有快捷方式"""
        commands_to_unregister = [
            cmd for cmd, pack in self.registered_commands.items() 
            if pack == pack_name
        ]
        
        for command in commands_to_unregister:
            await self.unregister_shortcut(command)
    
    async def unregister_shortcut(self, command: str):
        """注销快捷方式"""
        try:
            if command in self.registered_commands:
                # 从注册表中移除
                del self.registered_commands[command]
                
                # 移除动态创建的方法
                handler_name = f"shortcut_{command}"
                if hasattr(self, handler_name):
                    delattr(self, handler_name)
                
                logger.info(f"注销快捷方式: {command}")
        except Exception as e:
            logger.error(f"注销快捷方式失败 {command}: {e}")
    
    async def handle_shortcut_command(self, event: AstrMessageEvent, pack_name: str, command: str):
        """处理快捷方式命令"""
        try:
            pack = self.packs.get(pack_name)
            if not pack or not pack.enabled:
                yield event.plain_result(f"表情包 {pack_name} 已禁用")
                return
            
            # 获取用户输入的参数
            message_parts = event.message_str.split()
            if len(message_parts) < 2:
                # 没有参数，显示帮助信息
                shortcuts = [s for s in pack.shortcuts if s.enabled and s.command == command]
                if shortcuts:
                    shortcut = shortcuts[0]
                    yield event.plain_result(f"用法: /{command} [文本]\n{shortcut.description}")
                return
            
            # 获取参数文本
            text = " ".join(message_parts[1:])
            
            # 生成表情包（这里先返回模拟结果）
            result = await self.generate_meme(pack_name, command, text)
            yield event.plain_result(result)
            
        except Exception as e:
            logger.error(f"处理快捷方式命令失败 {command}: {e}")
            yield event.plain_result(f"生成表情包失败: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_meme(self, pack_name: str, command: str, text: str) -> str:
        """生成表情包（模拟实现）"""
        # 这里应该实现实际的表情包生成逻辑
        # 使用 skia-python 进行图像处理，cookit 进行图像操作等
        
        pack = self.packs.get(pack_name)
        if not pack:
            raise ValueError(f"表情包 {pack_name} 不存在")
        
        # 模拟表情包生成
        result = f"[{pack.display_name}] {command}: {text}"
        
        # 这里可以添加实际的图像处理逻辑
        # 例如：
        # import skia
        # from cookit import ImageProcessor
        # 
        # # 加载模板图像
        # template_path = self.packs_dir / pack_name / f"{command}.png"
        # if template_path.exists():
        #     # 使用 skia 和 cookit 处理图像
        #     # ...
        #     result_image_path = self.data_dir / "output" / f"{command}_{hash(text)}.png"
        #     # 返回生成的图像
        #     return event.image_result(str(result_image_path))
        
        return result
    
    @filter.command("meme")
    async def meme_command(self, event: AstrMessageEvent):
        """表情包管理命令"""
        message_parts = event.message_str.split()
        
        if len(message_parts) < 2:
            # 显示帮助信息
            help_text = """
表情包管理命令使用说明：
/meme list - 列出所有表情包
/meme enable <包名> - 启用表情包
/meme disable <包名> - 禁用表情包
/meme reload - 重新加载配置
/meme status - 显示状态信息
            """.strip()
            yield event.plain_result(help_text)
            return
        
        sub_command = message_parts[1].lower()
        
        if sub_command == "list":
            await self.handle_list_command(event)
        elif sub_command == "enable":
            await self.handle_enable_command(event, message_parts)
        elif sub_command == "disable":
            await self.handle_disable_command(event, message_parts)
        elif sub_command == "reload":
            await self.handle_reload_command(event)
        elif sub_command == "status":
            await self.handle_status_command(event)
        else:
            yield event.plain_result(f"未知命令: {sub_command}")
    
    async def handle_list_command(self, event: AstrMessageEvent):
        """处理列表命令"""
        if not self.packs:
            yield event.plain_result("暂无表情包")
            return
        
        text = "表情包列表：\n"
        for pack_name, pack in self.packs.items():
            status = "✅ 启用" if pack.enabled else "❌ 禁用"
            shortcuts = [s.command for s in pack.shortcuts if s.enabled]
            text += f"\n{pack.display_name} ({pack_name}) - {status}"
            if shortcuts:
                text += f"\n  快捷方式: {', '.join(shortcuts)}"
        
        yield event.plain_result(text)
    
    async def handle_enable_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理启用命令"""
        if len(message_parts) < 3:
            yield event.plain_result("请指定要启用的包名")
            return
        
        pack_name = message_parts[2]
        pack = self.packs.get(pack_name)
        
        if not pack:
            yield event.plain_result(f"表情包 {pack_name} 不存在")
            return
        
        if pack.enabled:
            yield event.plain_result(f"表情包 {pack_name} 已经启用")
            return
        
        # 启用包
        pack.enabled = True
        await self.register_pack_shortcuts(pack_name, pack)
        await self.save_config()
        
        yield event.plain_result(f"已启用表情包 {pack_name}")
    
    async def handle_disable_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理禁用命令"""
        if len(message_parts) < 3:
            yield event.plain_result("请指定要禁用的包名")
            return
        
        pack_name = message_parts[2]
        pack = self.packs.get(pack_name)
        
        if not pack:
            yield event.plain_result(f"表情包 {pack_name} 不存在")
            return
        
        if not pack.enabled:
            yield event.plain_result(f"表情包 {pack_name} 已经禁用")
            return
        
        # 禁用包
        pack.enabled = False
        await self.unregister_pack_shortcuts(pack_name)
        await self.save_config()
        
        yield event.plain_result(f"已禁用表情包 {pack_name}")
    
    async def handle_reload_command(self, event: AstrMessageEvent):
        """处理重载命令"""
        # 注销所有现有命令
        for command in list(self.registered_commands.keys()):
            await self.unregister_shortcut(command)
        
        # 重新加载配置
        self.packs.clear()
        await self.load_config()
        
        # 重新注册命令
        await self.register_all_shortcuts()
        
        yield event.plain_result("配置重载完成")
    
    async def handle_status_command(self, event: AstrMessageEvent):
        """处理状态命令"""
        total_packs = len(self.packs)
        enabled_packs = len([p for p in self.packs.values() if p.enabled])
        total_shortcuts = len(self.registered_commands)
        
        text = f"""
表情包插件状态：
总包数: {total_packs}
启用包数: {enabled_packs}
注册的快捷方式: {total_shortcuts}
数据目录: {self.data_dir}
配置文件: {self.config_file}
        """.strip()
        
        yield event.plain_result(text)
    
    async def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                "packs": {}
            }
            
            for pack_name, pack in self.packs.items():
                shortcuts_data = []
                for shortcut in pack.shortcuts:
                    shortcuts_data.append({
                        "name": shortcut.name,
                        "command": shortcut.command,
                        "description": shortcut.description,
                        "enabled": shortcut.enabled
                    })
                
                config_data["packs"][pack_name] = {
                    "display_name": pack.display_name,
                    "description": pack.description,
                    "enabled": pack.enabled,
                    "shortcuts": shortcuts_data,
                    "checksum": pack.checksum
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    async def terminate(self):
        """插件销毁时清理"""
        logger.info("MemeMaker 插件正在关闭...")
        
        # 注销所有动态注册的命令
        for command in list(self.registered_commands.keys()):
            await self.unregister_shortcut(command)
        
        logger.info("MemeMaker 插件已关闭")