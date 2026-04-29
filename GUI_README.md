# FreakSwim Bot GUI - User Guide

## Overview
The FreakSwim Bot GUI provides a dark-themed control panel for managing your Discord bot with:
- **Console Feed**: Real-time display of bot logs and activity
- **Command Buttons**: Quick access to all bot commands
- **Bot Control**: Start/Stop the bot with visual status indicators

## Building the Executable

### Prerequisites
1. Python 3.8 or higher installed
2. All dependencies installed: `pip install -r requirements.txt`

### Build Steps
1. Open a command prompt in the project directory
2. Run the build script: `build.bat`
3. Wait for the build to complete
4. The executable will be created as `FreakSwimGUI.exe` in the root folder

### What Gets Built
- **Single .exe file**: `FreakSwimGUI.exe`
- **Icon**: Uses `icon.png` as the application icon
- **Portable**: Can be copied to any folder

## Running the GUI

### Required Files (in same folder as .exe)
```
FreakSwimGUI.exe
config.ini          (your bot configuration)
icon.png            (for the window icon)
banners/            (folder with banner images)
icons/              (folder with icon images)
```

### Usage
1. Double-click `FreakSwimGUI.exe`
2. The GUI will open with dark theme
3. Click "▶ Start Bot" to launch the Discord bot
4. Monitor bot activity in the Console Feed
5. Use command buttons to test functionality
6. Click "■ Stop Bot" when finished

## GUI Features

### Console Feed (Left Panel)
- Displays all bot logs in real-time
- Color-coded messages:
  - **Green**: Success messages
  - **Red**: Error messages
  - **Purple**: Admin commands
  - **Blue**: Informational messages
- Auto-scrolls to show latest activity

### Command Buttons (Right Panel)

#### General Commands
- Test - Verify bot is responding
- Help - Show all available commands
- RGB Help - Display RGB-specific commands

#### RGB Commands
- Random RGB Color - Apply random color
- RGB Red/Green/Blue/Purple/Cyan - Apply specific colors

#### Banner Commands
- List Banners - Show all saved banners
- View Banner 1/2/3 - Display specific banners

#### Icon Commands
- List Icons - Show all saved icons
- View Icon 1/2/3 - Display specific icons

#### Admin Commands
- Set Timer (60s/120s/300s) - Adjust update intervals

### Command Input (Bottom)
- Type custom commands with parameters
- Press Enter or click Send to execute
- Example: `timer 180` for 3-minute intervals

## Configuration

The GUI reads from `config.ini` in the same folder. Ensure all settings are correct:
- Discord bot token
- Server ID
- Role IDs
- Channel IDs
- File paths

## Troubleshooting

### Build Issues
- **PyInstaller not found**: Run `pip install pyinstaller`
- **Build fails**: Check Python version (3.8+)
- **Missing icon**: Ensure `icon.png` exists in project folder

### Runtime Issues
- **Bot won't start**: Check `config.ini` is present and valid
- **No commands work**: Verify bot token is correct
- **Console empty**: Check bot permissions on Discord

### Path Issues
- All file paths in `config.ini` should be relative or absolute
- Banners and icons folders must exist
- The .exe looks for files relative to its location

## Notes

- The GUI runs the bot in a separate thread
- Console output is captured and displayed in real-time
- Stop the bot before closing the GUI for clean shutdown
- Direct command execution shows info but requires Discord to test
- Window size: 1000x700 pixels (adjustable by dragging)

## Development

To run without building:
```bash
python gui.py
```

To rebuild after changes:
```bash
build.bat
```

## Features

✓ Dark theme UI (VS Code inspired)
✓ Real-time console logging
✓ Organized command buttons
✓ Bot status indicator
✓ Custom command input
✓ Thread-safe bot execution
✓ Single .exe compilation
✓ Custom window icon
✓ Portable deployment

## Support

For issues or questions about the bot functionality, refer to the main README.md or check the Discord server.
