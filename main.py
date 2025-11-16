import os
import json
import asyncio
import hashlib
import tempfile
import shutil
import shlex
import argparse
import re
import io
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    import skia
    SKIA_AVAILABLE = True
except ImportError:
    SKIA_AVAILABLE = False
    logger.warning("skia-python not available, some features may be limited")
from PIL import Image, ImageDraw, ImageFont, ImageColor

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
    url: Optional[str] = None  # 在线下载URL
    version: Optional[str] = None
    author: Optional[str] = None
    
    def __post_init__(self):
        if self.shortcuts is None:
            self.shortcuts = []

@dataclass
class HubPack:
    """在线表情包信息"""
    name: str
    display_name: str
    description: str
    url: str
    version: str
    author: str
    size: int
    preview_url: Optional[str] = None
    downloads: int = 0

@dataclass
class UserSession:
    """用户会话信息"""
    user_id: str
    session_type: str  # 'delete_confirm', 'install_confirm', 'generate_pack', 'generate_sticker', 'generate_text', etc.
    data: Dict[str, Any]
    timeout: datetime

@dataclass
class StickerParams:
    """表情包生成参数"""
    pack: Optional[str] = None
    sticker: Optional[str] = None
    text: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    align: str = "center"
    valign: str = "middle"
    font: Optional[str] = None
    font_size: Optional[int] = None
    color: str = "black"
    stroke_color: Optional[str] = None
    stroke_width: int = 0
    angle: float = 0.0
    auto_resize: bool = True
    debug: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pack': self.pack,
            'sticker': self.sticker,
            'text': self.text,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'align': self.align,
            'valign': self.valign,
            'font': self.font,
            'font_size': self.font_size,
            'color': self.color,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'angle': self.angle,
            'auto_resize': self.auto_resize,
            'debug': self.debug
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StickerParams':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@register("meme-maker", "kamicry", "表情包制作插件，支持动态快捷方式注册", "1.3.0")
class MemeMakerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = Path(context.get_data_path()) if hasattr(context, 'get_data_path') else Path("data")
        self.packs_dir = self.data_dir / "packs"
        self.config_file = self.data_dir / "config.json"
        self.packs: Dict[str, PackConfig] = {}
        self.registered_commands: Dict[str, str] = {}  # command -> pack_name
        self.user_sessions: Dict[str, UserSession] = {}  # user_id -> session
        self.hub_cache: List[HubPack] = []
        self.hub_cache_time: Optional[datetime] = None
        
        # 配置
        self.hub_url = "http://localhost:8888"  # 本地测试API地址
        self.session_timeout = timedelta(minutes=5)
        self.hub_cache_timeout = timedelta(hours=1)
        
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
        
        # 启动会话清理任务
        asyncio.create_task(self.cleanup_sessions())
        
        logger.info(f"MemeMaker 插件初始化完成，已加载 {len(self.packs)} 个表情包")
    
    def is_superuser(self, event: AstrMessageEvent) -> bool:
        """检查用户是否为超级用户"""
        # 尝试多种方式检查权限
        if hasattr(event, 'is_superuser') and callable(event.is_superuser):
            return event.is_superuser()
        elif hasattr(event, 'sender') and hasattr(event.sender, 'role'):
            return event.sender.role in ['admin', 'superuser', 'owner']
        elif hasattr(event, 'user_id'):
            # 这里可以根据实际情况配置超级用户ID列表
            superuser_ids = self.get_configured_superusers()
            return str(event.user_id) in superuser_ids
        return False
    
    def get_configured_superusers(self) -> List[str]:
        """获取配置的超级用户ID列表"""
        # 可以从配置文件中读取超级用户列表
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('superusers', [])
        except Exception:
            pass
        return []
    
    async def create_session(self, user_id: str, session_type: str, data: Dict[str, Any]) -> UserSession:
        """创建用户会话"""
        session = UserSession(
            user_id=user_id,
            session_type=session_type,
            data=data,
            timeout=datetime.now() + self.session_timeout
        )
        self.user_sessions[user_id] = session
        return session
    
    async def get_session(self, user_id: str) -> Optional[UserSession]:
        """获取用户会话"""
        session = self.user_sessions.get(user_id)
        if session and datetime.now() < session.timeout:
            return session
        elif session:
            # 会话已过期，清理
            del self.user_sessions[user_id]
        return None
    
    async def clear_session(self, user_id: str):
        """清除用户会话"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def cleanup_sessions(self):
        """定期清理过期会话"""
        while True:
            try:
                now = datetime.now()
                expired_users = [
                    user_id for user_id, session in self.user_sessions.items()
                    if now >= session.timeout
                ]
                for user_id in expired_users:
                    del self.user_sessions[user_id]
                await asyncio.sleep(60)  # 每分钟清理一次
            except Exception as e:
                logger.error(f"清理会话时出错: {e}")
                await asyncio.sleep(60)
    
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
    
    @filter.regex(r"^(?!/).*")
    async def handle_session_message(self, event: AstrMessageEvent):
        """处理非命令消息，检查是否有活跃会话"""
        user_id = str(getattr(event, 'user_id', 'unknown'))
        session = await self.get_session(user_id)
        
        # 如果有活跃的生成会话，处理会话
        if session and session.session_type in ['generate_pack', 'generate_sticker', 'generate_text']:
            async for result in self.handle_generate_session(event, session):
                yield result
    
    @filter.command("meme")
    async def meme_command(self, event: AstrMessageEvent):
        """表情包管理命令"""
        message_parts = event.message_str.split()
        
        if len(message_parts) < 2:
            # 显示帮助信息
            help_image_path = self.create_help_image()
            if help_image_path and Path(help_image_path).exists():
                yield event.image_result(help_image_path)
            else:
                help_text = """
表情包管理命令使用说明：
/meme list - 列出所有表情包
/meme list --online - 列出在线表情包（管理员）
/meme generate [包名] [贴纸名] [文本] [选项] - 生成表情包
  选项: -x X -y Y -w WIDTH -h HEIGHT -a ALIGN -v VALIGN -f FONT -s SIZE -c COLOR --stroke-color COLOR --stroke-width N --debug
  相对调整: 使用 ^ 前缀，如 -x ^+10 表示在原位置基础上增加10
/meme install <包名> - 安装表情包
/meme update <包名> - 更新表情包
/meme delete <包名> - 删除表情包
/meme enable <包名> - 启用表情包
/meme disable <包名> - 禁用表情包
/meme help - 显示帮助信息
                """.strip()
                yield event.plain_result(help_text)
            return
        
        sub_command = message_parts[1].lower()
        
        # 检查是否有会话需要处理
        user_id = str(getattr(event, 'user_id', 'unknown'))
        session = await self.get_session(user_id)
        
        if session:
            # 处理会话响应
            if sub_command.lower() in ['yes', 'y', '是', '确认']:
                if session.session_type == 'delete_confirm':
                    pack_name = session.data['pack_name']
                    success, message = await self.delete_pack(pack_name)
                    await self.clear_session(user_id)
                    yield event.plain_result(message)
                    return
            elif sub_command.lower() in ['no', 'n', '否', '取消', 'exit', 'quit', '退出']:
                await self.clear_session(user_id)
                yield event.plain_result("操作已取消")
                return
            elif session.session_type in ['generate_pack', 'generate_sticker', 'generate_text']:
                # 处理生成会话
                async for result in self.handle_generate_session(event, session):
                    yield result
                return
        
        # 处理正常命令
        if sub_command == "list":
            await self.handle_list_command(event, message_parts[2:] if len(message_parts) > 2 else [])
        elif sub_command == "install":
            await self.handle_install_command(event, message_parts)
        elif sub_command == "update":
            await self.handle_update_command(event, message_parts)
        elif sub_command == "delete":
            await self.handle_delete_command(event, message_parts)
        elif sub_command == "enable":
            await self.handle_enable_command(event, message_parts)
        elif sub_command == "disable":
            await self.handle_disable_command(event, message_parts)
        elif sub_command == "reload":
            await self.handle_reload_command(event)
        elif sub_command == "status":
            await self.handle_status_command(event)
        elif sub_command == "generate":
            async for result in self.handle_generate_command(event, message_parts):
                yield result
        elif sub_command == "help":
            help_image_path = self.create_help_image()
            if help_image_path and Path(help_image_path).exists():
                yield event.image_result(help_image_path)
            else:
                yield event.plain_result("帮助图片生成失败，请查看控制台日志")
        else:
            yield event.plain_result(f"未知命令: {sub_command}")
    
    async def handle_list_command(self, event: AstrMessageEvent, args: List[str]):
        """处理列表命令"""
        is_online = '--online' in args
        
        if is_online:
            # 在线列表 - 需要管理员权限
            if not self.is_superuser(event):
                yield event.plain_result("查看在线表情包需要管理员权限")
                return
            
            yield event.plain_result("正在获取在线表情包列表...")
            hub_packs = await self.fetch_hub_packs()
            
            if not hub_packs:
                yield event.plain_result("无法获取在线表情包列表")
                return
            
            # 创建在线包的预览图
            pack_configs = []
            for hub_pack in hub_packs:
                pack_configs.append(PackConfig(
                    name=hub_pack.name,
                    display_name=hub_pack.display_name,
                    description=hub_pack.description,
                    enabled=False,  # 在线包默认未安装
                    shortcuts=[],
                    url=hub_pack.url,
                    version=hub_pack.version,
                    author=hub_pack.author
                ))
            
            image_path = self.create_pack_grid_image(pack_configs, "在线表情包列表")
            if image_path and Path(image_path).exists():
                yield event.image_result(image_path)
                
                # 同时发送文字说明
                text = f"找到 {len(hub_packs)} 个在线表情包：\n\n"
                for i, hub_pack in enumerate(hub_packs[:10]):  # 只显示前10个
                    status = "✅ 已安装" if hub_pack.name in self.packs else "⬇️ 可安装"
                    text += f"{status} {hub_pack.display_name} ({hub_pack.name})\n"
                    text += f"  版本: {hub_pack.version} | 作者: {hub_pack.author}\n"
                    text += f"  大小: {hub_pack.size // 1024}KB | 下载: {hub_pack.downloads}次\n\n"
                
                if len(hub_packs) > 10:
                    text += f"... 还有 {len(hub_packs) - 10} 个表情包\n"
                text += "使用 /meme install <包名> 来安装表情包"
                
                yield event.plain_result(text)
            else:
                # 降级到文字显示
                text = f"在线表情包列表 ({len(hub_packs)}个)：\n\n"
                for hub_pack in hub_packs:
                    status = "✅ 已安装" if hub_pack.name in self.packs else "⬇️ 可安装"
                    text += f"{status} {hub_pack.display_name}\n"
                    text += f"  包名: {hub_pack.name}\n"
                    text += f"  版本: {hub_pack.version} | 作者: {hub_pack.author}\n\n"
                
                yield event.plain_result(text)
        
        else:
            # 本地列表
            if not self.packs:
                yield event.plain_result("暂无本地表情包，使用 /meme list --online 查看可安装的表情包")
                return
            
            # 创建本地包预览图
            image_path = self.create_pack_grid_image(list(self.packs.values()), "本地表情包列表")
            if image_path and Path(image_path).exists():
                yield event.image_result(image_path)
            
            # 同时发送详细信息
            text = f"本地表情包列表 ({len(self.packs)}个)：\n\n"
            for pack_name, pack in self.packs.items():
                status = "✅ 启用" if pack.enabled else "❌ 禁用"
                shortcuts = [s.command for s in pack.shortcuts if s.enabled]
                text += f"{status} {pack.display_name} ({pack_name})\n"
                if shortcuts:
                    text += f"  快捷方式: {', '.join(shortcuts)}\n"
                if pack.version:
                    text += f"  版本: {pack.version}\n"
                if pack.author:
                    text += f"  作者: {pack.author}\n"
                text += "\n"
            
            yield event.plain_result(text.rstrip())
    
    async def handle_install_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理安装命令"""
        if not self.is_superuser(event):
            yield event.plain_result("安装表情包需要管理员权限")
            return
        
        if len(message_parts) < 3:
            yield event.plain_result("请指定要安装的包名\n用法: /meme install <包名>")
            return
        
        pack_name = message_parts[2]
        
        # 检查是否已存在
        if pack_name in self.packs:
            yield event.plain_result(f"表情包 {pack_name} 已存在，使用 /meme update {pack_name} 来更新")
            return
        
        yield event.plain_result(f"正在搜索表情包 {pack_name}...")
        
        # 获取在线包信息
        hub_packs = await self.fetch_hub_packs()
        target_pack = None
        for hub_pack in hub_packs:
            if hub_pack.name == pack_name:
                target_pack = hub_pack
                break
        
        if not target_pack:
            yield event.plain_result(f"在线找不到表情包 {pack_name}")
            return
        
        yield event.plain_result(f"开始下载表情包 {target_pack.display_name}...")
        
        # 下载并安装
        success = await self.download_pack(target_pack)
        if success:
            yield event.plain_result(f"✅ 成功安装表情包 {pack_name}\n快捷方式已自动注册")
        else:
            yield event.plain_result(f"❌ 安装表情包 {pack_name} 失败")
    
    async def handle_update_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理更新命令"""
        if not self.is_superuser(event):
            yield event.plain_result("更新表情包需要管理员权限")
            return
        
        if len(message_parts) < 3:
            yield event.plain_result("请指定要更新的包名\n用法: /meme update <包名>")
            return
        
        pack_name = message_parts[2]
        
        yield event.plain_result(f"正在更新表情包 {pack_name}...")
        
        success, message = await self.update_pack(pack_name)
        yield event.plain_result(message)
    
    async def handle_delete_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理删除命令"""
        if not self.is_superuser(event):
            yield event.plain_result("删除表情包需要管理员权限")
            return
        
        if len(message_parts) < 3:
            yield event.plain_result("请指定要删除的包名\n用法: /meme delete <包名>")
            return
        
        pack_name = message_parts[2]
        pack = self.packs.get(pack_name)
        
        if not pack:
            yield event.plain_result(f"表情包 {pack_name} 不存在")
            return
        
        # 创建确认会话
        user_id = str(getattr(event, 'user_id', 'unknown'))
        await self.create_session(user_id, 'delete_confirm', {'pack_name': pack_name})
        
        yield event.plain_result(
            f"⚠️ 确认删除表情包 {pack.display_name} ({pack_name})？\n"
            f"这将删除所有相关文件和配置！\n\n"
            f"回复 'yes' 确认删除，或回复 'no' 取消\n"
            f"(会话超时时间: 5分钟)"
        )
    
    async def handle_enable_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理启用命令"""
        if len(message_parts) < 3:
            yield event.plain_result("请指定要启用的包名\n用法: /meme enable <包名>")
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
        
        yield event.plain_result(f"✅ 已启用表情包 {pack_name}")
    
    async def handle_disable_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理禁用命令"""
        if len(message_parts) < 3:
            yield event.plain_result("请指定要禁用的包名\n用法: /meme disable <包名>")
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
        
        yield event.plain_result(f"✅ 已禁用表情包 {pack_name}")
    
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
    
    async def handle_generate_command(self, event: AstrMessageEvent, message_parts: List[str]):
        """处理生成命令"""
        user_id = str(getattr(event, 'user_id', 'unknown'))
        
        # 解析命令行参数
        args_str = event.message_str.split(maxsplit=2)
        args_text = args_str[2] if len(args_str) > 2 else ""
        
        # 使用shlex分割参数，支持引号
        try:
            args = shlex.split(args_text) if args_text else []
        except ValueError as e:
            yield event.plain_result(f"参数解析错误: {str(e)}")
            return
        
        # 解析参数
        params = await self.parse_generate_args(args)
        
        if isinstance(params, str):
            # 解析失败，返回错误信息
            yield event.plain_result(params)
            return
        
        # 检查是否需要交互式提示
        if not params.pack:
            # 开始交互式流程 - 请求包名
            await self.create_session(user_id, 'generate_pack', {'params': params.to_dict()})
            
            # 列出可用的包
            pack_list = "\n".join([f"  • {name} ({pack.display_name})" 
                                   for name, pack in self.packs.items() if pack.enabled])
            
            if not pack_list:
                await self.clear_session(user_id)
                yield event.plain_result("没有可用的表情包。请先使用 /meme list 查看或安装表情包。")
                return
            
            yield event.plain_result(
                f"请选择表情包:\n{pack_list}\n\n"
                f"回复表情包名称，或输入 'exit' 退出 (超时: 5分钟)"
            )
            return
        
        if not params.sticker:
            # 开始交互式流程 - 请求贴纸名
            await self.create_session(user_id, 'generate_sticker', {'params': params.to_dict()})
            
            # 列出该包中的贴纸
            pack = self.packs.get(params.pack)
            if not pack:
                await self.clear_session(user_id)
                yield event.plain_result(f"表情包 {params.pack} 不存在")
                return
            
            sticker_files = await self.get_sticker_list(params.pack)
            if not sticker_files:
                await self.clear_session(user_id)
                yield event.plain_result(f"表情包 {params.pack} 中没有可用的贴纸")
                return
            
            sticker_list = "\n".join([f"  • {s}" for s in sticker_files])
            yield event.plain_result(
                f"请选择贴纸 (来自 {pack.display_name}):\n{sticker_list}\n\n"
                f"回复贴纸名称，或输入 'exit' 退出 (超时: 5分钟)"
            )
            return
        
        if not params.text:
            # 开始交互式流程 - 请求文本
            await self.create_session(user_id, 'generate_text', {'params': params.to_dict()})
            yield event.plain_result(
                f"请输入文本内容:\n\n"
                f"回复文本内容，或输入 'exit' 退出 (超时: 5分钟)"
            )
            return
        
        # 所有参数齐全，生成表情包
        async for result in self.render_sticker(event, params):
            yield result
    
    async def handle_generate_session(self, event: AstrMessageEvent, session: UserSession):
        """处理生成会话的交互"""
        user_id = str(getattr(event, 'user_id', 'unknown'))
        user_input = event.message_str.strip()
        
        # 检查退出命令
        if user_input.lower() in ['exit', 'quit', '退出', '取消']:
            await self.clear_session(user_id)
            yield event.plain_result("已退出生成流程")
            return
        
        params = StickerParams.from_dict(session.data['params'])
        
        if session.session_type == 'generate_pack':
            # 用户输入了包名
            if user_input not in self.packs:
                yield event.plain_result(f"表情包 {user_input} 不存在，请重新输入")
                return
            
            params.pack = user_input
            
            # 进入下一步 - 请求贴纸
            session.data['params'] = params.to_dict()
            session.session_type = 'generate_sticker'
            session.timeout = datetime.now() + self.session_timeout
            
            sticker_files = await self.get_sticker_list(params.pack)
            if not sticker_files:
                await self.clear_session(user_id)
                yield event.plain_result(f"表情包 {params.pack} 中没有可用的贴纸")
                return
            
            pack = self.packs[params.pack]
            sticker_list = "\n".join([f"  • {s}" for s in sticker_files])
            yield event.plain_result(
                f"请选择贴纸 (来自 {pack.display_name}):\n{sticker_list}\n\n"
                f"回复贴纸名称，或输入 'exit' 退出"
            )
        
        elif session.session_type == 'generate_sticker':
            # 用户输入了贴纸名
            sticker_files = await self.get_sticker_list(params.pack)
            if user_input not in sticker_files:
                yield event.plain_result(f"贴纸 {user_input} 不存在，请重新输入")
                return
            
            params.sticker = user_input
            
            # 进入下一步 - 请求文本
            session.data['params'] = params.to_dict()
            session.session_type = 'generate_text'
            session.timeout = datetime.now() + self.session_timeout
            
            yield event.plain_result(
                f"请输入文本内容:\n\n"
                f"回复文本内容，或输入 'exit' 退出"
            )
        
        elif session.session_type == 'generate_text':
            # 用户输入了文本
            params.text = user_input
            
            # 清除会话
            await self.clear_session(user_id)
            
            # 生成表情包
            async for result in self.render_sticker(event, params):
                yield result
    
    async def parse_generate_args(self, args: List[str]) -> Union[StickerParams, str]:
        """解析生成命令参数"""
        params = StickerParams()
        
        # 使用argparse解析参数
        parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
        parser.add_argument('pack', nargs='?', default=None)
        parser.add_argument('sticker', nargs='?', default=None)
        parser.add_argument('text', nargs='?', default=None)
        parser.add_argument('-x', '--x', type=str, default=None)
        parser.add_argument('-y', '--y', type=str, default=None)
        parser.add_argument('-w', '--width', type=str, default=None)
        parser.add_argument('-h', '--height', type=str, default=None)
        parser.add_argument('-a', '--align', choices=['left', 'center', 'right'], default='center')
        parser.add_argument('-v', '--valign', choices=['top', 'middle', 'bottom'], default='middle')
        parser.add_argument('-f', '--font', type=str, default=None)
        parser.add_argument('-s', '--font-size', type=str, default=None)
        parser.add_argument('-c', '--color', type=str, default='black')
        parser.add_argument('--stroke-color', type=str, default=None)
        parser.add_argument('--stroke-width', type=int, default=0)
        parser.add_argument('--angle', type=float, default=0.0)
        parser.add_argument('--no-resize', action='store_true', default=False)
        parser.add_argument('--debug', action='store_true', default=False)
        
        try:
            parsed = parser.parse_args(args)
            
            params.pack = parsed.pack
            params.sticker = parsed.sticker
            params.text = parsed.text
            params.align = parsed.align
            params.valign = parsed.valign
            params.font = parsed.font
            params.color = parsed.color
            params.stroke_color = parsed.stroke_color
            params.stroke_width = parsed.stroke_width
            params.angle = parsed.angle
            params.auto_resize = not parsed.no_resize
            params.debug = parsed.debug
            
            # 解析相对/绝对参数
            if parsed.x:
                params.x = self.parse_relative_param(parsed.x, None)
            if parsed.y:
                params.y = self.parse_relative_param(parsed.y, None)
            if parsed.width:
                params.width = self.parse_relative_param(parsed.width, None)
            if parsed.height:
                params.height = self.parse_relative_param(parsed.height, None)
            if parsed.font_size:
                params.font_size = self.parse_relative_param(parsed.font_size, None)
            
            return params
            
        except Exception as e:
            return f"参数解析错误: {str(e)}\n\n用法: /meme generate [包名] [贴纸名] [文本] [-x X] [-y Y] [-w WIDTH] [-h HEIGHT] [-a ALIGN] [-v VALIGN] [-f FONT] [-s SIZE] [-c COLOR]"
    
    def parse_relative_param(self, value: str, base: Optional[int]) -> Optional[int]:
        """解析相对/绝对参数
        
        支持格式：
        - 123: 绝对值
        - ^+10: 相对于base增加10
        - ^-10: 相对于base减少10
        - ^10: 相对于base (等同于^+10)
        """
        if value is None:
            return None
        
        value = value.strip()
        
        # 相对调整
        if value.startswith('^'):
            if base is None:
                logger.warning(f"相对调整 {value} 但基准值为空，将使用0作为基准")
                base = 0
            
            rel_value = value[1:]
            if rel_value.startswith('+') or rel_value.startswith('-'):
                return base + int(rel_value)
            else:
                return base + int(rel_value)
        
        # 绝对值
        return int(value)
    
    async def get_sticker_list(self, pack_name: str) -> List[str]:
        """获取表情包中的贴纸列表"""
        pack_dir = self.packs_dir / pack_name
        if not pack_dir.exists():
            return []
        
        stickers = []
        for ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            for img_path in pack_dir.glob(f'*.{ext}'):
                stickers.append(img_path.stem)
        
        return sorted(list(set(stickers)))
    
    async def render_sticker(self, event: AstrMessageEvent, params: StickerParams):
        """渲染表情包"""
        try:
            # 加载模板图片
            pack_dir = self.packs_dir / params.pack
            sticker_path = None
            
            for ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                test_path = pack_dir / f"{params.sticker}.{ext}"
                if test_path.exists():
                    sticker_path = test_path
                    break
            
            if not sticker_path:
                yield event.plain_result(f"找不到贴纸文件: {params.sticker}")
                return
            
            # 加载图片
            base_image = Image.open(sticker_path).convert('RGBA')
            img_width, img_height = base_image.size
            
            # 创建绘图对象
            draw = ImageDraw.Draw(base_image)
            
            # 加载字体
            font = self.load_font(params.font, params.font_size or 48)
            
            # 计算文本位置和大小
            text_bbox = draw.textbbox((0, 0), params.text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 计算文本位置
            if params.x is not None:
                x = params.x
            else:
                if params.align == 'left':
                    x = 10
                elif params.align == 'right':
                    x = img_width - text_width - 10
                else:  # center
                    x = (img_width - text_width) // 2
            
            if params.y is not None:
                y = params.y
            else:
                if params.valign == 'top':
                    y = 10
                elif params.valign == 'bottom':
                    y = img_height - text_height - 10
                else:  # middle
                    y = (img_height - text_height) // 2
            
            # 绘制描边
            if params.stroke_color and params.stroke_width > 0:
                for adj_x in range(-params.stroke_width, params.stroke_width + 1):
                    for adj_y in range(-params.stroke_width, params.stroke_width + 1):
                        if adj_x != 0 or adj_y != 0:
                            draw.text((x + adj_x, y + adj_y), params.text, 
                                    font=font, fill=params.stroke_color)
            
            # 绘制文本
            draw.text((x, y), params.text, font=font, fill=params.color)
            
            # 调试模式 - 绘制边框
            if params.debug:
                draw.rectangle([x, y, x + text_width, y + text_height], 
                             outline='red', width=2)
            
            # 保存图片
            output_dir = self.data_dir / "output"
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / f"meme_{hash(params.text)}_{datetime.now().timestamp()}.png"
            base_image.save(output_path, 'PNG')
            
            # 返回图片
            yield event.image_result(str(output_path))
            
            logger.info(f"成功生成表情包: {params.pack}/{params.sticker} - {params.text}")
            
        except Exception as e:
            logger.error(f"生成表情包失败: {e}")
            import traceback
            traceback.print_exc()
            yield event.plain_result(f"生成表情包失败: {str(e)}")
    
    def load_font(self, font_name: Optional[str], size: int) -> ImageFont.FreeTypeFont:
        """加载字体"""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        
        # 如果指定了字体名称，优先尝试
        if font_name:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception as e:
                logger.warning(f"无法加载字体 {font_name}: {e}")
        
        # 尝试系统字体
        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            except Exception:
                continue
        
        # 降级到默认字体
        logger.warning("无法加载任何TrueType字体，使用默认字体")
        return ImageFont.load_default()
    
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
    
    async def fetch_hub_packs(self, force_refresh: bool = False) -> List[HubPack]:
        """获取在线表情包列表"""
        now = datetime.now()
        
        # 检查缓存
        if not force_refresh and self.hub_cache_time and (now - self.hub_cache_time) < self.hub_cache_timeout:
            return self.hub_cache
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.hub_url}/packs")
                response.raise_for_status()
                
                data = response.json()
                hub_packs = []
                
                for pack_data in data.get('packs', []):
                    hub_packs.append(HubPack(
                        name=pack_data['name'],
                        display_name=pack_data['display_name'],
                        description=pack_data['description'],
                        url=pack_data['url'],
                        version=pack_data['version'],
                        author=pack_data['author'],
                        size=pack_data['size'],
                        preview_url=pack_data.get('preview_url'),
                        downloads=pack_data.get('downloads', 0)
                    ))
                
                self.hub_cache = hub_packs
                self.hub_cache_time = now
                logger.info(f"成功获取 {len(hub_packs)} 个在线表情包")
                return hub_packs
                
        except Exception as e:
            logger.error(f"获取在线表情包失败: {e}")
            return []
    
    async def download_pack(self, hub_pack: HubPack, progress_callback=None) -> bool:
        """下载并安装表情包"""
        try:
            pack_dir = self.packs_dir / hub_pack.name
            pack_dir.mkdir(exist_ok=True)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 下载压缩包
                response = await client.get(hub_pack.url)
                response.raise_for_status()
                
                # 保存到临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name
                
                # 解压（这里简化处理，实际需要根据压缩格式处理）
                import zipfile
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(pack_dir)
                
                # 清理临时文件
                os.unlink(tmp_path)
                
                # 更新配置
                await self.add_pack_from_hub(hub_pack)
                
                return True
                
        except Exception as e:
            logger.error(f"下载表情包失败 {hub_pack.name}: {e}")
            return False
    
    async def add_pack_from_hub(self, hub_pack: HubPack):
        """从在线包信息添加到配置"""
        shortcuts = []
        pack_dir = self.packs_dir / hub_pack.name
        
        # 扫描包目录中的图片文件，自动生成快捷方式
        if pack_dir.exists():
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']:
                for img_path in pack_dir.glob(ext):
                    name = img_path.stem
                    shortcuts.append(ShortcutConfig(
                        name=name,
                        command=name,
                        description=f"{hub_pack.display_name} - {name}",
                        enabled=True
                    ))
        
        pack = PackConfig(
            name=hub_pack.name,
            display_name=hub_pack.display_name,
            description=hub_pack.description,
            enabled=True,
            shortcuts=shortcuts,
            url=hub_pack.url,
            version=hub_pack.version,
            author=hub_pack.author
        )
        
        self.packs[hub_pack.name] = pack
        await self.save_config()
        await self.register_pack_shortcuts(hub_pack.name, pack)
    
    async def delete_pack(self, pack_name: str) -> Tuple[bool, str]:
        """删除表情包"""
        try:
            pack = self.packs.get(pack_name)
            if not pack:
                return False, f"表情包 {pack_name} 不存在"
            
            # 注销快捷方式
            await self.unregister_pack_shortcuts(pack_name)
            
            # 删除配置
            del self.packs[pack_name]
            
            # 删除文件
            pack_dir = self.packs_dir / pack_name
            if pack_dir.exists():
                shutil.rmtree(pack_dir)
            
            # 保存配置
            await self.save_config()
            
            return True, f"成功删除表情包 {pack_name}"
            
        except Exception as e:
            logger.error(f"删除表情包失败 {pack_name}: {e}")
            return False, f"删除表情包失败: {str(e)}"
    
    async def update_pack(self, pack_name: str) -> Tuple[bool, str]:
        """更新表情包"""
        try:
            pack = self.packs.get(pack_name)
            if not pack or not pack.url:
                return False, f"表情包 {pack_name} 不支持更新"
            
            # 获取在线信息
            hub_packs = await self.fetch_hub_packs()
            hub_pack = None
            for hp in hub_packs:
                if hp.name == pack_name:
                    hub_pack = hp
                    break
            
            if not hub_pack:
                return False, f"在线找不到表情包 {pack_name}"
            
            # 删除旧包
            await self.unregister_pack_shortcuts(pack_name)
            pack_dir = self.packs_dir / pack_name
            if pack_dir.exists():
                shutil.rmtree(pack_dir)
            
            # 下载新包
            success = await self.download_pack(hub_pack)
            if success:
                return True, f"成功更新表情包 {pack_name}"
            else:
                return False, f"更新表情包 {pack_name} 失败"
                
        except Exception as e:
            logger.error(f"更新表情包失败 {pack_name}: {e}")
            return False, f"更新表情包失败: {str(e)}"
    
    def create_pack_grid_image(self, packs: List[PackConfig], title: str = "表情包列表") -> str:
        """创建表情包网格预览图"""
        try:
            # 设置图片参数
            img_width = 800
            img_height = 600
            grid_cols = 3
            grid_rows = min(4, (len(packs) + grid_cols - 1) // grid_cols)
            
            # 创建画布
            image = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()
            
            # 绘制标题
            draw.text((20, 20), title, fill='black', font=font_title)
            
            # 绘制网格
            cell_width = (img_width - 60) // grid_cols
            cell_height = (img_height - 100) // grid_rows
            
            for i, pack in enumerate(packs[:grid_rows * grid_cols]):
                row = i // grid_cols
                col = i % grid_cols
                
                x = 30 + col * cell_width
                y = 80 + row * cell_height
                
                # 绘制边框
                draw.rectangle([x, y, x + cell_width - 10, y + cell_height - 10], outline='gray')
                
                # 绘制包信息
                status = "✅" if pack.enabled else "❌"
                text_lines = [
                    f"{status} {pack.display_name}",
                    f"({pack.name})",
                    f"快捷方式: {len(pack.shortcuts)}个"
                ]
                
                for j, line in enumerate(text_lines):
                    draw.text((x + 10, y + 10 + j * 25), line, fill='black', font=font_text)
            
            # 保存图片
            output_path = self.data_dir / "temp_pack_grid.png"
            image.save(output_path)
            return str(output_path)
            
        except Exception as e:
            logger.error(f"创建网格图片失败: {e}")
            return ""
    
    def create_help_image(self) -> str:
        """创建帮助图片"""
        try:
            img_width = 800
            img_height = 1000
            
            # 创建画布
            image = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
                font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
                font_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()
                font_code = ImageFont.load_default()
            
            # 绘制标题
            draw.text((20, 20), "表情包管理插件帮助", fill='black', font=font_title)
            
            # 帮助内容
            help_content = [
                ("基本命令:", "header"),
                ("/meme generate [包] [贴纸] [文本]", "code"),
                ("  生成表情包（交互式或快速生成）", "text"),
                ("/meme list", "code"),
                ("  列出所有本地表情包", "text"),
                ("/meme list --online", "code"),
                ("  列出在线表情包（需要管理员权限）", "text"),
                ("", "text"),
                ("/meme install <包名>", "code"),
                ("  安装指定的在线表情包", "text"),
                ("/meme update <包名>", "code"),
                ("  更新指定的表情包", "text"),
                ("/meme delete <包名>", "code"),
                ("  删除指定的表情包（需要确认）", "text"),
                ("", "text"),
                ("/meme enable <包名>", "code"),
                ("  启用指定的表情包", "text"),
                ("/meme disable <包名>", "code"),
                ("  禁用指定的表情包", "text"),
                ("", "text"),
                ("/meme help", "code"),
                ("  显示此帮助信息", "text"),
                ("", "text"),
                ("使用说明:", "header"),
                ("• 使用 /meme generate 交互式生成表情", "text"),
                ("• 支持自定义位置、颜色、字体等选项", "text"),
                ("• 管理员操作需要相应权限", "text"),
                ("• 会话超时时间为5分钟", "text"),
            ]
            
            y_pos = 80
            for line, line_type in help_content:
                if line_type == "header":
                    draw.text((20, y_pos), line, fill='black', font=font_title)
                    y_pos += 40
                elif line_type == "code":
                    draw.text((40, y_pos), line, fill='blue', font=font_code)
                    y_pos += 30
                else:  # text
                    draw.text((60, y_pos), line, fill='black', font=font_text)
                    y_pos += 25
            
            # 保存图片
            output_path = self.data_dir / "help_image.png"
            image.save(output_path)
            return str(output_path)
            
        except Exception as e:
            logger.error(f"创建帮助图片失败: {e}")
            return ""
    
    async def terminate(self):
        """插件销毁时清理"""
        logger.info("MemeMaker 插件正在关闭...")
        
        # 注销所有动态注册的命令
        for command in list(self.registered_commands.keys()):
            await self.unregister_shortcut(command)
        
        logger.info("MemeMaker 插件已关闭")