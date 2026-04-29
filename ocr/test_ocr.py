"""
Test OCR parsing with the actual screenshot
"""

import asyncio
from parser import OCRParser
from pathlib import Path


async def test_ocr():
    """Test OCR on the debug screenshot"""
    # Initialize parser with correct path (when running from ocr directory)
    parser = OCRParser(debug_output=True, mask_path='zones.png')
    
    # Load the test scoreboard
    screenshot_path = Path('test_scoreboard.webp')
    if not screenshot_path.exists():
        print("❌ Test scoreboard not found")
        return
    
    # Read image bytes
    with open(screenshot_path, 'rb') as f:
        image_bytes = f.read()
    
    print("=" * 80)
    print("🧪 TESTING OCR WITH IMPROVED SETTINGS")
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
        for player in result['players']:
            print(f"\n  Player: {player['name']}")
            print(f"    Score:   {player['score']:,}")
            print(f"    Kills:   {player['kills']}")
            print(f"    Deaths:  {player['deaths']}")
            print(f"    Assists: {player['assists']}")
        
        print("\n" + "=" * 80)
        print("EXPECTED VALUES (from actual screenshot):")
        print("=" * 80)
        expected = [
            {"name": "Dill", "score": 11665, "kills": 10, "deaths": 0, "assists": 4},
            {"name": "Chebday", "score": 9990, "kills": 12, "deaths": 1, "assists": 5},
            {"name": "nuke", "score": 12220, "kills": 7, "deaths": 0, "assists": 12},
            {"name": "JimmyHimself", "score": 11190, "kills": 11, "deaths": 0, "assists": 8}
        ]
        
        for exp in expected:
            print(f"\n  Player: {exp['name']}")
            print(f"    Score:   {exp['score']:,}")
            print(f"    Kills:   {exp['kills']}")
            print(f"    Deaths:  {exp['deaths']}")
            print(f"    Assists: {exp['assists']}")
        
        print("\n" + "=" * 80)
        print("ACCURACY CHECK:")
        print("=" * 80)
        
        # Check each player
        for i, player in enumerate(result['players']):
            if i < len(expected):
                exp = expected[i]
                name_match = player['name'].lower() == exp['name'].lower()
                score_match = player['score'] == exp['score']
                kills_match = player['kills'] == exp['kills']
                deaths_match = player['deaths'] == exp['deaths']
                assists_match = player['assists'] == exp['assists']
                
                print(f"\n  {player['name']}:")
                print(f"    Name:    {'✅' if name_match else '❌'} ({player['name']} vs {exp['name']})")
                print(f"    Score:   {'✅' if score_match else '❌'} ({player['score']:,} vs {exp['score']:,})")
                print(f"    Kills:   {'✅' if kills_match else '❌'} ({player['kills']} vs {exp['kills']})")
                print(f"    Deaths:  {'✅' if deaths_match else '❌'} ({player['deaths']} vs {exp['deaths']})")
                print(f"    Assists: {'✅' if assists_match else '❌'} ({player['assists']} vs {exp['assists']})")
        
    else:
        print("\n❌ PARSING FAILED - No data extracted")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    asyncio.run(test_ocr())
