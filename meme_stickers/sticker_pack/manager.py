"""
Sticker pack manager for orchestrating pack lifecycle.
Manages loading, installing, updating, and deleting sticker packs.
"""

import json
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .models import PackManifest, PackConfig, HubPackInfo
from .pack import Pack, PackError
from .hub import HubClient, HubError
from .update import PackUpdater, UpdateError


class PackState(str, Enum):
    """Pack state enumeration"""
    LOADING = "loading"
    LOADED = "loaded"
    INSTALLING = "installing"
    INSTALLED = "installed"
    UPDATING = "updating"
    UPDATED = "updated"
    DELETING = "deleting"
    DELETED = "deleted"
    ERROR = "error"


@dataclass
class PackEvent:
    """Event for pack state changes"""
    pack_name: str
    state: PackState
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ManagerError(Exception):
    """Raised when manager operation fails"""
    pass


class StickerPackManager:
    """Manages sticker pack lifecycle"""
    
    def __init__(self, base_path: Path, hub_url: str = "http://localhost:8888"):
        """
        Initialize pack manager.
        
        Args:
            base_path: Base directory for packs and configuration
            hub_url: URL of the pack hub server
        """
        self.base_path = Path(base_path)
        self.packs_dir = self.base_path / "packs"
        self.config_file = self.base_path / "config.json"
        
        self.hub_client = HubClient(hub_url)
        self.updater = PackUpdater(self.hub_client)
        
        self.packs: Dict[str, Pack] = {}
        self.manifests: Dict[str, PackManifest] = {}
        self.configs: Dict[str, PackConfig] = {}
        
        self._state_callbacks: List[Callable[[PackEvent], Any]] = []
    
    def on_pack_state_change(self, callback: Callable[[PackEvent], Any]) -> None:
        """
        Register a callback for pack state changes.
        
        Args:
            callback: Function to call on state change
        """
        self._state_callbacks.append(callback)
    
    def _emit_event(self, event: PackEvent) -> None:
        """
        Emit a pack event to all listeners.
        
        Args:
            event: PackEvent to emit
        """
        for callback in self._state_callbacks:
            try:
                callback(event)
            except Exception as e:
                pass  # Silently ignore callback errors
    
    async def reload(self) -> None:
        """
        Reload all packs from disk.
        Discovers packs in the packs directory and loads their manifests.
        """
        self.packs.clear()
        self.manifests.clear()
        self.configs.clear()
        
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan packs directory
        for pack_dir in self.packs_dir.iterdir():
            if pack_dir.is_dir() and not pack_dir.name.startswith("."):
                await self._load_pack(pack_dir)
        
        # Load configuration
        await self._load_config()
    
    async def _load_pack(self, pack_dir: Path) -> None:
        """
        Load a single pack from directory.
        
        Args:
            pack_dir: Path to pack directory
        """
        pack_name = pack_dir.name
        self._emit_event(PackEvent(pack_name, PackState.LOADING))
        
        try:
            pack = Pack(pack_dir)
            manifest = await pack.load_manifest()
            
            # Discover stickers
            stickers = await pack.discover_stickers()
            manifest.stickers = stickers
            
            self.packs[pack_name] = pack
            self.manifests[pack_name] = manifest
            
            self._emit_event(PackEvent(pack_name, PackState.LOADED))
        
        except Exception as e:
            self._emit_event(PackEvent(pack_name, PackState.ERROR, str(e)))
    
    async def _load_config(self) -> None:
        """Load configuration from file"""
        if not self.config_file.exists():
            return
        
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            packs_config = data.get("packs", {})
            for pack_name, config_data in packs_config.items():
                config = PackConfig.from_dict(config_data)
                self.configs[pack_name] = config
        
        except Exception:
            pass  # Silently ignore config load errors
    
    async def _save_config(self) -> None:
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "packs": {
                name: config.to_dict()
                for name, config in self.configs.items()
            }
        }
        
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def get_pack(self, pack_name: str) -> Optional[Pack]:
        """
        Get a loaded pack.
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            Pack object or None if not found
        """
        return self.packs.get(pack_name)
    
    def get_manifest(self, pack_name: str) -> Optional[PackManifest]:
        """
        Get manifest for a pack.
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            PackManifest or None if not found
        """
        return self.manifests.get(pack_name)
    
    def get_config(self, pack_name: str) -> Optional[PackConfig]:
        """
        Get configuration for a pack.
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            PackConfig or None if not found
        """
        return self.configs.get(pack_name)
    
    def list_packs(self) -> List[str]:
        """
        List all loaded pack names.
        
        Returns:
            Sorted list of pack names
        """
        return sorted(self.packs.keys())
    
    def list_manifests(self) -> List[PackManifest]:
        """
        List all pack manifests.
        
        Returns:
            List of PackManifest objects
        """
        return [self.manifests[name] for name in self.list_packs()]
    
    async def install_pack(
        self,
        pack_info: HubPackInfo,
        pack_name: Optional[str] = None,
        progress_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """
        Install a pack from the hub.
        
        Args:
            pack_info: HubPackInfo object
            pack_name: Name for installed pack (if None, uses pack_info.name)
            progress_callback: Optional callback for progress updates
            
        Raises:
            ManagerError: If installation fails
        """
        final_name = pack_name or pack_info.name
        self._emit_event(PackEvent(final_name, PackState.INSTALLING))
        
        try:
            temp_dir = self.base_path / ".temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Download pack
            if progress_callback:
                progress_callback(f"Downloading {pack_info.display_name}...")
            
            pack_zip = await self.updater.download_pack(pack_info, temp_dir, progress_callback)
            
            # Install pack
            install_dir = await self.updater.install_pack(
                pack_zip,
                self.packs_dir,
                final_name,
                progress_callback,
            )
            
            # Remove zip
            pack_zip.unlink(missing_ok=True)
            
            # Load the installed pack
            await self._load_pack(install_dir)
            
            self._emit_event(PackEvent(final_name, PackState.INSTALLED))
        
        except Exception as e:
            self._emit_event(PackEvent(final_name, PackState.ERROR, str(e)))
            raise ManagerError(f"Failed to install pack: {e}")
        
        finally:
            # Clean up temp directory
            temp_dir = self.base_path / ".temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def update_pack(
        self,
        pack_name: str,
        progress_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """
        Update an installed pack.
        
        Args:
            pack_name: Name of pack to update
            progress_callback: Optional callback for progress updates
            
        Raises:
            ManagerError: If update fails
        """
        self._emit_event(PackEvent(pack_name, PackState.UPDATING))
        
        try:
            manifest = self.get_manifest(pack_name)
            if not manifest or not manifest.url:
                raise ManagerError(f"No update URL for pack: {pack_name}")
            
            # Get hub info
            hub_pack = await self.hub_client.fetch_pack_info(pack_name)
            if not hub_pack:
                raise ManagerError(f"Pack not found in hub: {pack_name}")
            
            # Check if update available
            if not await self.updater.check_update_available(pack_name, manifest.version):
                if progress_callback:
                    progress_callback("Pack is already up to date")
                return
            
            # Download and install update
            temp_dir = self.base_path / ".temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            pack_zip = await self.updater.download_pack(hub_pack, temp_dir, progress_callback)
            
            # Remove old pack
            old_pack_dir = self.packs_dir / pack_name
            if old_pack_dir.exists():
                shutil.rmtree(old_pack_dir)
            
            # Install new version
            install_dir = await self.updater.install_pack(
                pack_zip,
                self.packs_dir,
                pack_name,
                progress_callback,
            )
            
            # Remove zip
            pack_zip.unlink(missing_ok=True)
            
            # Load the updated pack
            await self._load_pack(install_dir)
            
            self._emit_event(PackEvent(pack_name, PackState.UPDATED))
        
        except Exception as e:
            self._emit_event(PackEvent(pack_name, PackState.ERROR, str(e)))
            raise ManagerError(f"Failed to update pack: {e}")
        
        finally:
            # Clean up temp directory
            temp_dir = self.base_path / ".temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def delete_pack(self, pack_name: str) -> None:
        """
        Delete an installed pack.
        
        Args:
            pack_name: Name of pack to delete
            
        Raises:
            ManagerError: If deletion fails
        """
        self._emit_event(PackEvent(pack_name, PackState.DELETING))
        
        try:
            pack_dir = self.packs_dir / pack_name
            if pack_dir.exists():
                shutil.rmtree(pack_dir)
            
            # Remove from caches
            self.packs.pop(pack_name, None)
            self.manifests.pop(pack_name, None)
            self.configs.pop(pack_name, None)
            
            # Save config
            await self._save_config()
            
            self._emit_event(PackEvent(pack_name, PackState.DELETED))
        
        except Exception as e:
            self._emit_event(PackEvent(pack_name, PackState.ERROR, str(e)))
            raise ManagerError(f"Failed to delete pack: {e}")
    
    async def fetch_hub_packs(self, force_refresh: bool = False) -> List[HubPackInfo]:
        """
        Fetch available packs from hub.
        
        Args:
            force_refresh: Force refresh hub cache
            
        Returns:
            List of HubPackInfo objects
            
        Raises:
            ManagerError: If fetch fails
        """
        try:
            return await self.hub_client.fetch_packs(force_refresh)
        except HubError as e:
            raise ManagerError(f"Failed to fetch hub packs: {e}")
    
    async def get_hub_packs(self) -> List["HubPackReference"]:
        """
        Fetch available packs from GitHub-based hub.
        
        Returns:
            List of HubPackReference objects
            
        Raises:
            ManagerError: If fetch fails
        """
        from .hub import fetch_hub_index
        try:
            return await fetch_hub_index(self.hub_client.hub_url)
        except HubError as e:
            raise ManagerError(f"Failed to fetch hub packs: {e}")
    
    async def install_from_hub(self, pack_slug: str, github_raw_template: str = "https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}") -> bool:
        """
        Install a pack from GitHub-based hub using its slug.
        
        Args:
            pack_slug: Slug of the pack in the hub
            github_raw_template: Template for GitHub raw URLs
            
        Returns:
            True if installation was successful
            
        Raises:
            ManagerError: If installation fails
        """
        from .hub import fetch_hub_index, fetch_pack_manifest
        
        try:
            packs = await fetch_hub_index(self.hub_client.hub_url)
            
            pack_ref = None
            for ref in packs:
                if ref.slug == pack_slug:
                    pack_ref = ref
                    break
            
            if not pack_ref:
                raise ManagerError(f"Pack not found in hub: {pack_slug}")
            
            manifest = await fetch_pack_manifest(pack_ref.source, github_raw_template)
            
            hub_pack_info = HubPackInfo(
                name=pack_ref.slug,
                display_name=manifest.get("display_name", pack_ref.slug),
                description=manifest.get("description", ""),
                url="",
                version=manifest.get("version", "1.0.0"),
                author=manifest.get("author", "Unknown"),
            )
            
            await self.install_pack(hub_pack_info, pack_slug)
            return True
        
        except HubError as e:
            raise ManagerError(f"Failed to install pack from hub: {e}")
        except Exception as e:
            raise ManagerError(f"Unexpected error installing pack from hub: {e}")


def create_pack_manager(base_path: Path, hub_url: str = "http://localhost:8888") -> StickerPackManager:
    """
    Factory function to create a StickerPackManager.
    
    Args:
        base_path: Base directory for packs
        hub_url: Hub server URL
        
    Returns:
        StickerPackManager instance
    """
    return StickerPackManager(base_path, hub_url)
