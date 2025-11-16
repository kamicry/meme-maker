"""
Pack list rendering utilities using Skia.
Handles drawing help images and pack listings.
"""

import skia
from pathlib import Path
from typing import List, Optional, Tuple
from .tools import FontCollection, SurfaceManager, DrawingHelpers


class PackListRenderer:
    """Renders pack information and help images."""
    
    PADDING = 16
    LINE_HEIGHT = 20
    FONT_SIZE = 12.0
    TITLE_FONT_SIZE = 18.0
    
    def __init__(self):
        """Initialize pack list renderer."""
        self.font_collection = FontCollection()
    
    def render_pack_list(self, pack_names: List[str], pack_descriptions: Optional[List[str]] = None,
                        title: str = "Available Packs") -> bytes:
        """
        Render a list of packs.
        
        Args:
            pack_names: List of pack names
            pack_descriptions: Optional list of pack descriptions
            title: Title for the list
            
        Returns:
            PNG image bytes
        """
        # Calculate dimensions
        num_packs = len(pack_names)
        width = 600
        height = 50 + (num_packs * self.LINE_HEIGHT) + self.PADDING * 3
        
        # Create surface
        surface = SurfaceManager.create_raster_surface(width, height)
        canvas = surface.getCanvas()
        
        # Fill background
        bg_rect = skia.Rect.MakeWH(width, height)
        DrawingHelpers.fill_rect(canvas, bg_rect, (255, 255, 255, 255))
        
        # Draw title
        title_font = self.font_collection.create_font(size=self.TITLE_FONT_SIZE)
        title_y = self.PADDING + 15
        DrawingHelpers.draw_text(canvas, title, self.PADDING, title_y, title_font, (0, 0, 0, 255))
        
        # Draw separator line
        sep_y = self.PADDING + 25
        DrawingHelpers.draw_line(canvas, self.PADDING, sep_y, width - self.PADDING, sep_y, 
                                1.0, (200, 200, 200, 255))
        
        # Draw pack list
        font = self.font_collection.create_font(size=self.FONT_SIZE)
        y = sep_y + 20
        
        for idx, pack_name in enumerate(pack_names):
            # Draw pack name
            DrawingHelpers.draw_text(canvas, f"• {pack_name}", self.PADDING + 10, y, font, (0, 0, 0, 255))
            
            # Draw description if provided
            if pack_descriptions and idx < len(pack_descriptions):
                desc = pack_descriptions[idx]
                if desc:
                    small_font = self.font_collection.create_font(size=10.0)
                    DrawingHelpers.draw_text(canvas, f"  {desc[:50]}...", self.PADDING + 20, y + 12, 
                                           small_font, (128, 128, 128, 255))
            
            y += self.LINE_HEIGHT
        
        return SurfaceManager.get_png_bytes(surface)
    
    def render_help_image(self, commands: List[Tuple[str, str]], title: str = "Help") -> bytes:
        """
        Render a help image with command descriptions.
        
        Args:
            commands: List of (command, description) tuples
            title: Help title
            
        Returns:
            PNG image bytes
        """
        # Calculate dimensions
        width = 700
        height = 60 + len(commands) * 25 + self.PADDING * 2
        
        # Create surface
        surface = SurfaceManager.create_raster_surface(width, height)
        canvas = surface.getCanvas()
        
        # Fill background
        bg_rect = skia.Rect.MakeWH(width, height)
        DrawingHelpers.fill_rect(canvas, bg_rect, (245, 245, 245, 255))
        
        # Draw title
        title_font = self.font_collection.create_font(size=self.TITLE_FONT_SIZE)
        DrawingHelpers.draw_text(canvas, title, self.PADDING, self.PADDING + 15, title_font, (0, 0, 0, 255))
        
        # Draw separator
        sep_y = self.PADDING + 25
        DrawingHelpers.draw_line(canvas, self.PADDING, sep_y, width - self.PADDING, sep_y, 
                                1.0, (200, 200, 200, 255))
        
        # Draw commands
        font = self.font_collection.create_font(size=self.FONT_SIZE)
        y = sep_y + 20
        
        for command, description in commands:
            # Draw command
            DrawingHelpers.draw_text(canvas, command, self.PADDING + 10, y, font, (0, 0, 100, 255))
            
            # Draw description
            small_font = self.font_collection.create_font(size=10.0)
            DrawingHelpers.draw_text(canvas, description, self.PADDING + 120, y, small_font, (100, 100, 100, 255))
            
            y += 25
        
        return SurfaceManager.get_png_bytes(surface)
    
    def render_pack_details(self, name: str, display_name: str, description: str, 
                           version: str, author: str, num_stickers: int) -> bytes:
        """
        Render detailed pack information.
        
        Args:
            name: Pack internal name
            display_name: Pack display name
            description: Pack description
            version: Pack version
            author: Pack author
            num_stickers: Number of stickers in pack
            
        Returns:
            PNG image bytes
        """
        width = 600
        height = 300
        
        # Create surface
        surface = SurfaceManager.create_raster_surface(width, height)
        canvas = surface.getCanvas()
        
        # Fill background
        bg_rect = skia.Rect.MakeWH(width, height)
        DrawingHelpers.fill_rect(canvas, bg_rect, (255, 255, 255, 255))
        
        # Draw title (display name)
        title_font = self.font_collection.create_font(size=self.TITLE_FONT_SIZE)
        DrawingHelpers.draw_text(canvas, display_name, self.PADDING, self.PADDING + 20, 
                                title_font, (0, 0, 0, 255))
        
        # Draw details
        font = self.font_collection.create_font(size=self.FONT_SIZE)
        y = self.PADDING + 50
        
        details = [
            f"Name: {name}",
            f"Version: {version}",
            f"Author: {author}",
            f"Stickers: {num_stickers}",
            f"Description: {description}"
        ]
        
        for detail in details:
            DrawingHelpers.draw_text(canvas, detail, self.PADDING, y, font, (0, 0, 0, 255))
            y += 25
        
        return SurfaceManager.get_png_bytes(surface)


def create_help_text_image(text: str, title: str = "Information") -> bytes:
    """
    Create a simple text-based help image.
    
    Args:
        text: Text to display
        title: Title
        
    Returns:
        PNG image bytes
    """
    lines = text.split('\n')
    width = max(400, min(800, max(len(line) * 8 for line in lines if line)))
    height = 60 + len(lines) * 15 + 20
    
    surface = SurfaceManager.create_raster_surface(width, height)
    canvas = surface.getCanvas()
    
    # Fill background
    bg_rect = skia.Rect.MakeWH(width, height)
    DrawingHelpers.fill_rect(canvas, bg_rect, (255, 255, 255, 255))
    
    # Draw title
    font_collection = FontCollection()
    title_font = font_collection.create_font(size=16.0)
    DrawingHelpers.draw_text(canvas, title, 16, 25, title_font, (0, 0, 0, 255))
    
    # Draw separator
    DrawingHelpers.draw_line(canvas, 16, 35, width - 16, 35, 1.0, (200, 200, 200, 255))
    
    # Draw text lines
    font = font_collection.create_font(size=11.0)
    y = 55
    for line in lines:
        DrawingHelpers.draw_text(canvas, line, 16, y, font, (50, 50, 50, 255))
        y += 15
    
    return SurfaceManager.get_png_bytes(surface)
