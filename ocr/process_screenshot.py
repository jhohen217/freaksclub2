"""
Process a specific screenshot and compare OCR results with actual values
"""

import asyncio
from parser import OCRParser
from pathlib import Path
from PIL import Image
import io


async def process_screenshot(image_path):
    """Process a screenshot and show results"""
    # Find Tesseract installation
    import os
    tesseract_path = None
    common_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in common_paths:
        if os.path.exists(path):
            tesseract_path = path
            print(f"✅ Found Tesseract at: {tesseract_path}")
            break
    
    if not tesseract_path:
        print("❌ Tesseract not found. Please install Tesseract OCR.")
        print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        return
    
    # Initialize parser with correct relative path from ocr directory
    parser = OCRParser(tesseract_path=tesseract_path, debug_output=True, mask_path='zones.png')
    
    # Load the screenshot
    screenshot_path = Path(image_path)
    if not screenshot_path.exists():
        print(f"❌ Screenshot not found: {image_path}")
        return
    
    print(f"📸 Loading screenshot: {screenshot_path}")
    
    # Handle webp format
    if screenshot_path.suffix.lower() == '.webp':
        # Convert webp to PNG in memory
        img = Image.open(screenshot_path)
        img_bytes_io = io.BytesIO()
        img.save(img_bytes_io, format='PNG')
        image_bytes = img_bytes_io.getvalue()
    else:
        # Read directly
        with open(screenshot_path, 'rb') as f:
            image_bytes = f.read()
    
    print("=" * 80)
    print("🧪 PROCESSING SCREENSHOT WITH OCR")
    print("=" * 80)
    
    # Parse the screenshot
    result = await parser.parse_screenshot(image_bytes)
    
    if result:
        print("\n" + "=" * 80)
        print("✅ PARSING RESULTS")
        print("=" * 80)
        
        print(f"\n⏱️  Match Time: {result['match_time']:.2f} minutes")
        print(f"👥 Players Found: {len(result['players'])}")
        
        print("\n📊 PLAYER STATS:")
        print("-" * 80)
        for i, player in enumerate(result['players'], 1):
            print(f"\n  Player {i}: {player['name']}")
            print(f"    Score:   {player['score']:,}")
            print(f"    Kills:   {player['kills']}")
            print(f"    Deaths:  {player['deaths']}")
            print(f"    Assists: {player['assists']}")
        
        print("\n" + "=" * 80)
        print("💾 Debug frames saved to: ocr/debug_frames/")
        print("=" * 80)
        
    else:
        print("\n❌ PARSING FAILED - No data extracted")
        print("Check ocr/debug_frames/ for debug output")
    
    print("\n" + "=" * 80)
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python process_screenshot.py <path_to_screenshot>")
        print("Example: python process_screenshot.py C:\\Users\\josh\\Desktop\\1.webp")
        sys.exit(1)
    
    image_path = sys.argv[1]
    asyncio.run(process_screenshot(image_path))
