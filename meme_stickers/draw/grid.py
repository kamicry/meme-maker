"""
Sticker grid rendering utilities using Skia.
Handles drawing grids of stickers and preview layouts.
"""

import skia
from pathlib import Path
from typing import List, Optional, Tuple
from .tools import FontCollection, SurfaceManager, DrawingHelpers, load_image_from_path, scale_image


class GridRenderer:
    """Renders grids of stickers."""
    
    CELL_SIZE = 128
    PADDING = 8
    TITLE_HEIGHT = 40
    FONT_SIZE = 14.0
    
    def __init__(self):
        """Initialize grid renderer."""
        self.font_collection = FontCollection()
    
    def render_grid(self, images: List[Path], cols: int = 4, title: Optional[str] = None) -> bytes:
        """
        Render a grid of images.
        
        Args:
            images: List of image paths to render
            cols: Number of columns in grid
            title: Optional title for the grid
            
        Returns:
            PNG image bytes
        """
        if not images:
            return self._create_empty_grid(title)
        
        # Calculate grid dimensions
        rows = (len(images) + cols - 1) // cols
        title_offset = self.TITLE_HEIGHT if title else 0
        width = cols * self.CELL_SIZE + (cols + 1) * self.PADDING
        height = title_offset + rows * self.CELL_SIZE + (rows + 1) * self.PADDING
        
        # Create surface
        surface = SurfaceManager.create_raster_surface(width, height)
        canvas = surface.getCanvas()
        
        # Fill white background
        bg_color = (255, 255, 255, 255)
        bg_rect = skia.Rect.MakeWH(width, height)
        DrawingHelpers.fill_rect(canvas, bg_rect, bg_color)
        
        # Draw title if provided
        if title:
            self._draw_title(canvas, title, width)
        
        # Draw grid cells
        for idx, image_path in enumerate(images):
            row = idx // cols
            col = idx % cols
            x = col * self.CELL_SIZE + (col + 1) * self.PADDING
            y = title_offset + row * self.CELL_SIZE + (row + 1) * self.PADDING
            
            self._draw_grid_cell(canvas, image_path, x, y)
        
        return SurfaceManager.get_png_bytes(surface)
    
    def render_grid_to_file(self, images: List[Path], output_path: Path, 
                           cols: int = 4, title: Optional[str] = None) -> bool:
        """
        Render a grid and save to file.
        
        Args:
            images: List of image paths to render
            output_path: Path where grid image should be saved
            cols: Number of columns in grid
            title: Optional title for the grid
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not images:
                bytes_data = self._create_empty_grid(title)
            else:
                bytes_data = self.render_grid(images, cols, title)
            
            if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                temp_surface = SurfaceManager.create_raster_surface(1, 1)
                # Use get_jpeg_bytes to encode
                image = skia.Image.MakeFromEncoded(skia.Data.MakeWithoutCopy(bytes_data))
                SurfaceManager.save_jpeg(temp_surface, output_path)
            else:
                output_path.write_bytes(bytes_data)
            
            return True
        except Exception:
            return False
    
    def _draw_title(self, canvas: skia.Canvas, title: str, width: int) -> None:
        """
        Draw title on canvas.
        
        Args:
            canvas: Skia Canvas to draw on
            title: Title text
            width: Canvas width for centering
        """
        font = self.font_collection.create_font(size=18.0)
        
        # Draw title background
        title_bg = skia.Rect.MakeWH(width, self.TITLE_HEIGHT)
        DrawingHelpers.fill_rect(canvas, title_bg, (240, 240, 240, 255))
        
        # Draw title text
        x = self.PADDING
        y = self.TITLE_HEIGHT - 10
        DrawingHelpers.draw_text(canvas, title, x, y, font, (0, 0, 0, 255))
    
    def _draw_grid_cell(self, canvas: skia.Canvas, image_path: Path, x: float, y: float) -> None:
        """
        Draw a single grid cell with image.
        
        Args:
            canvas: Skia Canvas to draw on
            image_path: Path to image file
            x: X position of cell
            y: Y position of cell
        """
        # Draw cell background
        cell_rect = skia.Rect.MakeXYWH(x, y, self.CELL_SIZE, self.CELL_SIZE)
        DrawingHelpers.fill_rect(canvas, cell_rect, (255, 255, 255, 255))
        
        # Draw cell border
        DrawingHelpers.draw_line(canvas, x, y, x + self.CELL_SIZE, y, 1.0, (200, 200, 200, 255))
        DrawingHelpers.draw_line(canvas, x + self.CELL_SIZE, y, x + self.CELL_SIZE, y + self.CELL_SIZE, 1.0, (200, 200, 200, 255))
        DrawingHelpers.draw_line(canvas, x + self.CELL_SIZE, y + self.CELL_SIZE, x, y + self.CELL_SIZE, 1.0, (200, 200, 200, 255))
        DrawingHelpers.draw_line(canvas, x, y + self.CELL_SIZE, x, y, 1.0, (200, 200, 200, 255))
        
        # Load and draw image
        image = load_image_from_path(image_path)
        if image:
            # Scale image to fit cell
            scaled_image = scale_image(image, self.CELL_SIZE - 4, self.CELL_SIZE - 4)
            img_x = x + 2 + (self.CELL_SIZE - 4 - scaled_image.width()) / 2
            img_y = y + 2 + (self.CELL_SIZE - 4 - scaled_image.height()) / 2
            canvas.drawImage(scaled_image, img_x, img_y)
    
    def _create_empty_grid(self, title: Optional[str] = None) -> bytes:
        """
        Create an empty grid placeholder.
        
        Args:
            title: Optional title
            
        Returns:
            PNG image bytes
        """
        title_offset = self.TITLE_HEIGHT if title else 0
        surface = SurfaceManager.create_raster_surface(400, 200 + title_offset)
        canvas = surface.getCanvas()
        
        # Fill background
        bg_rect = skia.Rect.MakeWH(400, 200 + title_offset)
        DrawingHelpers.fill_rect(canvas, bg_rect, (255, 255, 255, 255))
        
        # Draw title if provided
        if title:
            self._draw_title(canvas, title, 400)
        
        # Draw "No images" text
        font = self.font_collection.create_font(size=14.0)
        DrawingHelpers.draw_text(canvas, "No images to display", 50, 120 + title_offset, font, (128, 128, 128, 255))
        
        return SurfaceManager.get_png_bytes(surface)


def create_simple_grid(num_cells: int = 4, cell_color: Tuple[int, int, int, int] = (200, 200, 255, 255),
                      title: Optional[str] = None) -> bytes:
    """
    Create a simple grid with placeholder cells.
    
    Args:
        num_cells: Number of cells to create
        cell_color: RGBA color for cells
        title: Optional title
        
    Returns:
        PNG image bytes
    """
    cols = 4
    rows = (num_cells + cols - 1) // cols
    title_offset = 40 if title else 0
    cell_size = 80
    padding = 8
    
    width = cols * cell_size + (cols + 1) * padding
    height = title_offset + rows * cell_size + (rows + 1) * padding
    
    surface = SurfaceManager.create_raster_surface(width, height)
    canvas = surface.getCanvas()
    
    # Fill background
    bg_rect = skia.Rect.MakeWH(width, height)
    DrawingHelpers.fill_rect(canvas, bg_rect, (255, 255, 255, 255))
    
    # Draw title if provided
    if title:
        font = FontCollection().create_font(size=18.0)
        title_bg = skia.Rect.MakeWH(width, 40)
        DrawingHelpers.fill_rect(canvas, title_bg, (240, 240, 240, 255))
        DrawingHelpers.draw_text(canvas, title, padding, 30, font, (0, 0, 0, 255))
    
    # Draw grid cells
    for idx in range(num_cells):
        row = idx // cols
        col = idx % cols
        x = col * cell_size + (col + 1) * padding
        y = title_offset + row * cell_size + (row + 1) * padding
        
        cell_rect = skia.Rect.MakeXYWH(x, y, cell_size, cell_size)
        DrawingHelpers.fill_rect(canvas, cell_rect, cell_color)
        
        # Draw cell border
        DrawingHelpers.draw_line(canvas, x, y, x + cell_size, y, 1.0, (100, 100, 100, 255))
        DrawingHelpers.draw_line(canvas, x + cell_size, y, x + cell_size, y + cell_size, 1.0, (100, 100, 100, 255))
        DrawingHelpers.draw_line(canvas, x + cell_size, y + cell_size, x, y + cell_size, 1.0, (100, 100, 100, 255))
        DrawingHelpers.draw_line(canvas, x, y + cell_size, x, y, 1.0, (100, 100, 100, 255))
    
    return SurfaceManager.get_png_bytes(surface)
