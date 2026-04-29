@echo off
chcp 65001 >nul
cls
echo ================================
echo FreakSwim Bot - Launcher
echo ================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Handle UNC paths by using pushd (auto-maps to drive letter)
pushd "%SCRIPT_DIR%"
if errorlevel 1 (
    echo ERROR: Could not access script directory!
    pause
    exit /b 1
)

REM Check for config file and auto-create from example if needed
echo Checking for config file...
if not exist "config.ini" (
    if not exist "config.json" (
        if exist "config.ini.example" (
            echo Config file not found. Creating from template...
            copy "config.ini.example" "config.ini"
            echo.
            echo ================================
            echo IMPORTANT: Please edit config.ini
            echo and add your bot token and server IDs!
            echo ================================
            echo.
            notepad "config.ini"
            pause
        ) else if exist "config.json.example" (
            echo Config file not found. Creating from template...
            copy "config.json.example" "config.json"
            echo.
            echo ================================
            echo IMPORTANT: Please edit config.json
            echo and add your bot token and server IDs!
            echo ================================
            echo.
            notepad "config.json"
            pause
        )
    )
)

REM Check Python version (require 3.12+)
echo Checking Python version...
python -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>NUL
if errorlevel 1 (
    echo.
    echo ================================
    echo ERROR: Python 3.12 or higher required!
    echo ================================
    python --version
    echo.
    echo Please install Python 3.12 or higher from https://www.python.org/downloads/
    popd
    pause
    exit /b 1
)
echo Python version OK
echo.

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import discord" 2>NUL
if errorlevel 1 (
    echo Dependencies not installed. Installing from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies!
        popd
        pause
        exit /b 1
    )
    echo.
)
echo Dependencies OK
echo.

REM Set up error handling - redirect stderr to temp file
set ERROR_FILE=%TEMP%\freakswim_err_%RANDOM%.tmp

REM Launch the GUI using pythonw (no console window)
echo Starting FreakSwim Bot GUI...
start "" pythonw gui.py

REM Wait a moment for GUI to initialize
timeout /t 2 /nobreak >nul

REM Show confirmation
echo.
echo ================================
echo GUI launched successfully!
echo ================================
echo Bot is running. Check the GUI window.
echo Close GUI window to stop the bot.
echo.
popd
exit
