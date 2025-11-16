"""
Sticker rendering utilities using Skia.
Handles drawing individual stickers with parameters and effects.
"""

import skia
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from .tools import FontCollection, SurfaceManager, DrawingHelpers, load_image_from_path, scale_image


@dataclass
class StickerParams:
    """Parameters for sticker rendering."""
    base_image: Optional[Path] = None
    overlay_text: Optional[str] = None
    text_color: Tuple[int, int, int, int] = (0, 0, 0, 255)
    background_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    font_size: float = 16.0
    font_family: Optional[str] = None
    width: int = 512
    height: int = 512
    padding: int = 16


class StickerRenderer:
    """Renders stickers with configurable parameters."""
    
    def __init__(self):
        """Initialize sticker renderer."""
        self.font_collection = FontCollection()
    
    def render_sticker(self, params: StickerParams) -> bytes:
        """
        Render a sticker with given parameters.
        
        Args:
            params: StickerParams configuration
            
        Returns:
            PNG image bytes
        """
        # Create surface
        surface = SurfaceManager.create_raster_surface(params.width, params.height)
        canvas = surface.getCanvas()
        
        # Fill background
        background_rect = skia.Rect.MakeWH(params.width, params.height)
        DrawingHelpers.fill_rect(canvas, background_rect, params.background_color)
        
        # Draw base image if provided
        if params.base_image and params.base_image.exists():
            self._draw_base_image(canvas, params)
        
        # Draw overlay text if provided
        if params.overlay_text:
            self._draw_overlay_text(canvas, params)
        
        # Return PNG bytes
        return SurfaceManager.get_png_bytes(surface)
    
    def render_sticker_to_file(self, params: StickerParams, output_path: Path) -> bool:
        """
        Render a sticker and save to file.
        
        Args:
            params: StickerParams configuration
            output_path: Path where image should be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            surface = SurfaceManager.create_raster_surface(params.width, params.height)
            canvas = surface.getCanvas()
            
            # Fill background
            background_rect = skia.Rect.MakeWH(params.width, params.height)
            DrawingHelpers.fill_rect(canvas, background_rect, params.background_color)
            
            # Draw base image if provided
            if params.base_image and params.base_image.exists():
                self._draw_base_image(canvas, params)
            
            # Draw overlay text if provided
            if params.overlay_text:
                self._draw_overlay_text(canvas, params)
            
            # Save to file
            if output_path.suffix.lower() == '.jpg' or output_path.suffix.lower() == '.jpeg':
                SurfaceManager.save_jpeg(surface, output_path)
            else:
                SurfaceManager.save_png(surface, output_path)
            
            return True
        except Exception:
            return False
    
    def _draw_base_image(self, canvas: skia.Canvas, params: StickerParams) -> None:
        """
        Draw base image on canvas.
        
        Args:
            canvas: Skia Canvas to draw on
            params: StickerParams configuration
        """
        image = load_image_from_path(params.base_image)
        if not image:
            return
        
        # Scale image to fit within bounds
        max_size = params.width - 2 * params.padding
        scaled_image = scale_image(image, max_size, max_size)
        
        # Center image
        x = (params.width - scaled_image.width()) / 2
        y = (params.height - scaled_image.height()) / 2
        
        canvas.drawImage(scaled_image, x, y)
    
    def _draw_overlay_text(self, canvas: skia.Canvas, params: StickerParams) -> None:
        """
        Draw overlay text on canvas.
        
        Args:
            canvas: Skia Canvas to draw on
            params: StickerParams configuration
        """
        font = self.font_collection.create_font(params.font_family, params.font_size)
        
        # Draw text at bottom with padding
        y = params.height - params.padding - 10
        x = params.padding
        
        DrawingHelpers.draw_text(canvas, params.overlay_text, x, y, font, params.text_color)


def create_simple_sticker(width: int = 256, height: int = 256, 
                         background_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                         text: Optional[str] = None,
                         text_color: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> bytes:
    """
    Create a simple sticker with text.
    
    Args:
        width: Width in pixels
        height: Height in pixels
        background_color: RGBA background color
        text: Optional text to draw
        text_color: RGBA text color
        
    Returns:
        PNG image bytes
    """
    params = StickerParams(
        width=width,
        height=height,
        background_color=background_color,
        overlay_text=text,
        text_color=text_color
    )
    
    renderer = StickerRenderer()
    return renderer.render_sticker(params)
