# OCR Module - RecZone Stats Tracking

This module implements OCR (Optical Character Recognition) functionality to automatically parse Battle Royale Squads victory screenshots and track player statistics.

## Module Structure

```
ocr/
├── __init__.py         # Module initialization
├── parser.py           # OCR screenshot parsing
├── stats_manager.py    # Player statistics management
├── reczone.py          # Discord integration and commands
├── stats_data.json     # Persistent stats storage (auto-generated)
└── README.md          # This file
```

## Components

### parser.py - OCRParser

Handles screenshot processing and data extraction:
- Downloads images from Discord
- Uses Tesseract OCR to extract text from specific regions
- Parses player names, scores, K/D/A stats, and match time
- Returns structured data for stats tracking

**Key methods:**
- `parse_screenshot(image_bytes)` - Main parsing function
- `_parse_match_time()` - Extracts match duration
- `_parse_players()` - Extracts all 4 player stats
- `_parse_single_player()` - Parses individual player card

### stats_manager.py - StatsManager

Manages player statistics storage and retrieval:
- Loads/saves stats from JSON file
- Updates player stats when new screenshots are processed
- Generates leaderboards sorted by various categories
- Formats data for Discord embeds

**Key methods:**
- `update_player_stats(parsed_data)` - Add stats from a new screenshot
- `get_leaderboard(category, min_games)` - Get sorted rankings
- `format_leaderboard_embed(category)` - Create Discord embed
- `save_stats()` / `load_stats()` - Persistence

### reczone.py - RecZoneManager

Discord bot integration:
- Monitors configured channel for screenshot uploads
- Automatically processes new images
- Sends confirmation/error messages
- Implements stats commands
- Can scan channel history for existing screenshots

**Key methods:**
- `process_message(message)` - Handle new Discord messages
- `scan_channel_history(limit)` - Process old screenshots
- `register_commands(bot)` - Register Discord commands

## Data Structure

### Parsed Screenshot Data
```python
{
    'match_time': 19.93,  # Minutes
    'players': [
        {
            'name': 'nuke',
            'score': 12525,
            'kills': 12,
            'deaths': 1,
            'assists': 5
        },
        # ... 3 more players
    ]
}
```

### Player Stats Storage
```json
{
  "nuke": {
    "display_name": "nuke",
    "wins": 10,
    "kills": 120,
    "deaths": 15,
    "assists": 50,
    "score": 125000,
    "playtime": 199.5,
    "games_played": 10
  }
}
```

## Discord Commands

### fs.stats [category]
Display leaderboard for specified stat category.

**Categories:**
- `wins` - Victory count (default)
- `kills` - Total kills
- `deaths` - Total deaths
- `assists` - Total assists
- `score` - Total score
- `playtime` - Total match time
- `games_played` - Number of matches

**Example:**
```
fs.stats kills
```

### fs.scanreczone [limit]
Scan channel history for existing screenshots (Admin only).

**Example:**
```
fs.scanreczone 100
```

## Configuration

Set in `config.ini`:
```ini
[RecZone]
reczone_read_channel_id = 1433349098077032498
reczone_write_channel_id = 1150575800266002442
```

## Features

### Automatic Processing
- Bot monitors the read channel for image uploads
- Automatically parses and stores stats
- Sends confirmation message with extracted data
- Posts errors to write channel if parsing fails

### Case-Insensitive Names
- Player names stored in lowercase for consistency
- Original capitalization preserved in `display_name`
- "Nuke", "nuke", "NUKE" all map to same player

### Minimum Games Filter
- Leaderboards only show players with 2+ games
- Prevents one-time players from cluttering stats

### Historical Scanning
- Can process screenshots posted before bot setup
- Admin command to scan up to last 100 messages
- Useful for importing existing data

## OCR Regions

The parser divides the screenshot into regions for extraction:

1. **Top Right** - Match time (MM:SS format)
2. **Player Cards** - 4 horizontal sections containing:
   - Player name (top)
   - Score (large number)
   - K/D/A stats (bottom, 3 numbers)

## Dependencies

- `pytesseract` - Python wrapper for Tesseract OCR
- `opencv-python` - Image processing
- `Pillow` - Image handling
- `discord.py` - Discord bot integration
- `aiohttp` - Async HTTP for downloading images

## Error Handling

- Failed downloads → error message to write channel
- OCR parsing failures → error message to write channel
- Invalid data → skipped, no stats update
- All errors logged to console with stack traces

## Performance

- Async processing allows multiple screenshots simultaneously
- Image processing done in-memory (no disk I/O)
- Stats saved immediately after each update
- JSON format allows easy manual editing if needed

## Future Enhancements

Possible improvements:
- Machine learning for better OCR accuracy
- Support for different game modes
- Per-weapon statistics
- Time-based analytics (daily/weekly stats)
- Player comparison features
- Export to CSV/Excel
