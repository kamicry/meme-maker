"""Meme Stickers - AstrBot plugin for sticker pack management and rendering."""

from .config import Config, ConfigWrapper, ColorTuple, resolve_color_to_tuple
from .consts import PLUGIN_NAME

__all__ = [
    "__version__",
    "Config",
    "ConfigWrapper",
    "ColorTuple",
    "resolve_color_to_tuple",
    "PLUGIN_NAME",
]

__version__ = "2.0.0"
