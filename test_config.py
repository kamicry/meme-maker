"""Tests for meme_stickers.config colour utilities and config wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from meme_stickers.config import Config, resolve_color_to_tuple


def test_resolve_color_hex_short_form():
    """#RGB should expand to full RGBA with alpha 255."""

    assert resolve_color_to_tuple("#abc") == (170, 187, 204, 255)


def test_resolve_color_hex_with_alpha():
    """#RRGGBBAA should keep the specified alpha value."""

    assert resolve_color_to_tuple("#11223344") == (17, 34, 51, 68)


def test_resolve_color_sequence_rgb():
    """RGB sequences should default the alpha channel to 255."""

    assert resolve_color_to_tuple((10, 20, 30)) == (10, 20, 30, 255)


def test_resolve_color_sequence_rgba():
    """RGBA sequences should be returned unchanged."""

    assert resolve_color_to_tuple([10, 20, 30, 40]) == (10, 20, 30, 40)


def test_resolve_color_invalid_string():
    """Invalid strings should raise a ValueError."""

    try:
        resolve_color_to_tuple("not-a-colour")
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for invalid colour")


def test_resolve_color_invalid_sequence_size():
    """Sequences with the wrong length should raise a ValueError."""

    try:
        resolve_color_to_tuple((255, 255))
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for invalid colour sequence")


def test_config_from_mapping_normalises_values():
    """Config.from_mapping should coerce types and normalise colours."""

    config = Config.from_mapping(
        {
            "proxy": "",
            "auto_update": "true",
            "max_concurrent_downloads": "5",
            "render_text_color": "#00ff00",
            "render_shadow_color": (16, 16, 16, 128),
        }
    )

    assert config.proxy is None
    assert config.auto_update is True
    assert config.max_concurrent_downloads == 5
    assert config.render_text_color == (0, 255, 0, 255)
    assert config.render_shadow_color == (16, 16, 16, 128)


def test_config_from_mapping_invalid_bool():
    """Invalid boolean strings should raise a ValueError."""

    try:
        Config.from_mapping({"auto_update": "definitely"})
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for invalid boolean value")


def test_config_from_mapping_invalid_colour():
    """Invalid colour inputs inside configuration should raise a ValueError."""

    try:
        Config.from_mapping({"render_text_color": "blue"})
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for invalid colour")
