"""Central constants used across the Meme Stickers plugin.

These defaults are largely derived from the original NoneBot implementation
but adjusted for the AstrBot environment. Keeping them in a single module
avoids circular imports and makes it straightforward to expose the values
through configuration utilities.
"""

from __future__ import annotations

from typing import Tuple

PLUGIN_NAME = "meme_stickers"

# Hub / network defaults
DEFAULT_HUB_URL = "http://localhost:8888"
DEFAULT_PROXY = None
DEFAULT_GITHUB_RAW_TEMPLATE = "https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
DEFAULT_GITHUB_RELEASE_TEMPLATE = (
    "https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"
)
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_HTTP_TIMEOUT = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1.5
DEFAULT_RETRY_BACKOFF = 2.0
DEFAULT_PROMPT_TIMEOUT = 60.0
DEFAULT_AUTO_UPDATE = False
DEFAULT_FORCE_UPDATE = False

# Rendering defaults
DEFAULT_FONT_FAMILY = "Noto Sans CJK SC"
DEFAULT_FONT_SIZE = 48
DEFAULT_BACKGROUND_COLOR: Tuple[int, int, int, int] = (255, 255, 255, 255)
DEFAULT_TEXT_COLOR: Tuple[int, int, int, int] = (34, 34, 34, 255)
DEFAULT_ACCENT_COLOR: Tuple[int, int, int, int] = (255, 102, 0, 255)
DEFAULT_SHADOW_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 128)
DEFAULT_OUTLINE_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 230)
DEFAULT_GRID_BACKGROUND_COLOR: Tuple[int, int, int, int] = (26, 26, 28, 240)
DEFAULT_GRID_TEXT_COLOR: Tuple[int, int, int, int] = (240, 240, 240, 255)
DEFAULT_GRID_BORDER_COLOR: Tuple[int, int, int, int] = (80, 80, 80, 255)
