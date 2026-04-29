"""
Quick test to verify Chebday's score parsing fix
"""
import re

def extract_numbers_from_text(text, is_score_zone=False):
    """Test the enhanced number extraction logic"""
    print(f"Testing: '{text}' (is_score_zone={is_score_zone})")
    
    # First, try to find properly formatted scores with commas
    comma_numbers = re.findall(r'\d{1,2},\s*\d{3}', text)
    if comma_numbers and is_score_zone:
        score_candidates = [int(n.replace(',', '').replace(' ', '')) for n in comma_numbers]
        scores = [s for s in score_candidates if 1000 <= s <= 50000]
        if scores:
            print(f"  ✓ Found comma-formatted score: {scores}")
            return scores
    
    # ENHANCED: Handle "X X XXX" patterns specifically
    space_pattern = re.search(r'(\d+)\s+(\d+)\s+(\d{3})', text)
    if space_pattern and is_score_zone:
        first = space_pattern.group(1)
        middle = space_pattern.group(2)
        last = space_pattern.group(3)
        
        # Try concatenating all parts
        combined_all = int(first + middle + last)
        if 1000 <= combined_all <= 50000:
            print(f"  ✓ Found space-separated score: '{space_pattern.group(0)}' -> {combined_all}")
            return [combined_all]
        
        # If out of range, try dropping the middle digit
        combined_no_middle = int(first + last)
        if 1000 <= combined_no_middle <= 50000:
            print(f"  ✓ Found comma-misread pattern: '{space_pattern.group(0)}' -> {combined_no_middle} (dropped middle '{middle}')")
            return [combined_no_middle]
    
    print(f"  ✗ No score found")
    return []

# Test cases
print("=" * 60)
print("TESTING SCORE PARSING")
print("=" * 60)

test_cases = [
    ("9, 990", True),    # Current OCR output for Chebday
    ("9 1 990", True),   # Previous OCR output
    ("11,665", True),    # Dill's score
    ("12,220", True),    # nuke's score
    ("11,190", True),    # JimmyHimself's score
]

for text, is_score in test_cases:
    result = extract_numbers_from_text(text, is_score)
    print()

print("=" * 60)
