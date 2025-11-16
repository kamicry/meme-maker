#!/usr/bin/env python3
"""
Unit tests for Meme Stickers draw module.
Tests Skia rendering utilities, sticker generation, and grid creation.
"""

import sys
import tempfile
from pathlib import Path
from typing import Tuple

# Test utilities
def test_imports():
    """Test that all draw modules import successfully."""
    print("=" * 60)
    print("Test: Module Imports")
    print("=" * 60)
    
    try:
        from meme_stickers.draw.tools import (
            FontCollection, SurfaceManager, DrawingHelpers,
            load_image_from_path, scale_image
        )
        print("✓ tools module imported")
    except Exception as e:
        print(f"✗ tools import failed: {e}")
        return False
    
    try:
        from meme_stickers.draw.sticker import (
            StickerParams, StickerRenderer, create_simple_sticker
        )
        print("✓ sticker module imported")
    except Exception as e:
        print(f"✗ sticker import failed: {e}")
        return False
    
    try:
        from meme_stickers.draw.grid import (
            GridRenderer, create_simple_grid
        )
        print("✓ grid module imported")
    except Exception as e:
        print(f"✗ grid import failed: {e}")
        return False
    
    try:
        from meme_stickers.draw.pack_list import (
            PackListRenderer, create_help_text_image
        )
        print("✓ pack_list module imported")
    except Exception as e:
        print(f"✗ pack_list import failed: {e}")
        return False
    
    print("\n✓ All modules imported successfully\n")
    return True


def test_font_collection():
    """Test FontCollection functionality."""
    print("=" * 60)
    print("Test: FontCollection")
    print("=" * 60)
    
    from meme_stickers.draw.tools import FontCollection
    
    try:
        font_collection = FontCollection()
        print("✓ FontCollection initialized")
        
        # Test typeface retrieval
        typeface, size = font_collection.get_typeface(None, 14.0)
        print(f"✓ Typeface retrieved: {typeface}, size={size}")
        
        # Test font creation
        font = font_collection.create_font(None, 14.0)
        print(f"✓ Font created: {font}")
        
        # Test with specific font family
        font2 = font_collection.create_font("DejaVu Sans", 16.0)
        print(f"✓ Font with family created: {font2}")
        
        print("\n✓ FontCollection tests passed\n")
        return True
    except Exception as e:
        print(f"✗ FontCollection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_surface_manager():
    """Test SurfaceManager functionality."""
    print("=" * 60)
    print("Test: SurfaceManager")
    print("=" * 60)
    
    from meme_stickers.draw.tools import SurfaceManager
    
    try:
        # Test surface creation
        surface = SurfaceManager.create_raster_surface(256, 256)
        print("✓ Raster surface created")
        
        # Test PNG encoding
        png_bytes = SurfaceManager.get_png_bytes(surface)
        assert len(png_bytes) > 0, "PNG bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ PNG encoding works (size: {len(png_bytes)} bytes)")
        
        # Test JPEG encoding
        jpeg_bytes = SurfaceManager.get_jpeg_bytes(surface, quality=90)
        assert len(jpeg_bytes) > 0, "JPEG bytes empty"
        assert jpeg_bytes[:3] == b'\xff\xd8\xff', "Invalid JPEG header"
        print(f"✓ JPEG encoding works (size: {len(jpeg_bytes)} bytes)")
        
        # Test file saving
        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "test.png"
            SurfaceManager.save_png(surface, png_path)
            assert png_path.exists(), "PNG file not created"
            assert png_path.stat().st_size > 0, "PNG file is empty"
            print(f"✓ PNG file saved: {png_path}")
            
            jpeg_path = Path(temp_dir) / "test.jpg"
            SurfaceManager.save_jpeg(surface, jpeg_path)
            assert jpeg_path.exists(), "JPEG file not created"
            assert jpeg_path.stat().st_size > 0, "JPEG file is empty"
            print(f"✓ JPEG file saved: {jpeg_path}")
        
        print("\n✓ SurfaceManager tests passed\n")
        return True
    except Exception as e:
        print(f"✗ SurfaceManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_drawing_helpers():
    """Test DrawingHelpers functionality."""
    print("=" * 60)
    print("Test: DrawingHelpers")
    print("=" * 60)
    
    import skia
    from meme_stickers.draw.tools import SurfaceManager, DrawingHelpers, FontCollection
    
    try:
        surface = SurfaceManager.create_raster_surface(256, 256)
        canvas = surface.getCanvas()
        
        # Test fill_rect
        rect = skia.Rect.MakeWH(100, 100)
        DrawingHelpers.fill_rect(canvas, rect, (255, 0, 0, 255))
        print("✓ Rectangle filled")
        
        # Test draw_text
        font = FontCollection().create_font(None, 16.0)
        DrawingHelpers.draw_text(canvas, "Test", 10, 20, font, (0, 0, 0, 255))
        print("✓ Text drawn")
        
        # Test draw_circle
        DrawingHelpers.draw_circle(canvas, 128, 128, 50, (0, 255, 0, 255))
        print("✓ Circle drawn")
        
        # Test draw_line
        DrawingHelpers.draw_line(canvas, 0, 0, 100, 100, 2.0, (0, 0, 255, 255))
        print("✓ Line drawn")
        
        # Verify output
        png_bytes = SurfaceManager.get_png_bytes(surface)
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG output"
        print(f"✓ Drawing output is valid PNG ({len(png_bytes)} bytes)")
        
        print("\n✓ DrawingHelpers tests passed\n")
        return True
    except Exception as e:
        print(f"✗ DrawingHelpers test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sticker_renderer():
    """Test StickerRenderer functionality."""
    print("=" * 60)
    print("Test: StickerRenderer")
    print("=" * 60)
    
    from meme_stickers.draw.sticker import StickerParams, StickerRenderer
    
    try:
        renderer = StickerRenderer()
        print("✓ StickerRenderer initialized")
        
        # Test simple sticker without image
        params = StickerParams(
            width=256,
            height=256,
            background_color=(255, 255, 255, 255),
            overlay_text="Hello",
            text_color=(0, 0, 0, 255)
        )
        
        png_bytes = renderer.render_sticker(params)
        assert len(png_bytes) > 0, "Sticker bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Sticker rendered ({len(png_bytes)} bytes)")
        
        # Test sticker with file output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sticker.png"
            result = renderer.render_sticker_to_file(params, output_path)
            assert result is True, "Render to file failed"
            assert output_path.exists(), "Output file not created"
            print(f"✓ Sticker saved to file: {output_path}")
        
        print("\n✓ StickerRenderer tests passed\n")
        return True
    except Exception as e:
        print(f"✗ StickerRenderer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_grid_renderer():
    """Test GridRenderer functionality."""
    print("=" * 60)
    print("Test: GridRenderer")
    print("=" * 60)
    
    from meme_stickers.draw.grid import GridRenderer, create_simple_grid
    
    try:
        renderer = GridRenderer()
        print("✓ GridRenderer initialized")
        
        # Test empty grid
        png_bytes = renderer.render_grid([], title="Test Grid")
        assert len(png_bytes) > 0, "Grid bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Empty grid rendered ({len(png_bytes)} bytes)")
        
        # Test simple grid without images
        png_bytes = create_simple_grid(num_cells=9, title="Simple Grid")
        assert len(png_bytes) > 0, "Simple grid bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Simple grid created ({len(png_bytes)} bytes)")
        
        # Test grid with file output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "grid.png"
            result = renderer.render_grid_to_file([], output_path, title="Test")
            assert result is True, "Grid render to file failed"
            assert output_path.exists(), "Output file not created"
            print(f"✓ Grid saved to file: {output_path}")
        
        print("\n✓ GridRenderer tests passed\n")
        return True
    except Exception as e:
        print(f"✗ GridRenderer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pack_list_renderer():
    """Test PackListRenderer functionality."""
    print("=" * 60)
    print("Test: PackListRenderer")
    print("=" * 60)
    
    from meme_stickers.draw.pack_list import PackListRenderer, create_help_text_image
    
    try:
        renderer = PackListRenderer()
        print("✓ PackListRenderer initialized")
        
        # Test pack list rendering
        pack_names = ["pack1", "pack2", "pack3"]
        pack_descs = ["Description 1", "Description 2", "Description 3"]
        
        png_bytes = renderer.render_pack_list(pack_names, pack_descs, "Test Packs")
        assert len(png_bytes) > 0, "Pack list bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Pack list rendered ({len(png_bytes)} bytes)")
        
        # Test help image rendering
        commands = [
            ("/meme list", "List available packs"),
            ("/meme install <name>", "Install a pack"),
            ("/meme delete <name>", "Delete a pack"),
        ]
        
        png_bytes = renderer.render_help_image(commands, "Meme Commands")
        assert len(png_bytes) > 0, "Help image bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Help image rendered ({len(png_bytes)} bytes)")
        
        # Test pack details rendering
        png_bytes = renderer.render_pack_details(
            "test_pack", "Test Pack", "A test pack", "1.0.0", "Author", 10
        )
        assert len(png_bytes) > 0, "Pack details bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Pack details rendered ({len(png_bytes)} bytes)")
        
        # Test help text image
        png_bytes = create_help_text_image("Line 1\nLine 2\nLine 3", "Test Info")
        assert len(png_bytes) > 0, "Help text bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Help text image created ({len(png_bytes)} bytes)")
        
        print("\n✓ PackListRenderer tests passed\n")
        return True
    except Exception as e:
        print(f"✗ PackListRenderer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_simple_sticker():
    """Test create_simple_sticker helper."""
    print("=" * 60)
    print("Test: create_simple_sticker")
    print("=" * 60)
    
    from meme_stickers.draw.sticker import create_simple_sticker
    
    try:
        # Create sticker with text
        png_bytes = create_simple_sticker(
            width=200,
            height=200,
            background_color=(200, 200, 255, 255),
            text="Sample",
            text_color=(255, 0, 0, 255)
        )
        
        assert len(png_bytes) > 0, "Sticker bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Simple sticker created ({len(png_bytes)} bytes)")
        
        # Create sticker without text
        png_bytes = create_simple_sticker(width=100, height=100)
        assert len(png_bytes) > 0, "Sticker bytes empty"
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
        print(f"✓ Simple sticker without text created ({len(png_bytes)} bytes)")
        
        print("\n✓ create_simple_sticker tests passed\n")
        return True
    except Exception as e:
        print(f"✗ create_simple_sticker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_io():
    """Test image I/O operations."""
    print("=" * 60)
    print("Test: Image I/O")
    print("=" * 60)
    
    from meme_stickers.draw.tools import SurfaceManager, load_image_from_path
    from meme_stickers.draw.sticker import create_simple_sticker
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            
            # Create a test image
            png_bytes = create_simple_sticker(width=64, height=64)
            image_path = temp_dir / "test_image.png"
            image_path.write_bytes(png_bytes)
            print(f"✓ Test image created: {image_path}")
            
            # Test loading image
            image = load_image_from_path(image_path)
            assert image is not None, "Failed to load image"
            print(f"✓ Image loaded successfully")
            
            # Test loading non-existent image
            non_existent = temp_dir / "non_existent.png"
            image = load_image_from_path(non_existent)
            assert image is None, "Should return None for non-existent image"
            print(f"✓ Non-existent image handling works")
        
        print("\n✓ Image I/O tests passed\n")
        return True
    except Exception as e:
        print(f"✗ Image I/O test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MEME STICKERS DRAW MODULE TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("FontCollection", test_font_collection),
        ("SurfaceManager", test_surface_manager),
        ("DrawingHelpers", test_drawing_helpers),
        ("StickerRenderer", test_sticker_renderer),
        ("GridRenderer", test_grid_renderer),
        ("PackListRenderer", test_pack_list_renderer),
        ("create_simple_sticker", test_create_simple_sticker),
        ("Image I/O", test_image_io),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
