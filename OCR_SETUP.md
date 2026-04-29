# OCR Setup Guide for RecZone Stats Tracking

This guide will help you set up the OCR functionality for tracking player statistics from Battle Royale victory screenshots.

## Prerequisites

The OCR system requires **Tesseract OCR** to be installed on your system.

## Installing Tesseract OCR

### Windows

1. **Download Tesseract**
   - Visit: https://github.com/UB-Mannheim/tesseract/wiki
   - Download the latest Windows installer (e.g., `tesseract-ocr-w64-setup-5.3.3.exe`)

2. **Install Tesseract**
   - Run the installer
   - **Important**: During installation, note the installation path (default: `C:\Program Files\Tesseract-OCR`)
   - Complete the installation

3. **Configure Python to Find Tesseract**
   
   If Tesseract is not in your system PATH, you need to tell Python where to find it.
   
   Open `ocr/parser.py` and uncomment this line (around line 16):
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```
   
   Adjust the path if you installed Tesseract in a different location.

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Fedora/RHEL
sudo dnf install tesseract

# Arch Linux
sudo pacman -S tesseract
```

### macOS

```bash
# Using Homebrew
brew install tesseract
```

## Installing Python Dependencies

Install the required Python packages:

```bash
pip install pytesseract opencv-python
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Configuration

The RecZone channels are configured in `config.ini`:

```ini
[RecZone]
reczone_read_channel_id = 1433349098077032498  # Channel to monitor for screenshots
reczone_write_channel_id = 1150575800266002442  # Channel for bot messages
```

- **reczone_read_channel_id**: The channel where victory screenshots are posted
- **reczone_write_channel_id**: The channel where the bot sends confirmation/error messages

## How It Works

### Automatic Screenshot Processing

1. When a user posts an image in the RecZone read channel, the bot automatically:
   - Downloads the image
   - Runs OCR to extract player data
   - Updates the stats database (`ocr/stats_data.json`)
   - Sends a confirmation message to the write channel

2. The bot extracts the following data for each player:
   - Player name
   - Score
   - Kills
   - Deaths
   - Assists
   - Match time (added to playtime)
   - Win count (each screenshot = 1 win)

### Scanning Existing Screenshots

To process screenshots that were already posted before the bot was set up:

```
fs.scanreczone [limit]
```

- `limit`: Number of messages to scan (default: 100)
- **Admin only command**

Example:
```
fs.scanreczone 50
```

This will scan the last 50 messages in the RecZone channel and process any images found.

## Using Stats Commands

### View Leaderboards

```
fs.stats [category]
```

**Available categories:**
- `wins` - Total victories
- `kills` - Total kills
- `deaths` - Total deaths
- `assists` - Total assists
- `score` - Total score
- `playtime` - Total match time
- `games_played` - Number of matches recorded

**Examples:**
```
fs.stats wins
fs.stats kills
fs.stats playtime
```

### Default Behavior

If you just type `fs.stats` with no category, it defaults to `wins`.

### Help

If you enter an invalid category, the bot will show you the available options:
```
fs.stats invalid
```

## Minimum Games Requirement

Players must appear in at least **2 screenshots** to be displayed on the leaderboard. This prevents one-time players from cluttering the stats.

## Data Storage

Player statistics are stored in `ocr/stats_data.json`:

```json
{
  "nuke": {
    "display_name": "nuke",
    "wins": 2,
    "kills": 19,
    "deaths": 1,
    "assists": 10,
    "score": 24745,
    "playtime": 41.25,
    "games_played": 2
  },
  "dill": {
    ...
  }
}
```

### Resetting Stats

To reset all stats, simply delete the `ocr/stats_data.json` file. The bot will create a new one automatically.

## Troubleshooting

### OCR Not Working

1. **Verify Tesseract Installation**
   ```bash
   tesseract --version
   ```
   Should show the Tesseract version.

2. **Check Tesseract Path**
   - On Windows, make sure the path in `ocr/parser.py` is correct
   - Uncomment and update the `tesseract_cmd` line if needed

3. **Check Bot Logs**
   - The console will show any OCR errors
   - Error messages will also be posted to the write channel

### No Players Detected

If the OCR fails to detect players:
- The screenshot format may be different than expected
- Check the bot's error message in the write channel
- The image quality might be too low
- The layout might have changed (game updates)

### Stats Not Updating

1. Verify the bot is monitoring the correct channel
2. Check that images are being posted, not links
3. Ensure the bot has permission to read message history
4. Check console logs for errors

## OCR Accuracy

The OCR system is optimized for Battle Royale Squads victory screens with the layout shown in the example screenshots. If the game's UI changes, the OCR regions may need to be adjusted in `ocr/parser.py`.

### Improving Accuracy

If you notice OCR errors:
1. Post higher resolution screenshots (1920x1080 or better)
2. Ensure the screenshot is clear and not compressed
3. Report issues so the OCR regions can be fine-tuned

## Technical Notes

- **Case-insensitive**: Player names are stored case-insensitively (e.g., "Nuke" and "nuke" are the same)
- **Display names**: The bot remembers the most complete capitalization it has seen
- **Async processing**: Multiple screenshots can be processed simultaneously
- **Channel history**: The bot can process old images when it starts up
