# FreakSwim Bot GUI - Setup Instructions

## Quick Start

### Step 1: Install Dependencies
Open a command prompt in the project directory and run:
```bash
pip install -r requirements.txt
```

This will install:
- discord.py (Discord bot library)
- aiohttp (HTTP client for Discord)
- pyinstaller (For building the .exe)

### Step 2: Build the GUI Executable
Run the build script:
```bash
build.bat
```

The script will:
1. Check if PyInstaller is installed (install if needed)
2. Build the GUI as a single .exe file
3. Copy `FreakSwimGUI.exe` to the root folder
4. Display completion message

### Step 3: Run the Application

#### Option A: Run as Python Script (Development)
```bash
python gui.py
```

#### Option B: Run as Executable (Production)
1. Ensure these files are in the same folder:
   - `FreakSwimGUI.exe`
   - `config.ini`
   - `icon.png`
   - `banners/` folder
   - `icons/` folder

2. Double-click `FreakSwimGUI.exe`

## What You Get

### Dark-Themed GUI
- Professional dark theme (inspired by VS Code)
- Colors:
  - Background: `#1e1e1e`
  - Foreground: `#d4d4d4`
  - Accent: `#007acc`
  - Success: `#4ec9b0`
  - Error: `#f48771`
  - Admin: `#c586c0`

### Console Feed (Left Side)
- Real-time bot logs
- Color-coded messages
- Auto-scrolling
- Copy/paste support

### Command Buttons (Right Side)
Organized into sections:
- **General Commands**: test, help
- **RGB Commands**: random color, red, green, blue, purple, cyan
- **Banner Commands**: list, view banners 1-3
- **Icon Commands**: list, view icons 1-3
- **Admin Commands**: timer presets (60s, 120s, 300s)

### Bot Control
- **Start Bot**: Launch Discord bot in background thread
- **Stop Bot**: Safely shut down bot
- **Status Indicator**: Visual online/offline status

### Command Input
- Text field for custom commands
- Press Enter or click Send
- Examples:
  - `timer 180` - Set 3 minute interval
  - `rgb 255 128 0` - Set orange color
  - `banner myfile.png` - View specific banner

## File Structure

```
freakswim/
├── FreakSwimGUI.exe       # Compiled executable (created by build.bat)
├── gui.py                 # GUI source code
├── build.bat              # Build script
├── config.ini             # Bot configuration (required)
├── icon.png               # Application icon (required)
├── main.py                # Original CLI bot
├── rgb.py                 # RGB manager module
├── banner.py              # Banner manager module
├── icon.py                # Icon manager module
├── requirements.txt       # Python dependencies
├── GUI_README.md          # User guide
├── SETUP_INSTRUCTIONS.md  # This file
├── banners/               # Banner images folder
└── icons/                 # Icon images folder
```

## Troubleshooting

### "Module not found" errors
Run: `pip install -r requirements.txt`

### Build fails with UNC path error
Windows UNC paths (`\\server\share`) may cause issues.
Solution: Map the network drive to a letter (e.g., `Z:\`) and build from there

### GUI window doesn't show icon
Ensure `icon.png` is in the same folder as the .exe

### Bot won't start
1. Check `config.ini` exists and has valid bot token
2. Verify bot has proper Discord permissions
3. Check console feed for error messages

### "Config file not found" error
The .exe looks for `config.ini` in its own directory. Ensure it's there.

## Build Options

The build script uses these PyInstaller options:
- `--onefile`: Single executable file
- `--windowed`: No console window
- `--icon=icon.png`: Application icon
- `--name=FreakSwimGUI`: Output name
- `--add-data "icon.png;."`: Bundle icon in exe

### Custom Build
For advanced users, you can modify the build command:
```bash
pyinstaller --noconfirm --onefile --windowed --icon=icon.png --name=FreakSwimGUI --add-data "icon.png;." gui.py
```

## Deployment

To deploy the GUI to another computer:

1. Copy these files to the target folder:
   - `FreakSwimGUI.exe`
   - `config.ini` (with your bot token)
   - `icon.png`
   - `banners/` folder (with your images)
   - `icons/` folder (with your images)

2. No Python installation needed on target computer!

3. Double-click `FreakSwimGUI.exe` to run

## Features Summary

✅ Dark theme interface
✅ Real-time console logging with color coding
✅ Organized command buttons by category
✅ Start/Stop bot control
✅ Visual status indicator
✅ Custom command input field
✅ Thread-safe bot execution
✅ Single .exe compilation
✅ Custom window icon from icon.png
✅ Portable deployment (no Python needed)
✅ Config file support (reads from same folder)
✅ Auto-scrolling console
✅ Button hover effects
✅ 1000x700 resizable window

## Technical Details

### Threading
- GUI runs on main thread
- Bot runs on separate daemon thread
- Queue-based communication for console output

### Console Redirection
- Captures stdout and stderr
- Thread-safe message queue
- Updates every 100ms

### Configuration
- Reads config.ini at startup
- Validates required sections
- Uses relative paths for resources

### Bot Integration
- Full integration with existing bot code
- All RGB, banner, and icon features work
- Command registration at runtime

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Test
