# Meme Stickers Draw Module

Skia-based rendering utilities for generating sticker previews, grids, and help images in AstrBot.

## Overview

This module provides a platform-agnostic rendering engine for creating and manipulating images using the Skia graphics library. All drawing operations are designed to work without NoneBot dependencies and integrate seamlessly with AstrBot's message chain system.

## Modules

### tools.py - Core Drawing Utilities

#### FontCollection
Manages Skia fonts with fallback support for cross-platform compatibility.

**Features:**
- Automatic font discovery with fallback chain
- Support for CJK fonts (Noto Sans CJK SC)
- Graceful degradation to system defaults

**System Font Prerequisites:**
- Linux: DejaVu fonts, Liberation fonts
- macOS: Noto Sans fonts (via Homebrew)
- Windows: Arial, Verdana (included)

```python
from meme_stickers.draw import FontCollection

font_collection = FontCollection()
font = font_collection.create_font("Noto Sans", 16.0)
```

#### SurfaceManager
Creates and manages Skia surfaces with PNG/JPEG encoding support.

**Features:**
- Raster surface creation
- PNG encoding with quality parameter
- JPEG encoding with configurable quality
- Raw bytes output for MessageChain integration

```python
from meme_stickers.draw import SurfaceManager
from pathlib import Path

surface = SurfaceManager.create_raster_surface(512, 512)
canvas = surface.getCanvas()

# Get PNG bytes for AstrBot MessageChain
png_bytes = SurfaceManager.get_png_bytes(surface)

# Or save to file
output_path = Path("output.png")
SurfaceManager.save_png(surface, output_path)
```

#### DrawingHelpers
Common drawing operations (rectangles, text, circles, lines).

```python
from meme_stickers.draw import DrawingHelpers, SurfaceManager, FontCollection
import skia

surface = SurfaceManager.create_raster_surface(256, 256)
canvas = surface.getCanvas()
font_collection = FontCollection()
font = font_collection.create_font(None, 14.0)

# Fill rectangle with color
rect = skia.Rect.MakeWH(100, 100)
DrawingHelpers.fill_rect(canvas, rect, (255, 0, 0, 255))

# Draw text
DrawingHelpers.draw_text(canvas, "Hello", 10, 50, font, (0, 0, 0, 255))

# Draw circle
DrawingHelpers.draw_circle(canvas, 128, 128, 50, (0, 255, 0, 255))

# Draw line
DrawingHelpers.draw_line(canvas, 0, 0, 100, 100, 2.0, (0, 0, 255, 255))
```

### sticker.py - Sticker Rendering

#### StickerParams
Configuration dataclass for sticker rendering.

```python
from meme_stickers.draw import StickerParams
from pathlib import Path

params = StickerParams(
    base_image=Path("base.png"),
    overlay_text="Hello World",
    text_color=(0, 0, 0, 255),
    background_color=(255, 255, 255, 255),
    font_size=16.0,
    font_family="Noto Sans",
    width=512,
    height=512,
    padding=16
)
```

#### StickerRenderer
Renders stickers with configurable base images and overlay text.

```python
from meme_stickers.draw import StickerRenderer, StickerParams
from pathlib import Path

renderer = StickerRenderer()

# Render to bytes
png_bytes = renderer.render_sticker(params)

# Or render to file
output_path = Path("sticker.png")
renderer.render_sticker_to_file(params, output_path)
```

#### Helper Functions

```python
from meme_stickers.draw import create_simple_sticker

# Create a simple sticker with text
png_bytes = create_simple_sticker(
    width=256,
    height=256,
    background_color=(200, 200, 255, 255),
    text="Test",
    text_color=(255, 0, 0, 255)
)
```

### grid.py - Grid Rendering

#### GridRenderer
Renders grids of sticker images with optional titles.

```python
from meme_stickers.draw import GridRenderer
from pathlib import Path

renderer = GridRenderer()

# Render grid with images
image_paths = [Path("sticker1.png"), Path("sticker2.png")]
png_bytes = renderer.render_grid(image_paths, cols=4, title="Sticker Grid")

# Or render to file
output_path = Path("grid.png")
renderer.render_grid_to_file(image_paths, output_path, cols=4, title="Grid")
```

#### Helper Functions

```python
from meme_stickers.draw import create_simple_grid

# Create a simple placeholder grid
png_bytes = create_simple_grid(
    num_cells=9,
    cell_color=(200, 200, 255, 255),
    title="Simple Grid"
)
```

### pack_list.py - Pack List Rendering

#### PackListRenderer
Renders pack information and help images.

```python
from meme_stickers.draw import PackListRenderer

renderer = PackListRenderer()

# Render pack list
packs = ["pack1", "pack2", "pack3"]
descriptions = ["Description 1", "Description 2", "Description 3"]
png_bytes = renderer.render_pack_list(packs, descriptions, "Available Packs")

# Render help image
commands = [
    ("/meme list", "List available packs"),
    ("/meme install <name>", "Install a pack"),
    ("/meme delete <name>", "Delete a pack"),
]
help_bytes = renderer.render_help_image(commands, "Meme Commands")

# Render pack details
details_bytes = renderer.render_pack_details(
    name="test_pack",
    display_name="Test Pack",
    description="A test sticker pack",
    version="1.0.0",
    author="Pack Author",
    num_stickers=10
)
```

#### Helper Functions

```python
from meme_stickers.draw import create_help_text_image

# Create a text-based help image
text = "Line 1\nLine 2\nLine 3"
png_bytes = create_help_text_image(text, title="Information")
```

## Integration with AstrBot

All modules are designed to produce raw bytes suitable for AstrBot's MessageChain image system.

```python
from astrbot.api import MessageChain

# Create image bytes
from meme_stickers.draw import create_simple_sticker
png_bytes = create_simple_sticker(width=256, height=256)

# Use in MessageChain
message = MessageChain().image(data=png_bytes)
```

## System Requirements

### Runtime Dependencies
- skia-python >= 129.0.0
- Pillow >= 10.0.0

### System Packages (Linux)
```bash
sudo apt-get install libgles2-mesa-dev libgl1-mesa-dev libegl1-mesa-dev
```

### System Packages (macOS)
```bash
brew install glfw3 gl3w libegl
```

### System Packages (Windows)
- OpenGL libraries are typically pre-installed
- May require Visual C++ runtime

## Supported Image Formats

- **Input**: PNG, JPEG, GIF, WebP
- **Output**: PNG, JPEG

## Color Format

All colors are specified as RGBA tuples with values 0-255:
- Red: (255, 0, 0, 255)
- Green: (0, 255, 0, 255)
- Blue: (0, 0, 255, 255)
- Semi-transparent: (0, 0, 0, 128)

## Performance Notes

- Surface creation is relatively fast (~1-5ms)
- Font loading is cached for performance
- PNG encoding is slower than JPEG (use JPEG for speed-critical operations)
- Grid rendering scales with number of images (linear complexity)

## Testing

Comprehensive test suite available:

```bash
python test_draw.py
```

Tests verify:
- Module imports without NoneBot dependencies
- PNG/JPEG encoding produces valid headers
- Font collection handles missing fonts gracefully
- All rendering functions produce bytes output
- File I/O operations work correctly

## Architecture Notes

### No NoneBot Dependencies
This module is completely independent of NoneBot. All filesystem access uses `Path` objects passed at call time, with no hardcoded paths or environment variable dependencies.

### Platform-Agnostic Font Discovery
The FontCollection class implements a fallback chain approach for fonts:
1. Attempt to load requested font
2. Try common fallback fonts (DejaVu, Liberation, Noto, Ubuntu)
3. Fall back to system default

### Memory Efficiency
All rendering operations return bytes directly, avoiding unnecessary file I/O. Surfaces are created on-demand and can be garbage collected immediately after encoding.

### Error Handling
All functions gracefully handle missing images, fonts, and file I/O errors. Failures return None or False, never raise exceptions in user-facing functions.

## Examples

### Complete Sticker Generation Pipeline

```python
from pathlib import Path
from meme_stickers.draw import StickerRenderer, StickerParams, GridRenderer

# Create individual stickers
renderer = StickerRenderer()
params = StickerParams(
    overlay_text="My Sticker",
    background_color=(255, 255, 255, 255)
)

sticker_bytes = renderer.render_sticker(params)

# Create a grid of stickers
grid_renderer = GridRenderer()
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

sticker_path = output_dir / "sticker.png"
sticker_path.write_bytes(sticker_bytes)

grid_bytes = grid_renderer.render_grid(
    [sticker_path],
    cols=1,
    title="My Stickers"
)

grid_path = output_dir / "grid.png"
grid_path.write_bytes(grid_bytes)
```

### Help Image Generation

```python
from meme_stickers.draw import PackListRenderer

renderer = PackListRenderer()

# Generate help
commands = [
    ("/meme list", "Show available packs"),
    ("/meme install NAME", "Install a pack"),
]

help_bytes = renderer.render_help_image(commands, "Plugin Commands")

# Use in AstrBot
yield event.image(data=help_bytes)
```

## License

Part of the Meme Stickers AstrBot Plugin. See repository LICENSE file for details.
