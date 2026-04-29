# Startup Scan Feature

## Overview
The bot now automatically scans for missed screenshots when it starts up. This ensures that any screenshots posted while the bot was offline are caught and processed.

## How It Works

### 1. Automatic Startup Scan
When the bot starts (in `on_ready()` event), it automatically calls `scan_missed_messages()` to catch up on any missed screenshots.

### 2. Smart Scanning Algorithm
The scan works backward through message history and:
- Checks each image attachment for processing status
- Stops when it finds a screenshot that was already processed
- This prevents unnecessary scanning of old messages
- Processes any unprocessed screenshots it finds along the way

### 3. Duplicate Prevention
The system uses a robust tracking mechanism:
- Each screenshot is identified by: `message_id + attachment_id`
- This combination is stored in `screenshot_log.json`
- Before processing any screenshot, the bot checks if it's already in the log
- This prevents double-counting stats even if the scan runs multiple times

### 4. Configuration
In `main.py`, the scan is configured with:
```python
await reczone_manager.scan_missed_messages(max_messages=100)
```

**max_messages**: Safety limit on how far back to scan (default: 100 messages)
- Adjust this based on your channel activity
- Higher values scan further back but take longer
- The scan stops early when it finds a processed message

## Example Output

### When Missed Screenshots Are Found:
```
🔍 Scanning for missed screenshots in channel 123456789...
📸 Found missed screenshot: victory_001.png
✓ RecZone: OCR parsing successful!
  → Found 4 player(s): Dill, Chebday, nuke, JimmyHimself
  → Match time: 19.93 minutes
✓ Found already-processed screenshot: victory_000.png (stopping scan)
✅ Startup scan complete: Processed 1 missed screenshot(s) from 15 messages
```

### When No Missed Screenshots:
```
🔍 Scanning for missed screenshots in channel 123456789...
✓ Found already-processed screenshot: victory_000.png (stopping scan)
✓ Startup scan complete: No missed screenshots found (scanned 1 messages)
```

## Discord Notification
When missed screenshots are found and processed, the bot sends a notification to the write channel:
```
🔄 Bot Startup: Caught up on 1 missed screenshot(s)
```

## Benefits

1. **No Lost Data**: Screenshots posted during downtime are automatically caught
2. **Efficient**: Stops scanning as soon as it catches up
3. **Safe**: Uses existing duplicate prevention - won't double-count
4. **Transparent**: Logs all activity to console and notifies in Discord

## Technical Details

### Files Modified
- `ocr/reczone.py`: Added `scan_missed_messages()` method
- `main.py`: Added startup scan call in `on_ready()` event

### Key Methods
- `scan_missed_messages(max_messages)`: Main scanning logic
- `is_screenshot_processed(message_id, attachment_id)`: Duplicate detection
- `_process_screenshot(attachment, message)`: Screenshot processing

### Data Storage
All processed screenshots are tracked in `ocr/screenshot_log.json`:
```json
{
  "message_id_attachment_id": {
    "message_id": "123...",
    "attachment_id": "456...",
    "filename": "screenshot.png",
    "processed_at": "2025-10-31T13:31:20.712414",
    "match_time": 19.93,
    "players": [...]
  }
}
```

## Troubleshooting

### Scan Takes Too Long
- Reduce `max_messages` parameter
- Check channel activity level

### Screenshots Processed Multiple Times
- Should not happen due to duplicate detection
- Check `screenshot_log.json` for corruption
- Verify message/attachment IDs are consistent

### Scan Doesn't Find Screenshots
- Verify RecZone read channel ID is correct in `config.ini`
- Check that screenshots have image content types
- Ensure bot has permission to read message history
