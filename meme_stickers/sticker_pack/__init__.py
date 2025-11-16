"""
Sticker pack management module.
Provides models, pack operations, hub access, and manager orchestration.
"""

from .models import (
    FileSource,
    StickerInfo,
    GridSettings,
    PackManifest,
    PackConfig,
    HubPackInfo,
)
from .pack import Pack, PackError
from .hub import HubClient, HubError
from .update import PackUpdater, UpdateError
from .manager import (
    StickerPackManager,
    PackState,
    PackEvent,
    ManagerError,
    create_pack_manager,
)

__all__ = [
    "FileSource",
    "StickerInfo",
    "GridSettings",
    "PackManifest",
    "PackConfig",
    "HubPackInfo",
    "Pack",
    "PackError",
    "HubClient",
    "HubError",
    "PackUpdater",
    "UpdateError",
    "StickerPackManager",
    "PackState",
    "PackEvent",
    "ManagerError",
    "create_pack_manager",
]
