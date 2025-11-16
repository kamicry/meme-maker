"""Configuration helpers for the Meme Stickers AstrBot plugin.

The original Meme Stickers project shipped a Pydantic model that relied on
NoneBot's configuration helpers (`get_plugin_config`,
`ensure_localstore_path_config`). AstrBot exposes configuration through the
`AstrBotConfig` object instead, so this module provides a lightweight wrapper
around that structure while keeping the familiar defaults and validation
behaviour.

Notes
-----
* AstrBot exposes the plugin data directory through ``Context.get_data_path``.
  Later tickets use this directory to persist downloaded sticker packs and
  cached renders. The wrapper implemented here stays focused on configuration,
  but the documentation is included to make the data path discoverable for
  future contributors.
* Colours are accepted either as hex strings (``#RGB``, ``#RRGGBB`` or
  ``#RRGGBBAA``) or as RGB(A) tuples. They are always normalised to an RGBA
  tuple so downstream drawing utilities can consume them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union, TYPE_CHECKING, cast
from collections.abc import Mapping as ABCMapping

from .consts import (
    DEFAULT_ACCENT_COLOR,
    DEFAULT_AUTO_UPDATE,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FORCE_UPDATE,
    DEFAULT_GITHUB_RAW_TEMPLATE,
    DEFAULT_GITHUB_RELEASE_TEMPLATE,
    DEFAULT_GRID_BACKGROUND_COLOR,
    DEFAULT_GRID_BORDER_COLOR,
    DEFAULT_GRID_TEXT_COLOR,
    DEFAULT_HUB_ENABLE,
    DEFAULT_HUB_URL,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_OUTLINE_COLOR,
    DEFAULT_PROMPT_TIMEOUT,
    DEFAULT_PROXY,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SHADOW_COLOR,
    DEFAULT_TEXT_COLOR,
    PLUGIN_NAME,
)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from astrbot.api.config import AstrBotConfig
else:  # pragma: no cover - fallback for test environments
    AstrBotConfig = Any  # type: ignore


ColorTuple = Tuple[int, int, int, int]
ColorValue = Union[str, Sequence[int]]

_HEX_DIGITS = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
               "a", "b", "c", "d", "e", "f", "A", "B", "C", "D", "E", "F"}

_COLOR_FIELD_NAMES = (
    "render_background_color",
    "render_text_color",
    "render_accent_color",
    "render_shadow_color",
    "render_outline_color",
    "grid_background_color",
    "grid_text_color",
    "grid_border_color",
)


def resolve_color_to_tuple(color: ColorValue) -> ColorTuple:
    """Normalise a colour value into an RGBA tuple.

    Args:
        color: The colour expressed either as a hex string (``#RGB``,
            ``#RGBA``, ``#RRGGBB`` or ``#RRGGBBAA``) or as a 3/4 element
            iterable of integers in the range ``0-255``.

    Returns:
        A tuple of ``(R, G, B, A)`` components, each within ``0-255``.

    Raises:
        ValueError: If the input cannot be interpreted as a valid colour.
    """

    if isinstance(color, str):
        value = color.strip()
        if not value.startswith("#"):
            raise ValueError(f"Unsupported colour format: {color!r}")

        hex_value = value[1:]
        if not hex_value:
            raise ValueError("Hex colour string cannot be empty")
        if not all(ch in _HEX_DIGITS for ch in hex_value):
            raise ValueError(f"Invalid hex colour string: {color!r}")

        if len(hex_value) in (3, 4):
            hex_value = "".join(ch * 2 for ch in hex_value)
        elif len(hex_value) not in (6, 8):
            raise ValueError(
                "Hex colour must be either #RGB, #RGBA, #RRGGBB or #RRGGBBAA"
            )

        if len(hex_value) == 6:
            hex_value += "FF"

        try:
            components = tuple(
                int(hex_value[i : i + 2], 16) for i in range(0, len(hex_value), 2)
            )
        except ValueError as exc:  # pragma: no cover - guarded above, safety net
            raise ValueError(f"Invalid hex colour string: {color!r}") from exc

        if len(components) != 4:
            raise ValueError("Hex colour must resolve to four channels")

        return cast(ColorTuple, components)

    if isinstance(color, Sequence):
        try:
            components = tuple(int(x) for x in color)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Colour sequence must contain integers: {color!r}") from exc

        if len(components) not in (3, 4):
            raise ValueError("Colour sequence must have 3 (RGB) or 4 (RGBA) values")

        if any(component < 0 or component > 255 for component in components):
            raise ValueError("Colour components must be between 0 and 255")

        if len(components) == 3:
            components = components + (255,)

        return cast(ColorTuple, components)

    raise ValueError(f"Unsupported colour value: {color!r}")


@dataclass(frozen=True)
class Config:
    """Resolved configuration for the Meme Stickers plugin."""

    plugin_name: str = PLUGIN_NAME
    hub_url: str = DEFAULT_HUB_URL
    hub_enable: bool = DEFAULT_HUB_ENABLE
    proxy: Optional[str] = DEFAULT_PROXY
    github_raw_template: str = DEFAULT_GITHUB_RAW_TEMPLATE
    github_release_template: str = DEFAULT_GITHUB_RELEASE_TEMPLATE
    max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENCY
    request_timeout: float = DEFAULT_HTTP_TIMEOUT
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    retry_delay: float = DEFAULT_RETRY_DELAY
    retry_backoff: float = DEFAULT_RETRY_BACKOFF
    auto_update: bool = DEFAULT_AUTO_UPDATE
    force_update: bool = DEFAULT_FORCE_UPDATE
    prompt_timeout: float = DEFAULT_PROMPT_TIMEOUT
    render_font_family: str = DEFAULT_FONT_FAMILY
    render_font_size: int = DEFAULT_FONT_SIZE
    render_background_color: ColorTuple = field(default_factory=lambda: DEFAULT_BACKGROUND_COLOR)
    render_text_color: ColorTuple = field(default_factory=lambda: DEFAULT_TEXT_COLOR)
    render_accent_color: ColorTuple = field(default_factory=lambda: DEFAULT_ACCENT_COLOR)
    render_shadow_color: ColorTuple = field(default_factory=lambda: DEFAULT_SHADOW_COLOR)
    render_outline_color: ColorTuple = field(default_factory=lambda: DEFAULT_OUTLINE_COLOR)
    grid_background_color: ColorTuple = field(default_factory=lambda: DEFAULT_GRID_BACKGROUND_COLOR)
    grid_text_color: ColorTuple = field(default_factory=lambda: DEFAULT_GRID_TEXT_COLOR)
    grid_border_color: ColorTuple = field(default_factory=lambda: DEFAULT_GRID_BORDER_COLOR)

    @classmethod
    def from_mapping(
        cls,
        mapping: Optional[Mapping[str, Any]] = None,
        *,
        plugin_name: str = PLUGIN_NAME,
        overrides: Optional[Mapping[str, Any]] = None,
    ) -> "Config":
        """Create a :class:`Config` instance from a mapping.

        Args:
            mapping: Base configuration mapping obtained from ``AstrBotConfig``.
            plugin_name: Name of the plugin the configuration belongs to.
            overrides: Optional mapping of override values (takes precedence over
                ``mapping``).

        Returns:
            A fully realised :class:`Config` instance.

        Raises:
            ValueError: If the provided configuration is invalid.
        """

        combined: Dict[str, Any] = {}
        if mapping:
            combined.update(dict(mapping))
        if overrides:
            combined.update(dict(overrides))

        def _get_optional_str(name: str, default: Optional[str]) -> Optional[str]:
            value = combined.get(name, default)
            if value is None:
                return default
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return None
                return stripped
            return str(value)

        def _get_required_str(name: str, default: str) -> str:
            value = combined.get(name, default)
            if value is None:
                value = default
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    raise ValueError(f"{name} cannot be empty")
                return stripped
            return str(value)

        def _get_int(name: str, default: int, *, minimum: Optional[int] = None) -> int:
            value = combined.get(name, default)
            try:
                as_int = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be an integer") from exc
            if minimum is not None and as_int < minimum:
                raise ValueError(f"{name} must be >= {minimum}")
            return as_int

        def _get_float(name: str, default: float, *, minimum: Optional[float] = None) -> float:
            value = combined.get(name, default)
            try:
                as_float = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be a number") from exc
            if minimum is not None and as_float < minimum:
                raise ValueError(f"{name} must be >= {minimum}")
            return as_float

        def _get_bool(name: str, default: bool) -> bool:
            value = combined.get(name, default)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
                raise ValueError(f"{name} must be a boolean value")
            if isinstance(value, (int, float)):
                return bool(value)
            raise ValueError(f"{name} must be a boolean value")

        color_defaults: Dict[str, ColorTuple] = {
            "render_background_color": DEFAULT_BACKGROUND_COLOR,
            "render_text_color": DEFAULT_TEXT_COLOR,
            "render_accent_color": DEFAULT_ACCENT_COLOR,
            "render_shadow_color": DEFAULT_SHADOW_COLOR,
            "render_outline_color": DEFAULT_OUTLINE_COLOR,
            "grid_background_color": DEFAULT_GRID_BACKGROUND_COLOR,
            "grid_text_color": DEFAULT_GRID_TEXT_COLOR,
            "grid_border_color": DEFAULT_GRID_BORDER_COLOR,
        }

        resolved_colors: Dict[str, ColorTuple] = {}
        for field_name in _COLOR_FIELD_NAMES:
            if field_name in combined:
                resolved_colors[field_name] = resolve_color_to_tuple(combined[field_name])
            else:
                resolved_colors[field_name] = color_defaults[field_name]

        return cls(
            plugin_name=plugin_name,
            hub_url=_get_required_str("hub_url", DEFAULT_HUB_URL),
            hub_enable=_get_bool("hub_enable", DEFAULT_HUB_ENABLE),
            proxy=_get_optional_str("proxy", DEFAULT_PROXY),
            github_raw_template=_get_required_str(
                "github_raw_template", DEFAULT_GITHUB_RAW_TEMPLATE
            ),
            github_release_template=_get_required_str(
                "github_release_template", DEFAULT_GITHUB_RELEASE_TEMPLATE
            ),
            max_concurrent_downloads=_get_int(
                "max_concurrent_downloads", DEFAULT_MAX_CONCURRENCY, minimum=1
            ),
            request_timeout=_get_float("request_timeout", DEFAULT_HTTP_TIMEOUT, minimum=0.0),
            retry_attempts=_get_int("retry_attempts", DEFAULT_RETRY_ATTEMPTS, minimum=0),
            retry_delay=_get_float("retry_delay", DEFAULT_RETRY_DELAY, minimum=0.0),
            retry_backoff=_get_float("retry_backoff", DEFAULT_RETRY_BACKOFF, minimum=0.0),
            auto_update=_get_bool("auto_update", DEFAULT_AUTO_UPDATE),
            force_update=_get_bool("force_update", DEFAULT_FORCE_UPDATE),
            prompt_timeout=_get_float("prompt_timeout", DEFAULT_PROMPT_TIMEOUT, minimum=0.0),
            render_font_family=_get_required_str(
                "render_font_family", DEFAULT_FONT_FAMILY
            ),
            render_font_size=_get_int("render_font_size", DEFAULT_FONT_SIZE, minimum=1),
            render_background_color=resolved_colors["render_background_color"],
            render_text_color=resolved_colors["render_text_color"],
            render_accent_color=resolved_colors["render_accent_color"],
            render_shadow_color=resolved_colors["render_shadow_color"],
            render_outline_color=resolved_colors["render_outline_color"],
            grid_background_color=resolved_colors["grid_background_color"],
            grid_text_color=resolved_colors["grid_text_color"],
            grid_border_color=resolved_colors["grid_border_color"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Copiable representation of the configuration."""

        return {
            "plugin_name": self.plugin_name,
            "hub_url": self.hub_url,
            "hub_enable": self.hub_enable,
            "proxy": self.proxy,
            "github_raw_template": self.github_raw_template,
            "github_release_template": self.github_release_template,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "request_timeout": self.request_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "retry_backoff": self.retry_backoff,
            "auto_update": self.auto_update,
            "force_update": self.force_update,
            "prompt_timeout": self.prompt_timeout,
            "render_font_family": self.render_font_family,
            "render_font_size": self.render_font_size,
            "render_background_color": self.render_background_color,
            "render_text_color": self.render_text_color,
            "render_accent_color": self.render_accent_color,
            "render_shadow_color": self.render_shadow_color,
            "render_outline_color": self.render_outline_color,
            "grid_background_color": self.grid_background_color,
            "grid_text_color": self.grid_text_color,
            "grid_border_color": self.grid_border_color,
        }


class ConfigWrapper:
    """Bridge between :class:`AstrBotConfig` and :class:`Config`.

    The wrapper eagerly reads plugin-specific configuration from the
    ``AstrBotConfig`` instance and exposes both the raw mapping as well as the
    validated :class:`Config`. This mirrors the ergonomics of the original
    NoneBot-based implementation without depending on any of its helpers.
    """

    def __init__(
        self,
        astrbot_config: "AstrBotConfig",
        plugin_name: str = PLUGIN_NAME,
    ) -> None:
        self._astrbot_config = astrbot_config
        self.plugin_name = plugin_name
        self._raw_cache: Dict[str, Any] = {}
        self._config: Optional[Config] = None
        self.refresh()

    @property
    def raw(self) -> Dict[str, Any]:
        """Return a copy of the raw configuration mapping."""

        return dict(self._raw_cache)

    @property
    def config(self) -> Config:
        """Return the resolved :class:`Config` instance."""

        if self._config is None:
            self._config = Config.from_mapping(self._raw_cache, plugin_name=self.plugin_name)
        return self._config

    def refresh(self, *, overrides: Optional[Mapping[str, Any]] = None) -> None:
        """Reload configuration from the underlying :class:`AstrBotConfig`.

        Args:
            overrides: Optional mapping of values that should override the base
                configuration. These overrides are applied on each refresh call.
        """

        self._raw_cache = self._extract_plugin_config()
        if overrides:
            self._raw_cache.update(dict(overrides))
        self._config = Config.from_mapping(self._raw_cache, plugin_name=self.plugin_name)

    def apply_overrides(self, overrides: Mapping[str, Any]) -> Config:
        """Update the current configuration using the provided overrides."""

        self._raw_cache.update(dict(overrides))
        self._config = Config.from_mapping(self._raw_cache, plugin_name=self.plugin_name)
        return self._config

    def _extract_plugin_config(self) -> Dict[str, Any]:
        """Extract the plugin configuration from ``AstrBotConfig``.

        The method intentionally avoids NoneBot helpers and instead looks for
        dictionaries on ``AstrBotConfig`` that commonly host plugin data. The
        lookup order is:

        1. ``astrbot_config.plugins[plugin_name]`` if present
        2. ``astrbot_config.plugin_config[plugin_name]`` if present
        3. ``astrbot_config.config['plugins'][plugin_name]`` (dashboard export)
        4. ``astrbot_config.get(plugin_name)`` if the object implements ``get``

        All discovered mappings are merged, with later entries taking priority.
        """

        candidates: list[Mapping[str, Any]] = []

        def _maybe_add(mapping: Any) -> None:
            if isinstance(mapping, ABCMapping):
                candidates.append(mapping)

        plugins_section = getattr(self._astrbot_config, "plugins", None)
        if isinstance(plugins_section, ABCMapping):
            plugin_specific = plugins_section.get(self.plugin_name)
            _maybe_add(plugin_specific)

        plugin_config = getattr(self._astrbot_config, "plugin_config", None)
        if isinstance(plugin_config, ABCMapping):
            if self.plugin_name in plugin_config:
                _maybe_add(plugin_config.get(self.plugin_name))
            else:
                nested_plugins = plugin_config.get("plugins")
                if isinstance(nested_plugins, ABCMapping):
                    _maybe_add(nested_plugins.get(self.plugin_name))

        full_config = getattr(self._astrbot_config, "config", None)
        if isinstance(full_config, ABCMapping):
            nested_plugins = full_config.get("plugins")
            if isinstance(nested_plugins, ABCMapping):
                _maybe_add(nested_plugins.get(self.plugin_name))

        if hasattr(self._astrbot_config, "get"):
            try:
                candidate = self._astrbot_config.get(self.plugin_name)  # type: ignore[misc]
            except TypeError:
                candidate = None
            _maybe_add(candidate)

        merged: Dict[str, Any] = {}
        for mapping in candidates:
            merged.update(mapping)

        return merged

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - thin proxy
        """Delegate attribute access to the resolved :class:`Config`."""

        try:
            return getattr(self.config, item)
        except AttributeError as exc:  # pragma: no cover - pass-through
            raise AttributeError(item) from exc


__all__ = [
    "Config",
    "ConfigWrapper",
    "ColorTuple",
    "resolve_color_to_tuple",
]
