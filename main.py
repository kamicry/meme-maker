"""
Meme Stickers AstrBot Plugin
Provides sticker pack management and generation capabilities for AstrBot.
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger


@dataclass
class StickerPackMetadata:
    """Sticker pack metadata"""
    name: str
    display_name: str
    description: str
    version: str
    author: str
    stickers: List[str] = field(default_factory=list)
    enabled: bool = True
    url: Optional[str] = None
    checksum: Optional[str] = None


class ConfigWrapper:
    """
    Wraps plugin configuration and provides convenient access to settings.
    Manages plugin-specific configuration including sticker packs settings.
    """
    
    def __init__(self, astrbot_config: AstrBotConfig, plugin_name: str = "meme_stickers"):
        """
        Initialize configuration wrapper.
        
        Args:
            astrbot_config: AstrBot configuration object
            plugin_name: Plugin identifier for config namespace
        """
        self.astrbot_config = astrbot_config
        self.plugin_name = plugin_name
        self._config: Dict[str, Any] = {}
        
    def load(self, config_path: Path) -> None:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration JSON file
        """
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                self._config = {}
        else:
            logger.info("Configuration file not found, using defaults")
            self._config = self._get_default_config()
            
    def save(self, config_path: Path) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to configuration JSON file
        """
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved configuration to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "auto_update": False,
            "force_update": False,
            "hub_url": "http://localhost:8888",
            "cache_timeout": 3600,
            "packs": {}
        }
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        
    @property
    def auto_update(self) -> bool:
        """Whether auto-update is enabled"""
        return self.get("auto_update", False)
        
    @property
    def force_update(self) -> bool:
        """Whether force update is enabled"""
        return self.get("force_update", False)
        
    @property
    def hub_url(self) -> str:
        """Hub URL for pack downloads"""
        return self.get("hub_url", "http://localhost:8888")
        
    @property
    def packs(self) -> Dict[str, Any]:
        """Sticker packs configuration"""
        return self.get("packs", {})


class StickerPackManager:
    """
    Manages sticker packs lifecycle: loading, updating, and metadata.
    Handles pack discovery, validation, and state management.
    """
    
    def __init__(self, packs_dir: Path, config: ConfigWrapper):
        """
        Initialize sticker pack manager.
        
        Args:
            packs_dir: Directory containing sticker packs
            config: Configuration wrapper instance
        """
        self.packs_dir = packs_dir
        self.config = config
        self.packs: Dict[str, StickerPackMetadata] = {}
        self._update_task: Optional[asyncio.Task] = None
        
    async def reload(self) -> None:
        """
        Reload all sticker packs from disk.
        Discovers packs in the packs directory and loads their metadata.
        """
        logger.info("Reloading sticker packs...")
        self.packs.clear()
        
        if not self.packs_dir.exists():
            logger.warning(f"Packs directory does not exist: {self.packs_dir}")
            return
            
        # Scan packs directory
        for pack_dir in self.packs_dir.iterdir():
            if pack_dir.is_dir():
                await self._load_pack(pack_dir)
                
        logger.info(f"Loaded {len(self.packs)} sticker pack(s)")
        
    async def _load_pack(self, pack_dir: Path) -> None:
        """
        Load a single sticker pack from directory.
        
        Args:
            pack_dir: Path to pack directory
        """
        metadata_file = pack_dir / "metadata.json"
        if not metadata_file.exists():
            logger.warning(f"Pack metadata not found: {metadata_file}")
            return
            
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
                
            # Load sticker files
            stickers = []
            stickers_dir = pack_dir / "stickers"
            if stickers_dir.exists():
                stickers = [
                    f.stem for f in stickers_dir.iterdir()
                    if f.is_file() and f.suffix in ['.png', '.jpg', '.jpeg', '.gif']
                ]
                
            pack = StickerPackMetadata(
                name=metadata_data.get("name", pack_dir.name),
                display_name=metadata_data.get("display_name", pack_dir.name),
                description=metadata_data.get("description", ""),
                version=metadata_data.get("version", "1.0.0"),
                author=metadata_data.get("author", "Unknown"),
                stickers=sorted(stickers),
                enabled=metadata_data.get("enabled", True),
                url=metadata_data.get("url"),
                checksum=metadata_data.get("checksum")
            )
            
            self.packs[pack.name] = pack
            logger.info(f"Loaded pack '{pack.name}' with {len(pack.stickers)} sticker(s)")
            
        except Exception as e:
            logger.error(f"Failed to load pack from {pack_dir}: {e}")
            
    def get_pack(self, name: str) -> Optional[StickerPackMetadata]:
        """
        Get sticker pack by name.
        
        Args:
            name: Pack name
            
        Returns:
            Pack metadata or None if not found
        """
        return self.packs.get(name)
        
    def list_packs(self) -> List[StickerPackMetadata]:
        """
        Get list of all loaded packs.
        
        Returns:
            List of pack metadata
        """
        return list(self.packs.values())
        
    def list_enabled_packs(self) -> List[StickerPackMetadata]:
        """
        Get list of enabled packs.
        
        Returns:
            List of enabled pack metadata
        """
        return [pack for pack in self.packs.values() if pack.enabled]
        
    async def start_auto_update(self, force: bool = False) -> None:
        """
        Start automatic pack update task.
        
        Args:
            force: Whether to force update even if not changed
        """
        if self._update_task and not self._update_task.done():
            logger.info("Auto-update task already running")
            return
            
        logger.info(f"Starting auto-update task (force={force})")
        self._update_task = asyncio.create_task(self._auto_update_loop(force))
        
    async def _auto_update_loop(self, force: bool) -> None:
        """
        Auto-update loop that periodically checks for pack updates.
        
        Args:
            force: Whether to force update
        """
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                logger.info("Running auto-update check...")
                await self.reload()
            except asyncio.CancelledError:
                logger.info("Auto-update task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto-update loop: {e}")
                
    async def stop_auto_update(self) -> None:
        """Stop automatic pack update task"""
        if self._update_task and not self._update_task.done():
            logger.info("Stopping auto-update task")
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass


@register("meme_stickers", "kamicry", "Meme Stickers plugin for AstrBot", "2.0.0")
class MemeStickersPlugin(Star):
    """
    Main plugin class for Meme Stickers.
    Wires together configuration, data directories, and sticker pack management.
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        """
        Initialize Meme Stickers plugin.
        
        Args:
            context: AstrBot context
            config: AstrBot configuration
        """
        super().__init__(context)
        self.context = context
        self.astrbot_config = config
        
        # Initialize configuration wrapper
        self.config = ConfigWrapper(config, "meme_stickers")
        
        # Resolve plugin data directory
        self.data_dir = self._resolve_data_dir()
        self.packs_dir = self.data_dir / "packs"
        self.config_file = self.data_dir / "config.json"
        
        # Initialize sticker pack manager
        self.pack_manager: Optional[StickerPackManager] = None
        self._background_tasks: List[asyncio.Task] = []
        
    def _resolve_data_dir(self) -> Path:
        """
        Resolve and create plugin data directory.
        
        Returns:
            Path to plugin data directory
        """
        # Try to get data path from context
        if hasattr(self.context, 'get_data_path'):
            base_path = Path(self.context.get_data_path())
        else:
            # Fallback to data/plugins/meme_stickers
            base_path = Path("data/plugins/meme_stickers")
            
        # Create directory if it doesn't exist
        base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Plugin data directory: {base_path}")
        
        return base_path
        
    async def initialize(self) -> None:
        """
        Plugin initialization hook.
        - Creates data directories
        - Loads configuration
        - Initializes pack manager
        - Optionally starts auto-update
        """
        logger.info("Initializing Meme Stickers plugin...")
        
        # Create data directories
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Packs directory: {self.packs_dir}")
        
        # Load configuration
        self.config.load(self.config_file)
        
        # Initialize pack manager
        self.pack_manager = StickerPackManager(self.packs_dir, self.config)
        
        # Reload packs
        await self.pack_manager.reload()
        
        # Start auto-update if enabled
        if self.config.auto_update:
            logger.info("Auto-update enabled, starting background task...")
            task = asyncio.create_task(
                self.pack_manager.start_auto_update(self.config.force_update)
            )
            self._background_tasks.append(task)
            
        logger.info("Meme Stickers plugin initialized successfully")
        
    async def terminate(self) -> None:
        """
        Plugin termination hook.
        Gracefully cancels background tasks and cleans up resources.
        """
        logger.info("Terminating Meme Stickers plugin...")
        
        # Stop auto-update
        if self.pack_manager:
            await self.pack_manager.stop_auto_update()
            
        # Cancel all background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        self._background_tasks.clear()
        logger.info("Meme Stickers plugin terminated")
        
    def _plain(self, text: str) -> MessageEventResult:
        """
        Helper to create plain text message result.
        
        Args:
            text: Message text
            
        Returns:
            Plain text message result
        """
        return MessageEventResult().message(text)
        
    def _image(self, image_path: str) -> MessageEventResult:
        """
        Helper to create image message result.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Image message result
        """
        return MessageEventResult().image(image_path)
        
    @filter.command_group("meme")
    def meme(self):
        """Meme Stickers commands"""
        pass

    @meme.command()
    async def __default__(self, event: AstrMessageEvent):
        """Default handler for /meme command"""
        help_text = (
            "Meme Stickers Plugin\n"
            "Commands:\n"
            "  /meme list - List available sticker packs\n"
            "  /meme status - Show plugin status\n"
            "  /meme help - Show this help message"
        )
        yield event.plain_result(help_text)

    @meme.command("list")
    async def list_packs(self, event: AstrMessageEvent):
        """List available sticker packs"""
        async for msg in self._handle_list(event):
            yield msg

    @meme.command("status")
    async def show_status(self, event: AstrMessageEvent):
        """Show plugin status"""
        async for msg in self._handle_status(event):
            yield msg

    @meme.command("help")
    async def show_help(self, event: AstrMessageEvent):
        """Show help message"""
        help_text = (
            "Meme Stickers Plugin\n"
            "Commands:\n"
            "  /meme list - List available sticker packs\n"
            "  /meme status - Show plugin status\n"
            "  /meme help - Show this help message"
        )
        yield event.plain_result(help_text)
            
    async def _handle_list(self, event: AstrMessageEvent):
        """Handle list command"""
        if not self.pack_manager:
            yield event.plain_result("Pack manager not initialized")
            return
            
        packs = self.pack_manager.list_packs()
        if not packs:
            yield event.plain_result("No sticker packs available")
            return
            
        lines = ["Available Sticker Packs:"]
        for pack in packs:
            status = "✓" if pack.enabled else "✗"
            lines.append(
                f"  [{status}] {pack.display_name} ({pack.name}) - "
                f"{len(pack.stickers)} sticker(s) - v{pack.version}"
            )
            
        yield event.plain_result("\n".join(lines))
        
    async def _handle_status(self, event: AstrMessageEvent):
        """Handle status command"""
        if not self.pack_manager:
            yield event.plain_result("Pack manager not initialized")
            return
            
        all_packs = self.pack_manager.list_packs()
        enabled_packs = self.pack_manager.list_enabled_packs()
        
        status_text = (
            f"Meme Stickers Plugin Status\n"
            f"Data directory: {self.data_dir}\n"
            f"Packs directory: {self.packs_dir}\n"
            f"Total packs: {len(all_packs)}\n"
            f"Enabled packs: {len(enabled_packs)}\n"
            f"Auto-update: {'Enabled' if self.config.auto_update else 'Disabled'}\n"
            f"Force update: {'Yes' if self.config.force_update else 'No'}"
        )
        
        yield event.plain_result(status_text)
