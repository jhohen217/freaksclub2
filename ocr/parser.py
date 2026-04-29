"""
OCR Parser for Battle Royale Squads victory screenshots
Extracts player stats from victory screen images using mask-based OCR with EasyOCR
"""

import easyocr
import cv2
import numpy as np
from PIL import Image
import re
import io
from pathlib import Path


class OCRParser:
    """Parse Battle Royale victory screenshots using mask-based OCR with EasyOCR"""
    
    def __init__(self, debug_output=True, mask_path='ocr/zones.png'):
        """
        Initialize the OCR parser
        
        Args:
            debug_output: Whether to save debug frames (default True)
            mask_path: Path to mask image (required) - white regions will be processed
        """
        # Initialize EasyOCR reader with GPU support
        print("🔧 Initializing EasyOCR (this may take a moment on first run)...")
        self.reader = easyocr.Reader(['en'], gpu=True)
        print("✅ EasyOCR initialized successfully")
        
        self.debug_output = debug_output
        self.debug_counter = 0
        
        # OCR Configuration - IMPROVED
        self.upscale_factor = 4  # Increased from 2 to 4 for better small text recognition
        self.allowlist = '0123456789,:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_ '
        
        # Load mask image (required)
        self.mask = self._load_mask(mask_path)
        if self.mask is None:
            raise FileNotFoundError(f"❌ Mask file required but not found: {mask_path}")
        
        print(f"✓ Loaded mask from {mask_path}")
    
    def _load_mask(self, mask_path):
        """
        Load mask image for limiting OCR to specific regions
        
        Args:
            mask_path: Path to mask image (white regions = process, black = ignore)
            
        Returns:
            numpy array: Mask image in grayscale, or None if loading fails
        """
        try:
            mask_file = Path(mask_path)
            if not mask_file.exists():
                print(f"Mask file not found: {mask_path}")
                return None
            
            # Load mask image in grayscale
            mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                print(f"Failed to load mask image: {mask_path}")
                return None
            
            return mask
            
        except Exception as e:
            print(f"Error loading mask: {e}")
            return None
    
    def _extract_zones_from_mask(self, resized_mask):
        """
        Extract individual zone regions from the mask
        
        Args:
            resized_mask: Mask resized to match image dimensions
            
        Returns:
            list: List of zone dictionaries with bounding boxes
        """
        try:
            # Find contours in the mask (white regions)
            contours, _ = cv2.findContours(resized_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            zones = []
            for i, contour in enumerate(contours):
                # Get bounding rectangle for each white region
                x, y, w, h = cv2.boundingRect(contour)
                
                # Only include zones with reasonable size
                if w > 10 and h > 10:
                    zones.append({
                        'index': i,
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': w * h
                    })
            
            # Sort zones by position (top to bottom, left to right)
            zones.sort(key=lambda z: (z['y'], z['x']))
            
            print(f"🔍 Detected {len(zones)} zones from mask")
            for zone in zones:
                print(f"  Zone {zone['index']}: ({zone['x']}, {zone['y']}) {zone['width']}x{zone['height']}")
            
            return zones
            
        except Exception as e:
            print(f"Error extracting zones from mask: {e}")
            return []
    
    async def parse_screenshot(self, image_bytes, override=False):
        """
        Parse a victory screenshot using zones extracted from mask with EasyOCR
        
        Args:
            image_bytes: Raw image bytes from Discord attachment
            override: If True, bypass victory verification and treat as first place win
            
        Returns:
            dict: Parsed data containing match_time and list of players with stats
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            img_array = np.array(image)
            
            # Save original image info
            height, width = img_array.shape[:2]
            print(f"📐 Image dimensions: {width}x{height} pixels")
            
            # Convert to grayscale (minimal preprocessing like the working EasyOCR script)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Resize mask to match image
            resized_mask = cv2.resize(self.mask, (width, height), interpolation=cv2.INTER_LINEAR)
            print(f"🎭 Resized mask from {self.mask.shape} to {resized_mask.shape}")
            
            # Extract zones from mask
            zones = self._extract_zones_from_mask(resized_mask)
            
            if not zones:
                print("⚠ No zones detected in mask")
                return None
            
            # Save debug frames if enabled
            if self.debug_output:
                self._save_debug_frames(img_array, gray, resized_mask, zones)
            
            # Run OCR on each zone individually using EasyOCR with preprocessing
            zone_texts = []
            for zone in zones:
                x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
                zone_region = gray[y:y+h, x:x+w]
                
                # Determine if this is likely a stats zone (bottom zones with numbers)
                is_stats_zone = y > (height * 0.7)
                
                # Preprocess zone for better OCR
                processed_zone = self._preprocess_zone(zone_region, is_stats_zone)
                
                # Run EasyOCR on the zone with high-accuracy parameters
                # These settings prioritize accuracy over speed
                results = self.reader.readtext(
                    processed_zone,
                    allowlist=self.allowlist,
                    paragraph=False,
                    detail=1,                # Return detailed results with bounding boxes
                    width_ths=0.7,           # Width threshold for text grouping (lower = more strict)
                    ycenter_ths=0.5,         # Y-center threshold for line detection
                    height_ths=0.5,          # Height threshold for line matching
                    add_margin=0.1,          # Add margin around detected text
                    contrast_ths=0.05,       # Lower = more sensitive contrast detection
                    adjust_contrast=0.8,     # Higher = more contrast adjustment
                    text_threshold=0.5,      # Lower = more permissive text detection
                    low_text=0.2,            # Lower = detect fainter text
                    link_threshold=0.3,      # Lower = more strict character linking
                    canvas_size=4096,        # Larger canvas for better detection
                    mag_ratio=1.5            # Magnification ratio for better small text
                )
                
                # Combine all text from this zone
                zone_text = ' '.join([text for (bbox, text, conf) in results if conf > 0.3])
                
                zone_texts.append({
                    'zone_index': zone['index'],
                    'text': zone_text,
                    'bounds': (x, y, w, h),
                    'is_stats': is_stats_zone
                })
                print(f"📝 Zone {zone['index']} {'[STATS]' if is_stats_zone else '[NAME]'} OCR: {zone_text[:50].strip()}...")
            
            # Parse the zone texts to extract structured data
            parsed_data = self._parse_zone_texts(zone_texts, override=override)
            
            if not parsed_data or not parsed_data.get('players'):
                print("⚠ No player data extracted from zones")
                return None
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing screenshot: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_zone_texts(self, zone_texts, override=False):
        """
        Parse OCR text from individual zones to extract match time and player statistics
        Names and stats may be in separate zones that need to be paired by x-coordinate
        
        Args:
            zone_texts: List of dicts with zone_index, text, and bounds
            override: If True, bypass victory/game mode validation and treat as valid win
            
        Returns:
            dict: Parsed data with match_time, game_mode, and players list, or None if validation fails
        """
        try:
            match_time = 0.0
            players = []
            
            # Debug: Print all zone texts
            print("\n📊 ZONE TEXT ANALYSIS:")
            for zt in zone_texts:
                print(f"\n  Zone {zt['zone_index']} at {zt['bounds']}:")
                print(f"    Raw text: {repr(zt['text'][:100])}")
            
            combined_text = ' '.join([zt['text'] for zt in zone_texts])
            combined_upper = combined_text.upper()
            
            # OVERRIDE MODE: Skip validation failures but still try to detect game mode
            if override:
                print("\n🔓 OVERRIDE MODE ACTIVE:")
                print("  ⚠ Bypassing VICTORY validation failure")
                victory_found = True
                
                # Still try to detect game mode from text
                print("\n🎮 GAME MODE DETECTION (override):")
                game_mode = None
                
                # Check for SQUADS (various OCR variations)
                if any(pattern in combined_upper for pattern in ['SQUAD', 'SQAUD', 'SUQAD']):
                    game_mode = 'squads'
                    print("  ✓ Game mode detected: SQUADS")
                # Check for DUOS (various OCR variations)
                elif any(pattern in combined_upper for pattern in ['DUOS', 'DUO', 'DOUS']):
                    game_mode = 'duos'
                    print("  ✓ Game mode detected: DUOS")
                else:
                    # If we can't detect, default to squads
                    game_mode = 'squads'
                    print("  ⚠ Game mode NOT detected - defaulting to SQUADS")
                    print(f"  → Detected text: {combined_upper[:100]}")
            else:
                # VALIDATION 1: Check for Victory text (lenient matching for OCR errors)
                print("\n🏆 VICTORY VALIDATION:")
                victory_found = False
                
                # Check for various OCR variations of "VICTORY"
                victory_patterns = [
                    'VICTORY',   # Perfect match
                    'VICTOR',    # Missing Y
                    'VCTORY',    # Missing I
                    'VICTRY',    # Missing O
                    'VICORY',    # Missing T
                    'ICTORY',    # Missing V
                ]
                
                for pattern in victory_patterns:
                    if pattern in combined_upper:
                        victory_found = True
                        if pattern != 'VICTORY':
                            print(f"  ✓ VICTORY text found (detected as '{pattern}')")
                        else:
                            print(f"  ✓ VICTORY text found")
                        break
                
                if not victory_found:
                    print(f"  ✗ VICTORY text NOT found - rejecting screenshot")
                    print(f"  → Detected text: {combined_upper[:100]}")
                    return None
                
                # VALIDATION 2: Check for game mode (lenient matching)
                print("\n🎮 GAME MODE VALIDATION:")
                game_mode = None
                
                # Check for SQUADS (various OCR variations)
                if any(pattern in combined_upper for pattern in ['SQUAD', 'SQAUD', 'SUQAD']):
                    game_mode = 'squads'
                    print("  ✓ Game mode detected: SQUADS")
                # Check for DUOS (various OCR variations)
                elif any(pattern in combined_upper for pattern in ['DUOS', 'DUO', 'DOUS']):
                    game_mode = 'duos'
                    print("  ✓ Game mode detected: DUOS")
                else:
                    print("  ✗ Game mode NOT detected (must be SQUADS or DUOS) - rejecting screenshot")
                    print(f"  → Detected text: {combined_upper[:100]}")
                    return None
            
            # Find match time
            # First try direct colon format
            time_match = re.search(r'(\d+):(\d+)', combined_text)
            if not time_match:
                # Try comma format (OCR misread)
                time_match = re.search(r'(\d+),(\d+)', combined_text)
            
            if time_match:
                minutes = int(time_match.group(1))
                seconds = int(time_match.group(2))
                match_time = round(minutes + seconds / 60.0, 2)
                print(f"\n⏱ Match time found: {minutes}:{seconds:02d} = {match_time} minutes")
            
            # Separate zones into name zones and stat zones by analyzing y-coordinate
            # Group zones by y-coordinate to find rows
            y_groups = {}
            for zt in zone_texts:
                x, y, w, h = zt['bounds']
                y_rounded = round(y / 50) * 50  # Group by ~50px bands
                if y_rounded not in y_groups:
                    y_groups[y_rounded] = []
                y_groups[y_rounded].append(zt)
            
            # Sort y-groups to identify which is names and which is stats
            sorted_y_groups = sorted(y_groups.items())
            
            print(f"\n🔍 ZONE GROUPING: Found {len(sorted_y_groups)} rows")
            for y_val, zones in sorted_y_groups:
                print(f"  Row at y≈{y_val}: {len(zones)} zones")
            
            # Try to pair zones by x-coordinate across rows
            print("\n📝 PARSING STRATEGY:")
            
            # Case 1: If we have 2 distinct rows, pair them
            if len(sorted_y_groups) >= 2:
                # Find row with names (has letters) and row with stats (has numbers)
                name_row = None
                stat_row = None
                
                for y_val, zones in sorted_y_groups:
                    has_letters = any(any(c.isalpha() for c in zt['text']) for zt in zones)
                    has_numbers = any(any(c.isdigit() for c in zt['text']) for zt in zones)
                    
                    if has_letters and not has_numbers:
                        name_row = zones
                        print(f"  Name row identified at y≈{y_val}")
                    elif has_numbers and not has_letters:
                        stat_row = zones
                        print(f"  Stat row identified at y≈{y_val}")
                
                # Pair zones by x-coordinate with improved spatial awareness
                if name_row and stat_row:
                    print("  Using paired row strategy with spatial awareness")
                    
                    # Sort name zones and stat zones by x-coordinate for proper pairing
                    name_row_sorted = sorted(name_row, key=lambda z: z['bounds'][0])
                    stat_row_sorted = sorted(stat_row, key=lambda z: z['bounds'][0])
                    
                    # Group stat zones by detecting GAPS between players
                    # Zones within a player are ~60-100px apart
                    # Gaps between players are ~170-200px
                    player_stat_groups = []
                    current_group = []
                    last_x = None
                    
                    for stat_zone in stat_row_sorted:
                        x_stat = stat_zone['bounds'][0]
                        # Start new group if gap is > 150px (indicates new player)
                        if last_x is not None and (x_stat - last_x) > 150:
                            # Large gap detected - new player
                            if current_group:
                                player_stat_groups.append(current_group)
                            current_group = [stat_zone]
                        else:
                            # Same player - add to current group
                            current_group.append(stat_zone)
                        last_x = x_stat
                    
                    if current_group:
                        player_stat_groups.append(current_group)
                    
                    print(f"  Grouped stats into {len(player_stat_groups)} player groups")
                    
                    # Track all detected names for validation
                    detected_names = []
                    failed_players = []
                    
                    # Now pair each name with its stat group
                    for name_zone in name_row_sorted:
                        x_name = name_zone['bounds'][0]
                        name = self._extract_name_from_text(name_zone['text'])
                        
                        if not name:
                            continue
                        
                        detected_names.append(name)
                        
                        # Find the closest stat group by x-coordinate
                        best_group = None
                        min_distance = float('inf')
                        
                        for stat_group in player_stat_groups:
                            # Use the leftmost zone in the group for distance calculation
                            group_x = stat_group[0]['bounds'][0]
                            distance = abs(x_name - group_x)
                            if distance < min_distance:
                                min_distance = distance
                                best_group = stat_group
                        
                        if best_group and min_distance < 500:  # Within 500px
                            # Extract numbers from all zones in this group
                            player_stats = []
                            
                            # First zone is typically the score (larger zone)
                            for i, stat_zone in enumerate(best_group):
                                is_score = (i == 0 and stat_zone['bounds'][2] > 60)  # width > 60px = score
                                numbers = self._extract_numbers_from_text(
                                    stat_zone['text'], 
                                    time_match,
                                    is_score_zone=is_score
                                )
                                player_stats.extend(numbers)
                            
                            print(f"  Stats for {name}: {player_stats}")
                            
                            # Validate and assign stats (score, kills, deaths, assists, playtime_minutes)
                            if len(player_stats) >= 4:
                                # Filter out obviously wrong values
                                score = player_stats[0] if 1000 <= player_stats[0] <= 50000 else None
                                if not score and len(player_stats) > 4:
                                    # Try next value as score
                                    score = player_stats[1] if 1000 <= player_stats[1] <= 50000 else player_stats[0]
                                    player_stats = player_stats[1:]
                                
                                player_data = {
                                    'name': name,
                                    'score': player_stats[0],
                                    'kills': player_stats[1],
                                    'deaths': player_stats[2],
                                    'assists': player_stats[3]
                                }
                                
                                # Extract playtime if available (5th stat)
                                if len(player_stats) >= 5:
                                    playtime_minutes = player_stats[4]
                                    # Validate playtime (should be reasonable: 0-60 minutes typically)
                                    if 0 <= playtime_minutes <= 120:
                                        player_data['playtime_minutes'] = playtime_minutes
                                        print(f"  ✓ PAIRED: {name} - Score: {player_stats[0]}, K/D/A: {player_stats[1]}/{player_stats[2]}/{player_stats[3]}, Playtime: {playtime_minutes}m")
                                    else:
                                        print(f"  ✓ PAIRED: {name} - Score: {player_stats[0]}, K/D/A: {player_stats[1]}/{player_stats[2]}/{player_stats[3]}")
                                else:
                                    print(f"  ✓ PAIRED: {name} - Score: {player_stats[0]}, K/D/A: {player_stats[1]}/{player_stats[2]}/{player_stats[3]}")
                                
                                players.append(player_data)
                                
                                # Remove this group so it's not reused
                                player_stat_groups.remove(best_group)
                            else:
                                print(f"  ✗ FAILED: Name '{name}' found but insufficient stats: {player_stats}")
                                failed_players.append(name)
                        else:
                            print(f"  ✗ FAILED: Name '{name}' found but no nearby stat group (min_distance={min_distance})")
                            failed_players.append(name)
                    
                    # ALL-OR-NOTHING VALIDATION: If any player failed, reject entire screenshot
                    if failed_players:
                        print(f"\n❌ REJECTING SCREENSHOT: Failed to extract complete stats for {len(failed_players)} player(s): {', '.join(failed_players)}")
                        print(f"   → Successfully parsed: {len(players)} player(s)")
                        print(f"   → Failed to parse: {len(failed_players)} player(s)")
                        print(f"   → All-or-nothing policy: Rejecting entire screenshot")
                        return None
                else:
                    print("  ⚠ Could not identify distinct name/stat rows, trying single-zone strategy")
                    # Fall back to single zone strategy
                    players = self._parse_single_zone_strategy(zone_texts, time_match)
            else:
                print("  Using single-zone strategy (all data in one zone)")
                players = self._parse_single_zone_strategy(zone_texts, time_match)
            
            print(f"\n✅ FINAL: Found {len(players)} players")
            print(f"✅ Game mode: {game_mode}")
            
            return {
                'match_time': match_time,
                'game_mode': game_mode,
                'players': players
            }
            
        except Exception as e:
            print(f"Error parsing zone texts: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_name_from_text(self, text):
        """Extract player name from text"""
        lines = text.strip().split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line and len(clean_line) >= 2 and any(c.isalpha() for c in clean_line):
                return self._clean_player_name(clean_line)
        return ""
    
    def _extract_numbers_from_text(self, text, time_match=None, is_score_zone=False):
        """
        Extract numbers from text, filtering out time values
        Handles various OCR artifacts like spaces, extra digits, comma misreads
        
        Args:
            text: Text to extract numbers from
            time_match: Match object from time regex (to filter out time values)
            is_score_zone: If True, look specifically for score patterns (4-5 digit numbers)
        
        Returns:
            list: Extracted numbers
        """
        # Debug log
        if text.strip():
            print(f"    🔢 Extracting numbers from: '{text}' (is_score_zone={is_score_zone})")
        
        # First, try to find properly formatted scores with commas
        # Handle: "11,665", "9, 990" (space after comma), "17 ,760" (space before comma)
        # Remove spaces around commas first
        text_no_space_comma = re.sub(r'\s*,\s*', ',', text)
        comma_numbers = re.findall(r'\d{1,2},\d{3}', text_no_space_comma)
        if comma_numbers and is_score_zone:
            # Remove commas and spaces, then convert to int
            score_candidates = [int(n.replace(',', '').replace(' ', '')) for n in comma_numbers]
            # Filter to reasonable score range (1000-50000)
            scores = [s for s in score_candidates if 1000 <= s <= 50000]
            if scores:
                print(f"    ✓ Found comma-formatted score: {scores}")
                return scores
        
        text_cleaned = text
        
        # ENHANCED: Handle "X X XXX" patterns specifically (like "9 1 990")
        # This is a common OCR error where the comma in "9,990" becomes a space and "1"
        space_pattern = re.search(r'(\d+)\s+(\d+)\s+(\d{3})', text_cleaned)
        if space_pattern and is_score_zone:
            first = space_pattern.group(1)
            middle = space_pattern.group(2)
            last = space_pattern.group(3)
            
            # Try concatenating all parts: "9 1 990" -> "91990"
            combined_all = int(first + middle + last)
            if 1000 <= combined_all <= 50000:
                print(f"    ✓ Found space-separated score: '{space_pattern.group(0)}' -> {combined_all}")
                return [combined_all]
            
            # If that's out of range, try dropping the middle digit: "9 1 990" -> "9990"
            # This handles OCR misreading comma as space+digit
            combined_no_middle = int(first + last)
            if 1000 <= combined_no_middle <= 50000:
                print(f"    ✓ Found comma-misread pattern: '{space_pattern.group(0)}' -> {combined_no_middle} (dropped middle '{middle}')")
                return [combined_no_middle]
        
        # Special case: Handle "11 0 190" pattern (middle 0 should be 1)
        # Pattern: XX 0 XXX where the 0 is likely a misread 1
        text_cleaned = re.sub(r'(\d{2})\s+0\s+(\d{3})', r'\g<1>1\2', text_cleaned)
        
        # Handle comma-space combinations: "9, 990" -> "9,990" then "9990"
        text_cleaned = re.sub(r'(\d),\s+(\d)', r'\1,\2', text_cleaned)
        
        # Handle space-separated digit groups: "12 089" -> "12089", "12 1 220" -> "12220"
        # Be aggressive: replace any sequence of [digit][space/comma][digit] with concatenated digits
        iteration_count = 0
        while iteration_count < 10:  # Safety limit
            new_text = re.sub(r'(\d+)[,\s]+(\d+)', r'\1\2', text_cleaned)
            if new_text == text_cleaned:
                break
            text_cleaned = new_text
            iteration_count += 1
        
        # Handle comma misread patterns more carefully
        # Pattern 1: Middle "1" in 6-digit number like "121220" -> "12220"
        # Only if it looks like: XX1XXX where the last 3 digits would make sense as decimals
        text_cleaned = re.sub(r'(\d{2})1(\d{3})(?!\d)', r'\1\2', text_cleaned)
        
        # Pattern 2: Leading "2" on 6-digit scores (but NOT leading "1")
        # "210665" -> "10665" (comma misread as 2)
        # But preserve "110190" as it could be valid
        text_cleaned = re.sub(r'\b2(\d{5})\b', r'\1', text_cleaned)
        
        # Extract all numbers
        numbers = re.findall(r'\d+', text_cleaned)
        numbers = [int(n) for n in numbers]
        
        print(f"    → After cleaning: {numbers}")
        
        # Filter out time numbers
        if time_match:
            minutes_val = int(time_match.group(1))
            seconds_val = int(time_match.group(2))
            numbers = [n for n in numbers if n != minutes_val and n != seconds_val]
        
        # If this is a score zone, filter to reasonable score ranges
        if is_score_zone:
            # Scores are typically 1,000 - 50,000
            original_count = len(numbers)
            numbers = [n for n in numbers if 1000 <= n <= 50000]
            if len(numbers) < original_count:
                print(f"    ⚠ Filtered out non-score values (kept {len(numbers)}/{original_count})")
        
        print(f"    → Final numbers: {numbers}")
        return numbers
    
    def _parse_single_zone_strategy(self, zone_texts, time_match):
        """Parse when name and stats are in the same zone"""
        players = []
        
        for zone_data in zone_texts:
            text = zone_data['text']
            
            # Extract name
            name = self._extract_name_from_text(text)
            # Extract numbers
            numbers = self._extract_numbers_from_text(text, time_match)
            
            # Try to extract stats (score, kills, deaths, assists, playtime_minutes)
            if name and len(numbers) >= 4:
                player_data = {
                    'name': name,
                    'score': numbers[0],
                    'kills': numbers[1],
                    'deaths': numbers[2],
                    'assists': numbers[3]
                }
                
                # Extract playtime if available (5th stat)
                if len(numbers) >= 5:
                    playtime_minutes = numbers[4]
                    # Validate playtime (should be reasonable: 0-60 minutes typically)
                    if 0 <= playtime_minutes <= 120:
                        player_data['playtime_minutes'] = playtime_minutes
                        print(f"  ✓ PLAYER: {name} - Score: {numbers[0]}, K/D/A: {numbers[1]}/{numbers[2]}/{numbers[3]}, Playtime: {playtime_minutes}m")
                    else:
                        print(f"  ✓ PLAYER: {name} - Score: {numbers[0]}, K/D/A: {numbers[1]}/{numbers[2]}/{numbers[3]}")
                else:
                    print(f"  ✓ PLAYER: {name} - Score: {numbers[0]}, K/D/A: {numbers[1]}/{numbers[2]}/{numbers[3]}")
                
                players.append(player_data)
        
        return players
    
    def _preprocess_zone(self, zone_image, is_stats_zone):
        """
        Enhanced preprocessing with different strategies for stats vs name zones
        
        Args:
            zone_image: Grayscale zone image
            is_stats_zone: Boolean indicating if this is a stats zone (numbers)
            
        Returns:
            Preprocessed image ready for OCR
        """
        try:
            original_h, original_w = zone_image.shape
            
            # Always upscale for better OCR
            scale_factor = 3
            zone_image = cv2.resize(
                zone_image,
                (original_w * scale_factor, original_h * scale_factor),
                interpolation=cv2.INTER_CUBIC
            )
            
            # For stats zones (numbers), use minimal preprocessing
            # Let EasyOCR's neural network handle the raw image
            if is_stats_zone:
                # Only apply gentle contrast enhancement - no thresholding
                # This prevents creating artifacts from shapes/icons
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                zone_image = clahe.apply(zone_image)
            else:
                # For name zones, use lighter preprocessing
                # Just enhance contrast
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                zone_image = clahe.apply(zone_image)
            
            return zone_image
            
        except Exception as e:
            print(f"Error preprocessing zone: {e}")
            return zone_image
    
    def _clean_player_name(self, name):
        """Clean and normalize player name"""
        if not name:
            return ""
        
        # Remove special characters and extra whitespace
        cleaned = re.sub(r'[^\w\s-]', '', name)
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _save_debug_frames(self, color_image, gray_image, resized_mask, zones):
        """
        Save debug visualization frames showing detected zones
        Only keeps the latest instance (overwrites previous files)
        
        Args:
            color_image: Original color image
            gray_image: Grayscale version
            resized_mask: Mask resized to match image
            zones: List of detected zone dictionaries
        """
        try:
            from pathlib import Path
            
            # Create debug output directory relative to this file's location
            debug_dir = Path(__file__).parent / "debug_frames"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            # Clear previous debug files to keep only latest
            for old_file in debug_dir.glob("*"):
                try:
                    old_file.unlink()
                except:
                    pass
            
            # Save original screenshot
            original_path = debug_dir / "01_original.png"
            cv2.imwrite(str(original_path), cv2.cvtColor(color_image, cv2.COLOR_RGB2BGR))
            print(f"💾 Original saved: {original_path}")
            
            # Save grayscale
            gray_path = debug_dir / "02_grayscale.png"
            cv2.imwrite(str(gray_path), gray_image)
            print(f"💾 Grayscale saved: {gray_path}")
            
            # Save mask
            mask_path = debug_dir / "03_mask.png"
            cv2.imwrite(str(mask_path), resized_mask)
            print(f"💾 Mask saved: {mask_path}")
            
            # Draw detected zones on original image
            zones_img = color_image.copy()
            for zone in zones:
                x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
                # Draw rectangle around zone
                cv2.rectangle(zones_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
                # Add zone label
                cv2.putText(zones_img, f"Zone {zone['index']}", (x + 5, y + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            zones_path = debug_dir / "04_detected_zones.png"
            cv2.imwrite(str(zones_path), cv2.cvtColor(zones_img, cv2.COLOR_RGB2BGR))
            print(f"💾 Detected zones saved: {zones_path}")
            
            # Save individual zone images (both original and preprocessed)
            height = gray_image.shape[0]
            for zone in zones:
                x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
                zone_region = gray_image[y:y+h, x:x+w]
                
                # Save original zone
                zone_img_path = debug_dir / f"zone_{zone['index']:02d}_original.png"
                cv2.imwrite(str(zone_img_path), zone_region)
                
                # Save preprocessed zone (what OCR actually sees)
                is_stats_zone = y > (height * 0.7)
                preprocessed = self._preprocess_zone(zone_region, is_stats_zone)
                zone_processed_path = debug_dir / f"zone_{zone['index']:02d}_processed.png"
                cv2.imwrite(str(zone_processed_path), preprocessed)
            
            print(f"💾 Individual zone images saved (original + preprocessed)")
            
            # Save OCR text for each zone
            text_output = []
            for zone in zones:
                x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
                zone_region = gray_image[y:y+h, x:x+w]
                
                # Run EasyOCR on this zone for debug output
                results = self.reader.readtext(zone_region)
                zone_text = ' '.join([text for (bbox, text, conf) in results])
                
                text_output.append(f"=== Zone {zone['index']} ({x},{y}) {w}x{h} ===\n{zone_text}\n")
            
            text_path = debug_dir / "05_zones_ocr.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_output))
            print(f"💾 OCR text saved: {text_path}")
            
        except Exception as e:
            print(f"Error saving debug frames: {e}")
            import traceback
            traceback.print_exc()
