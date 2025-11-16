"""
Individual sticker pack operations.
Handles loading, validation, and manipulation of a single pack.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import PackManifest, StickerInfo, FileSource


class PackError(Exception):
    """Raised when pack operation fails"""
    pass


class Pack:
    """Represents a single sticker pack"""
    
    MANIFEST_FILE = "metadata.json"
    CONFIG_FILE = "config.json"
    STICKERS_DIR = "stickers"
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    
    def __init__(self, pack_dir: Path):
        """
        Initialize a pack from a directory.
        
        Args:
            pack_dir: Path to pack directory
        """
        self.pack_dir = Path(pack_dir)
        self.manifest: Optional[PackManifest] = None
        self.stickers_dir = self.pack_dir / self.STICKERS_DIR
    
    async def load_manifest(self) -> PackManifest:
        """
        Load and validate pack manifest.
        
        Returns:
            Loaded PackManifest
            
        Raises:
            PackError: If manifest is invalid or missing
        """
        manifest_file = self.pack_dir / self.MANIFEST_FILE
        
        if not manifest_file.exists():
            raise PackError(f"Manifest not found: {manifest_file}")
        
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.manifest = PackManifest.from_dict(data)
            
            # Validate required fields
            if not self.manifest.name:
                raise PackError("Pack name is required")
            if not self.manifest.display_name:
                raise PackError("Pack display_name is required")
            
            return self.manifest
        
        except json.JSONDecodeError as e:
            raise PackError(f"Invalid manifest JSON: {e}")
        except Exception as e:
            raise PackError(f"Failed to load manifest: {e}")
    
    async def discover_stickers(self) -> List[StickerInfo]:
        """
        Discover sticker files in the pack.
        
        Returns:
            List of discovered StickerInfo objects
        """
        stickers = []
        
        if not self.stickers_dir.exists():
            return stickers
        
        for sticker_file in sorted(self.stickers_dir.iterdir()):
            if sticker_file.is_file() and sticker_file.suffix.lower() in self.SUPPORTED_FORMATS:
                sticker = StickerInfo(
                    name=sticker_file.stem,
                    path=str(sticker_file.relative_to(self.pack_dir)),
                    file_source=FileSource.LOCAL,
                )
                stickers.append(sticker)
        
        return stickers
    
    async def save_manifest(self) -> None:
        """
        Save manifest to disk.
        
        Raises:
            PackError: If save fails
        """
        if not self.manifest:
            raise PackError("No manifest loaded")
        
        manifest_file = self.pack_dir / self.MANIFEST_FILE
        
        try:
            self.pack_dir.mkdir(parents=True, exist_ok=True)
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(self.manifest.to_dict(), f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            raise PackError(f"Failed to save manifest: {e}")
    
    async def validate(self) -> bool:
        """
        Validate pack structure and contents.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check manifest
            if not (self.pack_dir / self.MANIFEST_FILE).exists():
                return False
            
            # Load and validate manifest
            await self.load_manifest()
            
            # Check stickers directory exists
            if not self.stickers_dir.exists():
                return False
            
            # Check at least one sticker exists
            stickers = await self.discover_stickers()
            return len(stickers) > 0
        
        except Exception:
            return False
    
    def get_sticker_path(self, sticker_name: str) -> Optional[Path]:
        """
        Get full path to a sticker file.
        
        Args:
            sticker_name: Name of sticker (without extension)
            
        Returns:
            Path to sticker file or None if not found
        """
        for sticker_file in self.stickers_dir.iterdir():
            if sticker_file.stem == sticker_name and sticker_file.suffix.lower() in self.SUPPORTED_FORMATS:
                return sticker_file
        return None
    
    def get_sticker_bytes(self, sticker_name: str) -> Optional[bytes]:
        """
        Read sticker file as bytes.
        
        Args:
            sticker_name: Name of sticker (without extension)
            
        Returns:
            Sticker file bytes or None if not found
        """
        sticker_path = self.get_sticker_path(sticker_name)
        if sticker_path:
            return sticker_path.read_bytes()
        return None
    
    async def list_stickers(self) -> List[str]:
        """
        List all sticker names in the pack.
        
        Returns:
            Sorted list of sticker names
        """
        stickers = await self.discover_stickers()
        return sorted([s.name for s in stickers])
    
    def __repr__(self) -> str:
        """String representation"""
        manifest_name = self.manifest.name if self.manifest else "unknown"
        return f"Pack({manifest_name})"
