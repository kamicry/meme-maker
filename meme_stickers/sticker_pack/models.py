"""
Sticker pack models and validation.
Defines pydantic models for pack manifests, configurations, and related data structures.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class FileSource(str, Enum):
    """Source of sticker file"""
    LOCAL = "local"
    REMOTE = "remote"
    BUILTIN = "builtin"


@dataclass
class StickerInfo:
    """Information about a single sticker"""
    name: str
    path: str
    file_source: FileSource = FileSource.LOCAL
    created_at: Optional[str] = None


@dataclass
class GridSettings:
    """Grid rendering settings for a pack"""
    columns: int = 3
    rows: int = 3
    cell_width: int = 200
    cell_height: int = 200
    background_color: str = "#FFFFFF"
    border_color: str = "#000000"
    border_width: int = 1


@dataclass
class PackManifest:
    """Pack manifest metadata (from metadata.json)"""
    name: str
    display_name: str
    description: str
    version: str
    author: str
    enabled: bool = True
    url: Optional[str] = None
    checksum: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    stickers: List[StickerInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "enabled": self.enabled,
            "url": self.url,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stickers": [
                {
                    "name": s.name,
                    "path": s.path,
                    "file_source": s.file_source.value,
                    "created_at": s.created_at,
                }
                for s in self.stickers
            ]
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PackManifest":
        """Create PackManifest from dictionary"""
        stickers = []
        for sticker_data in data.get("stickers", []):
            sticker = StickerInfo(
                name=sticker_data.get("name", ""),
                path=sticker_data.get("path", ""),
                file_source=FileSource(sticker_data.get("file_source", "local")),
                created_at=sticker_data.get("created_at"),
            )
            stickers.append(sticker)
        
        return PackManifest(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Unknown"),
            enabled=data.get("enabled", True),
            url=data.get("url"),
            checksum=data.get("checksum"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            stickers=stickers,
        )


@dataclass
class PackConfig:
    """Pack configuration (from config.json)"""
    name: str
    display_name: str
    description: str
    enabled: bool = True
    shortcuts: List[Dict[str, Any]] = field(default_factory=list)
    url: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    checksum: Optional[str] = None
    grid_settings: Optional[GridSettings] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "enabled": self.enabled,
            "shortcuts": self.shortcuts,
            "url": self.url,
            "version": self.version,
            "author": self.author,
            "checksum": self.checksum,
        }
        if self.grid_settings:
            result["grid_settings"] = {
                "columns": self.grid_settings.columns,
                "rows": self.grid_settings.rows,
                "cell_width": self.grid_settings.cell_width,
                "cell_height": self.grid_settings.cell_height,
                "background_color": self.grid_settings.background_color,
                "border_color": self.grid_settings.border_color,
                "border_width": self.grid_settings.border_width,
            }
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PackConfig":
        """Create PackConfig from dictionary"""
        grid_settings = None
        if "grid_settings" in data and data["grid_settings"]:
            gs = data["grid_settings"]
            grid_settings = GridSettings(
                columns=gs.get("columns", 3),
                rows=gs.get("rows", 3),
                cell_width=gs.get("cell_width", 200),
                cell_height=gs.get("cell_height", 200),
                background_color=gs.get("background_color", "#FFFFFF"),
                border_color=gs.get("border_color", "#000000"),
                border_width=gs.get("border_width", 1),
            )
        
        return PackConfig(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            shortcuts=data.get("shortcuts", []),
            url=data.get("url"),
            version=data.get("version"),
            author=data.get("author"),
            checksum=data.get("checksum"),
            grid_settings=grid_settings,
        )


@dataclass
class HubPackInfo:
    """Information about a pack in the hub"""
    name: str
    display_name: str
    description: str
    url: str
    version: str
    author: str
    size: Optional[int] = None
    preview_url: Optional[str] = None
    downloads: Optional[int] = None
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "author": self.author,
            "size": self.size,
            "preview_url": self.preview_url,
            "downloads": self.downloads,
            "checksum": self.checksum,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HubPackInfo":
        """Create HubPackInfo from dictionary"""
        return HubPackInfo(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Unknown"),
            size=data.get("size"),
            preview_url=data.get("preview_url"),
            downloads=data.get("downloads"),
            checksum=data.get("checksum"),
        )
