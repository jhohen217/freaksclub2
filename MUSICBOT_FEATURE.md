# Music Bot Nickname Feature

## Overview
The bot now automatically renames music bots' server nicknames to display the currently playing song. After 8 minutes of no activity, the nickname resets to the original basename.

## Configuration

### Config File (`config.ini`)
```ini
[MusicBots]
bot_user_ids = 412347553141751808, 239631525350604801
bot_basenames = 
```

- **bot_user_ids**: Comma-separated list of music bot Discord user IDs to track
- **bot_basenames**: Comma-separated list of basenames matching the order of bot_user_ids (auto-captured on startup)

**Example after first run:**
```ini
[MusicBots]
bot_user_ids = 412347553141751808, 239631525350604801
bot_basenames = 🌭freakswim.FM, MusicBot
```
The basenames list uses **index matching** - the first basename corresponds to the first bot ID, second to second, etc.

## How It Works

### 1. Startup Behavior
- When the bot starts, it captures the current nickname of each tracked music bot
- These basenames are saved to `config.ini` for persistence
- If basenames already exist in config, they are loaded instead of re-captured

### 2. Message Monitoring
- Monitors the `designated_channel_id` for messages from tracked music bots
- Looks for messages containing "Started playing [song] by [artist]"
- Example: "🎵 Started playing Little Lies by Fleetwood Mac"

### 3. Nickname Changing
- When a song is detected, the bot's nickname is changed to:
  - Format: `"{song_title} - {artist}"`
  - Example: `"Little Lies - Fleetwood Mac"`

### 4. Timer Management
- **8-minute timer** starts when a nickname is changed
- If a new song starts before 8 minutes, the old timer is cancelled and a new one starts
- After 8 minutes of no new songs, the nickname resets to the basename

### 5. Multi-Bot Support
- Tracks multiple music bots simultaneously
- Each bot has its own independent timer
- Different basenames can be configured for each bot

## Message Parsing

The parser uses regex to extract song information:
- Pattern: `Started playing {song} by {artist}`
- Case-insensitive matching
- Automatically cleans up emoji and special characters

## Example Workflow

1. **Music bot posts:** "🎵 Started playing Little Lies by Fleetwood Mac"
2. **Bot detects message** and extracts: song="Little Lies", artist="Fleetwood Mac"
3. **Nickname changed to:** "Little Lies - Fleetwood Mac"
4. **8-minute timer starts**
5. **If another song plays:** Timer resets, nickname updates to new song
6. **If 8 minutes pass:** Nickname resets to "🌭freakswim.FM" (or configured basename)

## Technical Details

### Files Modified
- `musicbot.py` - New module with MusicBotManager class
- `main.py` - Integration of music bot manager
- `config.ini` - Added [MusicBots] section

### Key Functions
- `capture_basenames()` - Captures original nicknames on startup
- `parse_song_info()` - Extracts song/artist from message
- `change_bot_nickname()` - Updates nickname and manages timers
- `reset_to_basename()` - Async timer function to restore original name
- `process_message()` - Main message handler

### Timer Logic
- Uses `asyncio.create_task()` to run timers in background
- Timers stored in `active_timers` dictionary: `{bot_id: asyncio.Task}`
- Old timers are cancelled with `.cancel()` when new songs start
- Each bot has independent timer management

## Permissions Required

The bot must have permission to:
- **Manage Nicknames** - To change music bot nicknames
- **Read Messages** - To monitor the channel
- **View Channel** - To access the designated channel

## Troubleshooting

### Bot doesn't change nicknames
- Check that bot has "Manage Nicknames" permission
- Verify bot's role is higher than the music bot's role
- Check console for error messages

### Basenames not captured
- Ensure music bots are in the server when bot starts
- Verify user IDs are correct in config
- Check console logs for capture status

### Songs not detected
- Verify messages are in the designated channel
- Check message format matches "Started playing [song] by [artist]"
- Review console logs for parsing attempts

## Adding More Music Bots

To track additional music bots:

1. Get the bot's Discord User ID
2. Add to `bot_user_ids` in config.ini:
   ```ini
   bot_user_ids = 412347553141751808, 239631525350604801, NEW_BOT_ID
   ```
3. Clear or add to `bot_basenames` (leaving empty will auto-capture):
   ```ini
   bot_basenames = 
   ```
   Or manually add the new basename to the list:
   ```ini
   bot_basenames = 🌭freakswim.FM, MusicBot, NewBotName
   ```
4. Restart the bot

**Note:** The order of basenames must match the order of bot_user_ids!

## Console Output

When working correctly, you'll see:
```
MusicBotManager initialized with 2 music bot(s)
🎵 Capturing music bot basenames...
Captured basename for bot 412347553141751808: 🌭freakswim.FM
Loaded basename for bot 239631525350604801: MusicBot
✅ Music bot basenames captured

Detected song from bot 412347553141751808: Little Lies - Fleetwood Mac
Changed bot 412347553141751808 nickname to: Little Lies - Fleetwood Mac
Started 8-minute reset timer for bot 412347553141751808
```
