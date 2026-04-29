# Enhanced OCR Settings for Better Accuracy

## Overview
Enhanced the EasyOCR parameters in `ocr/parser.py` to prioritize accuracy over speed. These settings are more computationally expensive but provide better text detection.

## New Parameters

### Text Detection Quality
- **`detail=1`**: Returns detailed results including bounding boxes and confidence scores
- **`canvas_size=4096`**: Increased from default 2560 to 4096 for better handling of high-resolution images
- **`mag_ratio=1.5`**: Magnification ratio for better small text detection (default is 1.0)

### Text Grouping & Detection
- **`width_ths=0.7`**: Width threshold for text grouping (lower = more strict grouping)
- **`ycenter_ths=0.5`**: Y-center threshold for line detection (helps group text on same line)
- **`height_ths=0.5`**: Height threshold for matching text to lines
- **`add_margin=0.1`**: Adds 10% margin around detected text regions
- **`link_threshold=0.3`**: Character linking threshold (lower = more strict, reduces false positives)

### Image Processing
- **`contrast_ths=0.05`**: Lowered from 0.1 to 0.05 for more sensitive contrast detection
- **`adjust_contrast=0.8`**: Increased from 0.5 to 0.8 for stronger contrast adjustment
- **`text_threshold=0.5`**: Lowered from 0.6 to 0.5 for more permissive text detection
- **`low_text=0.2`**: Lowered from 0.3 to 0.2 to detect fainter/smaller text

## Expected Impact

### Improvements:
1. **Better number detection**: Stricter character linking should reduce "9 1 990" misreads
2. **Improved comma detection**: Better contrast handling should correctly detect commas vs spaces
3. **Higher accuracy**: More permissive thresholds catch more text variations
4. **Better small text**: Increased canvas size and mag ratio help with small numbers

### Trade-offs:
- **Slower processing**: More detailed analysis takes longer per screenshot
- **Higher memory usage**: Larger canvas size requires more RAM
- **More CPU/GPU usage**: More intensive processing on each zone

## Testing
To test the enhanced settings, run:
```bash
cd ocr
python test_ocr.py
```

The debug output will show if the OCR now correctly reads "9,990" instead of "9 1 990".
