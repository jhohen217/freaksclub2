# OCR Zones Configuration

This document explains the percentage-based zone system for OCR extraction in the FreakSwim project.

## Overview

The OCR parser now uses a configurable JSON file to define zones for text extraction. This allows easy adjustment of OCR regions without modifying code, making it adaptable to different screen resolutions and layouts.

## Configuration File

The zones are defined in `ocr/zones_config.json`. This file uses **normalized coordinates** (0.0 to 1.0) that are automatically scaled to any image resolution.

### Coordinate System

- `x`: Horizontal position (0.0 = left edge, 1.0 = right edge)
- `y`: Vertical position (0.0 = top edge, 1.0 = bottom edge)
- `w`: Width of the zone (as a fraction of total width)
- `h`: Height of the zone (as a fraction of total height)

### Example Calculation

For a 16:9 image (1920x1080 pixels):
```python
# Zone definition: {"x": 0.83, "y": 0.03, "w": 0.15, "h": 0.10}
# Converts to pixel coordinates:
x1 = int(0.83 * 1920) = 1594
y1 = int(0.03 * 1080) = 32
x2 = int((0.83 + 0.15) * 1920) = 1882
y2 = int((0.03 + 0.10) * 1080) = 140
# Result: Region from (1594, 32) to (1882, 140)
```

## Zone Structure

### Match Time Zone

Located in the top-right corner of the screen:

```json
"match_time": {
  "x": 0.83,
  "y": 0.03,
  "w": 0.15,
  "h": 0.10,
  "hint": "PSM 7, whitelist digits and ':'"
}
```

### Player Zones

Four player cards arranged horizontally at the bottom:

```json
"players": [
  {
    "index": 0,
    "name_zone": {
      "x": 0.07,
      "y": 0.70,
      "w": 0.18,
      "h": 0.05
    },
    "stats_zone": {
      "x": 0.07,
      "y": 0.79,
      "w": 0.18,
      "h": 0.13
    },
    "hint": "Leftmost player card"
  },
  // ... 3 more player zones
]
```

## Usage

### Automatic Loading

The zones configuration is automatically loaded when the `OCRParser` is initialized:

```python
parser = OCRParser(tesseract_path='path/to/tesseract')
# Loads zones from 'ocr/zones_config.json' by default
```

### Custom Configuration Path

You can specify a different configuration file:

```python
parser = OCRParser(
    tesseract_path='path/to/tesseract',
    zones_config_path='custom/zones.json'
)
```

### Fallback Behavior

If the zones configuration file is missing or invalid, the parser automatically falls back to hardcoded values. You'll see this message:

```
⚠ Using fallback hardcoded zones
```

## Adjusting Zones

To adjust the OCR zones for better accuracy:

1. **Enable debug output** (enabled by default)
2. **Process a screenshot** - this will generate debug frames in `ocr/debug_frames/`
3. **Review the debug image** - it shows colored rectangles over the detected zones:
   - Green = Name zones
   - Red = Stats zones
   - Cyan = Match time zone
4. **Adjust the coordinates** in `ocr/zones_config.json` as needed
5. **Test again** to verify the changes

### Tips for Adjusting

- **Zone too small**: Increase `w` and/or `h`
- **Zone too large**: Decrease `w` and/or `h`
- **Zone misaligned left/right**: Adjust `x`
- **Zone misaligned up/down**: Adjust `y`
- **Make small changes**: Increment/decrement by 0.01 to 0.05 at a time

## Resolution Independence

The percentage-based system automatically adapts to any resolution:

- **720p (1280x720)**: Zones scale proportionally
- **1080p (1920x1080)**: Zones scale proportionally  
- **1440p (2560x1440)**: Zones scale proportionally
- **4K (3840x2160)**: Zones scale proportionally

This means the same configuration works for all 16:9 resolutions!

## Debug Output

When debug mode is enabled, the parser saves:

1. **`debug_frame_XXX.png`**: Annotated screenshot showing all zones
2. **`debug_p1_name.png` through `debug_p4_name.png`**: Individual name regions
3. **`debug_p1_stats.png` through `debug_p4_stats.png`**: Individual stats regions
4. **`full_screenshot_XXX.png`**: Original screenshot for reference
5. **`full_ocr_text_XXX.txt`**: Complete OCR output for debugging

These files help diagnose OCR issues and fine-tune zone positions.

## Example: Creating Custom Zones

If you need to create zones for a different layout:

1. Take a screenshot of the victory screen
2. Use an image editor to measure the positions (in pixels)
3. Convert to normalized coordinates:
   ```
   normalized_x = pixel_x / image_width
   normalized_y = pixel_y / image_height
   normalized_w = zone_width / image_width
   normalized_h = zone_height / image_height
   ```
4. Update `zones_config.json` with the new values
5. Test and iterate

## Troubleshooting

### Zones not loading

Check the console output:
- `✓ Loaded zones configuration from ocr/zones_config.json` = Success
- `⚠ Using fallback hardcoded zones` = File missing or invalid

### Poor OCR accuracy

1. Check debug frames to verify zones are correctly positioned
2. Ensure zones fully cover the text areas
3. Add a small margin around text for better recognition
4. Consider the `hint` field for OCR configuration guidance

### JSON syntax errors

Validate your JSON file:
- Use a JSON validator (many online tools available)
- Check for missing commas, brackets, or quotes
- Ensure all numbers are valid (no trailing commas in arrays)

## Technical Implementation

The system uses these key methods:

- **`_load_zones_config()`**: Loads and validates the JSON configuration
- **`_get_zone_coords()`**: Converts normalized coordinates to pixel coordinates
- **`_parse_single_player_with_zones()`**: Uses zone configuration for parsing
- **`_save_debug_frame()`**: Visualizes zones on debug output

The implementation maintains backward compatibility by falling back to hardcoded values if the configuration is unavailable.
