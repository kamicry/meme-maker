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
from .hub import (
    HubClient,
    HubError,
    GitHubSource,
    HubPackReference,
    HubIndex,
    fetch_hub_index,
    fetch_pack_manifest,
    construct_github_raw_url,
)
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
    "GitHubSource",
    "HubPackReference",
    "HubIndex",
    "fetch_hub_index",
    "fetch_pack_manifest",
    "construct_github_raw_url",
    "PackUpdater",
    "UpdateError",
    "StickerPackManager",
    "PackState",
    "PackEvent",
    "ManagerError",
    "create_pack_manager",
]
