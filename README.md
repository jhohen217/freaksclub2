# FreakRGB Discord Bot

A Discord bot that manages server banners and role colors.

## Features

- **Banner Management**
  - Automatically cycles server banners every 20 seconds
  - Allows server boosters to add new banners
  - Stores banners locally for persistence
  - Commands to list, show, and delete banners

- **RGB Role Color**
  - Cycles a specified role through RGB colors
  - Configurable color change interval

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/freakrgb.git
cd freakrgb
```

2. Copy the example config and update it:
```bash
cp config.json.example config.json
```

3. Update config.json with your settings:
```json
{
    "rgb_role_id": 1150577684771000382,
    "booster_role_id": 1172098000563228716,
    "color_change_interval": 3600,
    "banner_change_interval": 20,
    "banner_storage_path": "/path/to/banner/storage"
}
```

4. Create a .env file with your Discord bot token:
```
DISCORD_BOT_TOKEN=your_token_here
```

## Commands

- `/banners` - List all saved banner images
- `/showbanner <number/filename>` - Display a specific banner image
- `/deletebanner <number/filename>` - Delete a specific banner image
- `/help` - Show command documentation
- `rgb! [seconds]` - Change RGB cycle timing

## Adding Banners

1. Post an image in the radio channel
2. Tag the bot in your message
3. Must have the server booster role

## Requirements

- Python 3.8+
- discord.py
- python-dotenv
- aiohttp

## Running the Bot

Simply run:
```bash
python freakrgb/main.py
