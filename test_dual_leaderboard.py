"""
Test script for the new dual leaderboard formatting
"""

from ocr.stats_manager import StatsManager

# Initialize stats manager
stats = StatsManager()

# Check if we have existing data
if not stats.get_all_stats():
    print("No existing stats found. Adding sample data...")
    
    # Add some sample data
    sample_players = [
        {
            'players': [
                {'name': 'Charlie', 'score': 3071573, 'kills': 320, 'deaths': 280, 'assists': 98, 'playtime_minutes': 154},
                {'name': 'invasion', 'score': 2963780, 'kills': 290, 'deaths': 310, 'assists': 85, 'playtime_minutes': 135},
                {'name': 'reggae', 'score': 2800000, 'kills': 384, 'deaths': 360, 'assists': 125, 'playtime_minutes': 180},
                {'name': 'KillerKarpfen100', 'score': 2855639, 'kills': 350, 'deaths': 340, 'assists': 110, 'playtime_minutes': 165},
                {'name': 'ChristianKM', 'score': 2545277, 'kills': 280, 'deaths': 290, 'assists': 95, 'playtime_minutes': 142},
                {'name': 'miffy', 'score': 2400000, 'kills': 260, 'deaths': 270, 'assists': 88, 'playtime_minutes': 130},
                {'name': 'iiAM.Energy', 'score': 2200000, 'kills': 245, 'deaths': 255, 'assists': 82, 'playtime_minutes': 120},
                {'name': 'Trapton', 'score': 2100000, 'kills': 230, 'deaths': 240, 'assists': 75, 'playtime_minutes': 115},
            ],
            'match_time': 150
        }
    ]
    
    # Add multiple "matches" to ensure min_games requirement is met
    for _ in range(2):
        for match in sample_players:
            stats.update_player_stats(match)
    
    print(f"Added sample data for {len(stats.get_all_stats())} players\n")

print("=" * 60)
print("DUAL LEADERBOARD FORMAT (Top 6)")
print("=" * 60)

# Get the dual leaderboard format
dual_board = stats.format_leaderboard_embed(min_games=2, top_n=6)

# Display the formatted output
print(f"\nColor: {hex(dual_board['color'])}")
print(f"Description: '{dual_board['description']}'\n")

# Display each field (table)
print("Fields:")
for idx, field in enumerate(dual_board['fields'], 1):
    print(f"\n  Field {idx}:")
    print(f"  Name: '{field['name']}'")
    print(f"  Inline: {field['inline']}")
    print(f"  Value:\n{field['value']}\n")

print("=" * 60)
print("\nDISCORD PREVIEW (how it will appear):")
print("=" * 60)
for field in dual_board['fields']:
    print(field['value'])
    print()

print("=" * 60)
print("✅ Features:")
print("  • No rank column (ordering implies rank)")
print("  • No section titles (just data)")
print("  • No main title (accumulating leaderboard)")
print("  • Each row wrapped in backticks (like PHP toField())")
print("  • Separate fields for each table")
print("  • Proper column alignment and spacing")
print("  • Matches discord-table-builder style")
print("=" * 60)
