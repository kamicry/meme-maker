"""
Skia drawing utilities for sticker rendering.
Provides font management, surface creation, and image encoding utilities.
"""

import skia
from pathlib import Path
from typing import Optional, Tuple, List
import io


class FontCollection:
    """Manages Skia font collection with fallback fonts."""
    
    def __init__(self):
        """Initialize font collection with system fonts and fallbacks."""
        self.font_mgr = skia.FontMgr.RefDefault()
        self.typeface_cache = {}
        self._setup_fallback_fonts()
    
    def _setup_fallback_fonts(self) -> None:
        """Setup fallback font list for platform-agnostic font discovery."""
        # Common fallback fonts across platforms
        self.fallback_fonts = [
            "Noto Sans CJK SC",  # Chinese support
            "Noto Sans",
            "DejaVu Sans",
            "Liberation Sans",
            "Ubuntu",
            "Arial",
            "Helvetica",
            "Verdana",
        ]
    
    def get_typeface(self, font_family: Optional[str] = None, size: float = 14.0) -> Tuple[skia.Typeface, float]:
        """
        Get a typeface with fallback support.
        
        Args:
            font_family: Preferred font family name
            size: Font size in points
            
        Returns:
            Tuple of (Typeface, size)
        """
        if font_family and font_family in self.typeface_cache:
            return self.typeface_cache[font_family], size
        
        # Try requested font first
        if font_family:
            typeface = self.font_mgr.matchFamilyStyle(font_family, skia.FontStyle())
            if typeface:
                self.typeface_cache[font_family] = typeface
                return typeface, size
        
        # Try fallback fonts
        for fallback in self.fallback_fonts:
            typeface = self.font_mgr.matchFamilyStyle(fallback, skia.FontStyle())
            if typeface:
                self.typeface_cache[fallback] = typeface
                return typeface, size
        
        # Return default font
        default_typeface = skia.Typeface.MakeDefault()
        return default_typeface, size
    
    def create_font(self, font_family: Optional[str] = None, size: float = 14.0) -> skia.Font:
        """
        Create a Skia Font with fallback support.
        
        Args:
            font_family: Preferred font family name
            size: Font size in points
            
        Returns:
            Skia Font object
        """
        typeface, font_size = self.get_typeface(font_family, size)
        return skia.Font(typeface, font_size)


class SurfaceManager:
    """Manages Skia surface creation and image encoding."""
    
    @staticmethod
    def create_surface(width: int, height: int, color_type: skia.ColorType = skia.kRGBA_8888_ColorType) -> skia.Surface:
        """
        Create a Skia surface.
        
        Args:
            width: Surface width in pixels
            height: Surface height in pixels
            color_type: Color type for the surface
            
        Returns:
            Skia Surface object
        """
        return skia.Surface.MakeRasterDirect(
            skia.ImageInfo.Make(width, height, color_type),
            bytearray(width * height * 4)
        )
    
    @staticmethod
    def create_raster_surface(width: int, height: int) -> skia.Surface:
        """
        Create a raster surface (simplest approach).
        
        Args:
            width: Surface width in pixels
            height: Surface height in pixels
            
        Returns:
            Skia Surface object
        """
        return skia.Surface.MakeRasterN32Premul(width, height)
    
    @staticmethod
    def save_png(surface: skia.Surface, output_path: Path) -> None:
        """
        Save surface as PNG image.
        
        Args:
            surface: Skia Surface to save
            output_path: Path where PNG should be saved
        """
        image = surface.makeImageSnapshot()
        data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        output_path.write_bytes(data.bytes())
    
    @staticmethod
    def save_jpeg(surface: skia.Surface, output_path: Path, quality: int = 90) -> None:
        """
        Save surface as JPEG image.
        
        Args:
            surface: Skia Surface to save
            output_path: Path where JPEG should be saved
            quality: JPEG quality (0-100)
        """
        image = surface.makeImageSnapshot()
        data = image.encodeToData(skia.EncodedImageFormat.kJPEG, quality)
        output_path.write_bytes(data.bytes())
    
    @staticmethod
    def get_png_bytes(surface: skia.Surface) -> bytes:
        """
        Get PNG bytes from surface without writing to disk.
        
        Args:
            surface: Skia Surface
            
        Returns:
            PNG image bytes
        """
        image = surface.makeImageSnapshot()
        data = image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        return data.bytes()
    
    @staticmethod
    def get_jpeg_bytes(surface: skia.Surface, quality: int = 90) -> bytes:
        """
        Get JPEG bytes from surface without writing to disk.
        
        Args:
            surface: Skia Surface
            quality: JPEG quality (0-100)
            
        Returns:
            JPEG image bytes
        """
        image = surface.makeImageSnapshot()
        data = image.encodeToData(skia.EncodedImageFormat.kJPEG, quality)
        return data.bytes()


class DrawingHelpers:
    """Helper functions for common drawing operations."""
    
    @staticmethod
    def fill_rect(canvas: skia.Canvas, rect: skia.Rect, color: Tuple[int, int, int, int]) -> None:
        """
        Draw a filled rectangle.
        
        Args:
            canvas: Skia Canvas to draw on
            rect: Rectangle bounds
            color: RGBA color tuple
        """
        paint = skia.Paint()
        paint.setColor(skia.Color4f(color[0]/255, color[1]/255, color[2]/255, color[3]/255))
        canvas.drawRect(rect, paint)
    
    @staticmethod
    def draw_text(canvas: skia.Canvas, text: str, x: float, y: float, font: skia.Font, 
                  color: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> None:
        """
        Draw text on canvas.
        
        Args:
            canvas: Skia Canvas to draw on
            text: Text to draw
            x: X coordinate
            y: Y coordinate
            font: Skia Font to use
            color: RGBA color tuple
        """
        paint = skia.Paint()
        paint.setColor(skia.Color4f(color[0]/255, color[1]/255, color[2]/255, color[3]/255))
        canvas.drawString(text, x, y, font, paint)
    
    @staticmethod
    def draw_circle(canvas: skia.Canvas, cx: float, cy: float, radius: float,
                    color: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> None:
        """
        Draw a filled circle.
        
        Args:
            canvas: Skia Canvas to draw on
            cx: Center X coordinate
            cy: Center Y coordinate
            radius: Circle radius
            color: RGBA color tuple
        """
        paint = skia.Paint()
        paint.setColor(skia.Color4f(color[0]/255, color[1]/255, color[2]/255, color[3]/255))
        canvas.drawCircle(cx, cy, radius, paint)
    
    @staticmethod
    def draw_line(canvas: skia.Canvas, x1: float, y1: float, x2: float, y2: float,
                  stroke_width: float = 1.0, color: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> None:
        """
        Draw a line.
        
        Args:
            canvas: Skia Canvas to draw on
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            stroke_width: Line width
            color: RGBA color tuple
        """
        paint = skia.Paint()
        paint.setColor(skia.Color4f(color[0]/255, color[1]/255, color[2]/255, color[3]/255))
        paint.setStrokeWidth(stroke_width)
        canvas.drawLine(x1, y1, x2, y2, paint)


def load_image_from_path(image_path: Path) -> Optional[skia.Image]:
    """
    Load an image from file path.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Skia Image or None if loading failed
    """
    if not image_path.exists():
        return None
    
    try:
        with open(image_path, 'rb') as f:
            data = f.read()
        return skia.Image.MakeFromEncoded(skia.Data.MakeWithoutCopy(data))
    except Exception:
        return None


def scale_image(image: skia.Image, target_width: int, target_height: int) -> skia.Image:
    """
    Scale an image to target dimensions.
    
    Args:
        image: Skia Image to scale
        target_width: Target width
        target_height: Target height
        
    Returns:
        Scaled Skia Image
    """
    surface = SurfaceManager.create_raster_surface(target_width, target_height)
    canvas = surface.getCanvas()
    
    src_rect = skia.Rect.MakeWH(image.width(), image.height())
    dst_rect = skia.Rect.MakeWH(target_width, target_height)
    canvas.drawImageRect(image, src_rect, dst_rect)
    
    return surface.makeImageSnapshot()
