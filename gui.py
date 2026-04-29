"""
FreakSwim Discord Bot - GUI Control Panel
Dark-themed GUI with console feed and command buttons
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import queue
import sys
import os
from pathlib import Path
import configparser

# Import bot modules
import discord
from discord.ext import commands
import freakrgb.rgb_manager as rgb_manager_mod
import freakrgb.banner_manager as banner_manager_mod
import freakrgb.avatar_manager as avatar_manager_mod
import browser


class ConsoleRedirector:
    """Redirects stdout/stderr to GUI console"""
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue
        
    def write(self, message):
        if message.strip():
            self.queue.put(message)
    
    def flush(self):
        pass


class BotGUI:
    """Main GUI application for Discord bot control"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("FreakSwim Bot Control Panel")
        self.root.geometry("1000x700")
        
        # Dark theme colors
        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
        self.button_bg = "#2d2d2d"
        self.button_hover = "#3e3e3e"
        self.accent_color = "#007acc"
        self.admin_color = "#c586c0"
        self.success_color = "#4ec9b0"
        self.error_color = "#f48771"
        
        # Set window background
        self.root.configure(bg=self.bg_color)
        
        # Set window icon
        try:
            # Get correct path for both .py and .exe
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            icon_path = application_path / "icon.png"
            if icon_path.exists():
                self.root.iconphoto(True, tk.PhotoImage(file=str(icon_path)))
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        # Bot variables
        self.bot = None
        self.bot_thread = None
        self.bot_running = False
        self.config = None
        
        # Queue for console output
        self.console_queue = queue.Queue()
        
        # Create GUI elements first (needed before loading config)
        self.create_widgets()
        
        # Load configuration (after widgets are created)
        self.load_config()
        
        # Start console update loop
        self.update_console()
        
        # Auto-start the bot
        self.root.after(1000, self.start_bot)  # Start after 1 second
    
    def load_config(self):
        """Load bot configuration"""
        try:
            # Get correct path for both .py and .exe
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            config_path = application_path / "config.ini"
            self.config = configparser.ConfigParser()
            self.config.read(config_path, encoding='utf-8')
            self.log_message("✓ Configuration loaded successfully", self.success_color)
        except Exception as e:
            self.log_message(f"✗ Error loading config: {e}", self.error_color)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container with two columns using PanedWindow for resizable sidebar
        main_container = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            bg=self.bg_color,
            sashwidth=8,
            sashrelief=tk.RAISED,
            bd=0
        )
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left column - Console feed
        left_frame = tk.Frame(main_container, bg=self.bg_color)
        
        console_label = tk.Label(
            left_frame,
            text="Console Feed",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_color,
            fg=self.fg_color
        )
        console_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Console text area
        self.console = scrolledtext.ScrolledText(
            left_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#0e0e0e",
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for colored text
        self.console.tag_config("success", foreground=self.success_color)
        self.console.tag_config("error", foreground=self.error_color)
        self.console.tag_config("admin", foreground=self.admin_color)
        self.console.tag_config("accent", foreground=self.accent_color)
        
        # Right column - Control buttons (resizes with window)
        right_frame = tk.Frame(main_container, bg=self.bg_color)
        
        # Add both frames to PanedWindow
        main_container.add(left_frame, minsize=300)
        main_container.add(right_frame, minsize=250)
        
        # Bot Control Section
        control_header_frame = tk.Frame(right_frame, bg=self.bg_color)
        control_header_frame.pack(fill=tk.X, pady=(0, 5))
        
        control_label = tk.Label(
            control_header_frame,
            text="Bot Control",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_color,
            fg=self.fg_color
        )
        control_label.pack(side=tk.LEFT)
        
        # Status indicator in Bot Control section
        self.status_label = tk.Label(
            control_header_frame,
            text="● Offline",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.error_color
        )
        self.status_label.pack(side=tk.RIGHT)
        
        control_frame = tk.Frame(right_frame, bg=self.bg_color)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = self.create_button(
            control_frame,
            "▶ Start Bot",
            self.start_bot,
            self.success_color
        )
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.stop_button = self.create_button(
            control_frame,
            "■ Stop Bot",
            self.stop_bot,
            self.error_color
        )
        self.stop_button.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.stop_button.config(state=tk.DISABLED)
        
        # Commands Section with scrollable canvas
        commands_label = tk.Label(
            right_frame,
            text="Commands",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_color,
            fg=self.fg_color
        )
        commands_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Create canvas and scrollbar for commands
        canvas_frame = tk.Frame(right_frame, bg=self.bg_color)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        commands_container = tk.Frame(canvas, bg=self.bg_color)
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=commands_container, anchor=tk.NW)
        
        # Bind canvas resize to update scroll region
        def on_canvas_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update window width to match canvas width
            canvas.itemconfig(canvas_window, width=event.width)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        canvas.bind('<Configure>', on_canvas_configure)
        commands_container.bind('<Configure>', on_frame_configure)
        
        # Bind mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Command buttons
        self.create_command_sections(commands_container)
        
        # Input section at bottom
        input_frame = tk.Frame(self.root, bg=self.bg_color)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        input_label = tk.Label(
            input_frame,
            text="Command Input:",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.fg_color
        )
        input_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.command_input = tk.Entry(
            input_frame,
            font=("Consolas", 10),
            bg=self.button_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.FLAT
        )
        self.command_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.command_input.bind("<Return>", lambda e: self.send_custom_command())
        
        send_button = self.create_button(
            input_frame,
            "Send",
            self.send_custom_command,
            self.accent_color
        )
        send_button.pack(side=tk.RIGHT)
    
    def create_button(self, parent, text, command, color=None):
        """Create a styled button"""
        if color is None:
            color = self.accent_color
            
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 8),  # Smaller font
            bg=self.button_bg,
            fg=color,
            activebackground=self.button_hover,
            activeforeground=color,
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,  # Smaller padding
            pady=3   # Smaller padding
        )
        
        # Hover effects
        button.bind("<Enter>", lambda e: button.config(bg=self.button_hover))
        button.bind("<Leave>", lambda e: button.config(bg=self.button_bg))
        
        return button
    
    def create_command_sections(self, parent):
        """Create command button sections"""
        # General Commands
        self.create_section(parent, "General Commands", [
            ("Test", "test", self.fg_color),
            ("Help", "help", self.fg_color),
        ])
        
        # RGB Commands
        self.create_section(parent, "RGB Commands", [
            ("Random RGB Color", "rgb", self.success_color),
            ("RGB Red", lambda: self.send_command("rgb 255 0 0"), "#ff0000"),
            ("RGB Green", lambda: self.send_command("rgb 0 255 0"), "#00ff00"),
            ("RGB Blue", lambda: self.send_command("rgb 0 0 255"), "#0000ff"),
            ("RGB Purple", lambda: self.send_command("rgb 128 0 128"), "#800080"),
            ("RGB Cyan", lambda: self.send_command("rgb 0 255 255"), "#00ffff"),
        ])
        
        # Banner Commands
        self.create_section(parent, "Banner Commands", [
            ("List Banners", "banners", self.accent_color),
            ("📁 Explore Banner Folder", self.open_banner_folder, self.accent_color),
        ])
        
        # Icon Commands
        self.create_section(parent, "Icon Commands", [
            ("List Icons", "icons", self.accent_color),
            ("📁 Explore Icon Folder", self.open_icon_folder, self.accent_color),
        ])
        
        # OCR/RecZone Stats Section
        self.create_ocr_stats_section(parent)
        
        # Browser Commands
        self.create_section(parent, "Browser Commands", [
            ("🖥️ Full / Windowed", self.browser_fullscreen_toggle, self.accent_color),
            ("🔳 Min (Windowed)", self.browser_minimize, self.fg_color),
            ("🔄 Refresh Page", self.browser_refresh, self.success_color),
            ("📑 List Bookmarks", self.browser_list_bookmarks, self.accent_color),
            ("✖ Close Browser", self.browser_close, self.error_color),
        ])
        
        # Admin Commands
        self.create_section(parent, "Admin Commands", [
            ("Set Timer (60s)", lambda: self.send_command("timer 60"), self.admin_color),
            ("Set Timer (120s)", lambda: self.send_command("timer 120"), self.admin_color),
            ("Set Timer (300s)", lambda: self.send_command("timer 300"), self.admin_color),
        ])
    
    def create_section(self, parent, title, buttons):
        """Create a section with title and buttons"""
        section_frame = tk.Frame(parent, bg=self.bg_color)
        section_frame.pack(fill=tk.X, pady=(5, 10))
        
        # Section title
        title_label = tk.Label(
            section_frame,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
            anchor=tk.W
        )
        title_label.pack(fill=tk.X, pady=(0, 5))
        
        # Buttons in grid
        for i, (text, command, color) in enumerate(buttons):
            if callable(command):
                cmd = command
            else:
                cmd = lambda c=command: self.send_command(c)
            
            button = self.create_button(section_frame, text, cmd, color)
            button.pack(fill=tk.X, pady=2)
    
    def create_ocr_stats_section(self, parent):
        """Create OCR stats display section"""
        section_frame = tk.Frame(parent, bg=self.bg_color)
        section_frame.pack(fill=tk.X, pady=(5, 10))
        
        # Section title
        title_label = tk.Label(
            section_frame,
            text="RecZone Stats",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
            anchor=tk.W
        )
        title_label.pack(fill=tk.X, pady=(0, 5))
        
        # Stats display area
        stats_display = tk.Frame(section_frame, bg=self.button_bg, relief=tk.FLAT)
        stats_display.pack(fill=tk.X, pady=(0, 5))
        
        self.stats_text = tk.Text(
            stats_display,
            height=6,
            font=("Consolas", 8),
            bg=self.button_bg,
            fg=self.fg_color,
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.stats_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Refresh button and stat commands
        button_frame = tk.Frame(section_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X)
        
        refresh_button = self.create_button(
            button_frame,
            "🔄 Refresh Stats",
            self.refresh_ocr_stats,
            self.success_color
        )
        refresh_button.pack(fill=tk.X, pady=2)
        
        # Stat category buttons
        stats_button = self.create_button(
            button_frame,
            "View Leaderboard (Wins)",
            lambda: self.send_command("stats wins"),
            "#FFD700"
        )
        stats_button.pack(fill=tk.X, pady=2)
        
        kills_button = self.create_button(
            button_frame,
            "View Leaderboard (Kills)",
            lambda: self.send_command("stats kills"),
            "#FF6B6B"
        )
        kills_button.pack(fill=tk.X, pady=2)
        
        rebuild_button = self.create_button(
            button_frame,
            "🔄 Rebuild Database",
            self.rebuild_database,
            self.error_color
        )
        rebuild_button.pack(fill=tk.X, pady=2)
        
        recalc_button = self.create_button(
            button_frame,
            "🔧 Recalculate from Log",
            self.recalculate_stats,
            self.admin_color
        )
        recalc_button.pack(fill=tk.X, pady=2)
        
        # Initial stats load
        self.refresh_ocr_stats()
    
    def refresh_ocr_stats(self):
        """Refresh OCR stats display"""
        try:
            # Get path to stats file
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            stats_file = application_path / "ocr" / "stats_data.json"
            
            if stats_file.exists():
                import json
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                
                # Calculate summary
                total_players = len(stats)
                total_games = sum(p['games_played'] for p in stats.values())
                total_wins = sum(p['wins'] for p in stats.values())
                
                # Get top player by wins
                if stats:
                    top_player = max(stats.items(), key=lambda x: x[1]['wins'])
                    top_name = top_player[1]['display_name']
                    top_wins = top_player[1]['wins']
                else:
                    top_name = "N/A"
                    top_wins = 0
                
                # Format stats text
                stats_text = f"Players Tracked: {total_players}\n"
                stats_text += f"Total Games: {total_games}\n"
                stats_text += f"Total Victories: {total_wins}\n"
                stats_text += f"Top Player: {top_name} ({top_wins} wins)\n"
                stats_text += f"\nUse buttons below to view leaderboards"
                
                # Update display
                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(1.0, stats_text)
                self.stats_text.config(state=tk.DISABLED)
                
                self.log_message("✓ OCR stats refreshed", self.success_color)
            else:
                # No stats yet
                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(1.0, "No stats data yet.\n\nPost victory screenshots to\nthe RecZone channel to start\ntracking player statistics.\n\nOr use 'Scan RecZone Channel'\nto process existing images.")
                self.stats_text.config(state=tk.DISABLED)
                
        except Exception as e:
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, f"Error loading stats:\n{str(e)}")
            self.stats_text.config(state=tk.DISABLED)
            self.log_message(f"✗ Error refreshing stats: {e}", self.error_color)
    
    def log_message(self, message, color=None):
        """Add message to console"""
        self.console.config(state=tk.NORMAL)
        
        if color:
            # Determine tag based on color
            if color == self.success_color:
                tag = "success"
            elif color == self.error_color:
                tag = "error"
            elif color == self.admin_color:
                tag = "admin"
            elif color == self.accent_color:
                tag = "accent"
            else:
                tag = None
            
            self.console.insert(tk.END, message + "\n", tag)
        else:
            self.console.insert(tk.END, message + "\n")
        
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
    
    def update_console(self):
        """Update console with queued messages"""
        try:
            while True:
                message = self.console_queue.get_nowait()
                self.log_message(message)
        except queue.Empty:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_console)
    
    def start_bot(self):
        """Start the Discord bot"""
        if self.bot_running:
            self.log_message("Bot is already running!", self.error_color)
            return
        
        try:
            self.log_message("Starting bot...", self.accent_color)
            
            # Redirect stdout/stderr
            sys.stdout = ConsoleRedirector(self.console, self.console_queue)
            sys.stderr = ConsoleRedirector(self.console, self.console_queue)
            
            # Start bot in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
            self.bot_thread.start()
            
            self.bot_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="● Online", fg=self.success_color)
            
            self.log_message("✓ Bot started successfully!", self.success_color)
        except Exception as e:
            self.log_message(f"✗ Error starting bot: {e}", self.error_color)
    
    def run_bot(self):
        """Run the Discord bot"""
        try:
            # Load configuration
            config = configparser.ConfigParser()
            # Get the directory of the executable (works for both .py and .exe)
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                application_path = Path(sys.executable).parent
            else:
                # Running as script
                application_path = Path(__file__).parent
            
            config_path = application_path / "config.ini"
            config.read(config_path, encoding='utf-8')
            
            BOT_TOKEN = config['Discord']['bot_token']
            COMMAND_PREFIX = config['Commands']['command_prefix']
            
            # Create bot
            intents = discord.Intents.default()
            intents.guilds = True
            intents.members = True
            intents.message_content = True
            
            self.bot = commands.Bot(
                command_prefix=COMMAND_PREFIX,
                intents=intents,
                help_command=None
            )
            
            # Initialize managers from freakrgb package
            rgb_manager = rgb_manager_mod.RGBManager(self.bot)
            banner_manager = banner_manager_mod.BannerManager(self.bot)
            icon_manager = avatar_manager_mod.AvatarManager(self.bot)
            
            # Initialize RecZone manager for OCR
            from ocr.reczone import RecZoneManager
            reczone_manager = RecZoneManager(self.bot, config_path=str(config_path))
            
            # Initialize Music Bot manager
            import musicbot
            musicbot_manager = musicbot.MusicBotManager(self.bot, config_path=str(config_path))
            
            # Initialize Browser manager
            browser_manager = browser.BrowserManager(self.bot, config_path=str(config_path))
            self.browser_manager = browser_manager
            
            # Register commands
            @self.bot.command(name='test', help='Test if bot is responding')
            async def test_command(ctx):
                await ctx.send(f"✅ Bot is working! Prefix is '{COMMAND_PREFIX}'")
                print(f"Test command executed by {ctx.author.name}")
            
            rgb_manager.register_commands(self.bot.tree, self.bot.guilds[0] if self.bot.guilds else None)
            rgb_manager.register_text_commands(self.bot)
            banner_manager.register_commands(self.bot.tree, self.bot.guilds[0] if self.bot.guilds else None)
            icon_manager.register_commands(self.bot.tree, self.bot.guilds[0] if self.bot.guilds else None)
            reczone_manager.register_commands(self.bot)
            browser_manager.register_commands(self.bot)
            
            @self.bot.event
            async def setup_hook():
                await banner_manager.load_existing_images()
                await icon_manager.load_existing_images()
                rgb_manager.start()
                banner_manager.start()
                icon_manager.start()
                print("Bot setup complete")
            
            @self.bot.event
            async def on_ready():
                print(f"Bot logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
                print(f"Connected to {len(self.bot.guilds)} guild(s)")
                print(f"Command prefix: {COMMAND_PREFIX}")
                print("Bot is ready and running...")
                
                # Scan for missed screenshots on startup
                print("\n🔄 Running startup scan for missed screenshots...")
                await reczone_manager.scan_missed_messages(max_messages=100)
                print("✅ Startup scan complete\n")
                
                # Capture music bot basenames
                print("🎵 Capturing music bot basenames...")
                await musicbot_manager.capture_basenames()
                print("✅ Music bot basenames captured\n")
            
            @self.bot.event
            async def on_message(message):
                # Handle music bot messages (before ignoring all bot messages)
                if message.author.bot:
                    musicbot_handled = await musicbot_manager.process_message(message)
                    if musicbot_handled:
                        print("  -> Handled by MusicBot manager")
                        return
                    return
                
                # Handle RecZone screenshot processing
                reczone_handled = await reczone_manager.process_message(message)
                if reczone_handled:
                    print("  -> Handled by RecZone manager")
                
                # Handle browser control (URLs, refresh, close in bot channel)
                browser_handled = await browser_manager.process_message(message)
                if browser_handled:
                    print("  -> Handled by Browser manager")
                
                # Handle banner/icon uploads (in designated channel only)
                designated_channel_id = int(config['Discord']['designated_channel_id'])
                if message.channel.id == designated_channel_id:
                    banner_handled = await banner_manager.handle_message(message)
                    if not banner_handled:
                        await icon_manager.handle_message(message)
                
                await self.bot.process_commands(message)
            
            @self.bot.event
            async def on_message_delete(message):
                """Handle message deletion events"""
                await reczone_manager.handle_message_delete(message)
            
            # Run bot
            self.bot.run(BOT_TOKEN)
            
        except Exception as e:
            print(f"Error running bot: {e}")
            self.bot_running = False
            self._save_crash_dump(e)

    def _save_crash_dump(self, error):
        """Save crash dump to logs folder"""
        import traceback
        import logging
        from datetime import datetime
        
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = logs_dir / f"crash_{timestamp}.log"
        
        with open(crash_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Crash Dump - {datetime.now().isoformat()} ===\n\n")
            f.write(f"Error: {error}\n\n")
            f.write("=== Full Traceback ===\n")
            traceback.print_exc(file=f)
        
        print(f"💾 Crash dump saved to: {crash_file}")
    
    def stop_bot(self):
        """Stop the Discord bot"""
        if not self.bot_running:
            self.log_message("Bot is not running!", self.error_color)
            return
        
        try:
            self.log_message("Stopping bot...", self.accent_color)
            
            if self.bot:
                # Close bot connection
                import asyncio
                asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
            
            self.bot_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="● Offline", fg=self.error_color)
            
            self.log_message("✓ Bot stopped successfully!", self.success_color)
        except Exception as e:
            self.log_message(f"✗ Error stopping bot: {e}", self.error_color)
    
    def send_command(self, command):
        """Execute a command directly through the bot"""
        if not self.bot_running or not self.bot:
            self.log_message("⚠ Bot must be running to send commands!", self.error_color)
            return
        
        try:
            # Get designated channel
            if not self.config:
                self.log_message("⚠ Configuration not loaded!", self.error_color)
                return
            
            channel_id = int(self.config['Discord']['designated_channel_id'])
            prefix = self.config['Commands']['command_prefix']
            
            # Execute command directly
            import asyncio
            
            async def execute_command():
                try:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        self.log_message(f"✗ Channel {channel_id} not found!", self.error_color)
                        return
                    
                    # Create a fake message context to invoke the command
                    # Get the guild from the channel
                    guild = channel.guild
                    
                    # Get bot member in the guild (to use as author)
                    bot_member = guild.me if guild else None
                    
                    if not bot_member:
                        self.log_message(f"✗ Bot not found in guild!", self.error_color)
                        return
                    
                    # Parse the command
                    cmd_parts = command.split()
                    cmd_name = cmd_parts[0]
                    
                    # Get the command object
                    bot_command = self.bot.get_command(cmd_name)
                    
                    if bot_command:
                        # Create a mock context
                        from discord.ext import commands as discord_commands
                        
                        class MockMessage:
                            def __init__(self, channel, author, content, bot):
                                self.channel = channel
                                self.author = author
                                self.content = content
                                self.guild = channel.guild
                                self.id = 0
                                self._state = bot._connection
                                self.attachments = []
                                self.embeds = []
                                self.mention_everyone = False
                                self.mentions = []
                                self.role_mentions = []
                                self.edited_at = None
                                self.pinned = False
                                self.type = discord.MessageType.default
                                
                        # Create mock message with prefix so command can parse args properly
                        full_command = f"{prefix}{command}"
                        mock_message = MockMessage(channel, bot_member, full_command, self.bot)
                        ctx = await self.bot.get_context(mock_message)
                        
                        # Invoke the command using ctx.invoke() to properly handle pre-parsed arguments
                        await ctx.invoke(bot_command)
                        self.log_message(f"✓ Executed: {prefix}{command}", self.success_color)
                    else:
                        self.log_message(f"✗ Command '{cmd_name}' not found!", self.error_color)
                        
                except Exception as e:
                    self.log_message(f"✗ Error executing command: {e}", self.error_color)
                    import traceback
                    traceback.print_exc()
            
            # Schedule the coroutine
            asyncio.run_coroutine_threadsafe(execute_command(), self.bot.loop)
            
        except Exception as e:
            self.log_message(f"✗ Error: {e}", self.error_color)
    
    def send_custom_command(self):
        """Send custom command from input field"""
        command = self.command_input.get().strip()
        if command:
            self.send_command(command)
            self.command_input.delete(0, tk.END)
    
    def browser_fullscreen_toggle(self):
        """Toggle browser between fullscreen and windowed mode"""
        if not self.bot_running or not hasattr(self, 'browser_manager'):
            self.log_message("⚠ Bot must be running to control browser!", self.error_color)
            return
        import asyncio

        async def _toggle():
            success, new_state = await self.browser_manager.toggle_fullscreen()
            if success:
                if new_state == 'fullscreen':
                    self.log_message("🖥️ Browser toggled to fullscreen", self.accent_color)
                else:
                    self.log_message("🔳 Browser toggled to windowed", self.accent_color)
            else:
                self.log_message("✗ No browser to toggle", self.error_color)

        asyncio.run_coroutine_threadsafe(_toggle(), self.bot.loop)

    def browser_minimize(self):
        """Restore browser to windowed mode (show title bar + X button)"""
        if not self.bot_running or not hasattr(self, 'browser_manager'):
            self.log_message("⚠ Bot must be running to control browser!", self.error_color)
            return
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self.browser_manager.minimize_browser(), self.bot.loop
        )
        self.log_message("🔳 Browser restored to windowed mode", self.fg_color)

    def browser_list_bookmarks(self):
        """List all browser bookmarks in the console"""
        if not self.bot_running or not hasattr(self, 'browser_manager'):
            self.log_message("⚠ Bot must be running to list bookmarks!", self.error_color)
            return
        bookmarks = self.browser_manager.bookmarks
        if bookmarks:
            self.log_message("📑 Bookmarks:", self.accent_color)
            for name, url in sorted(bookmarks.items()):
                self.log_message(f"  • {name} → {url}", self.fg_color)
        else:
            self.log_message("📑 No bookmarks saved. Use: URL name", self.fg_color)

    def browser_refresh(self):
        """Refresh the browser page"""
        if not self.bot_running or not hasattr(self, 'browser_manager'):
            self.log_message("⚠ Bot must be running to control browser!", self.error_color)
            return
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self.browser_manager.refresh_browser(), self.bot.loop
        )
        self.log_message("🔄 Browser refresh sent", self.success_color)
    
    def browser_close(self):
        """Close the browser"""
        if not self.bot_running or not hasattr(self, 'browser_manager'):
            self.log_message("⚠ Bot must be running to control browser!", self.error_color)
            return
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self.browser_manager.close_browser(), self.bot.loop
        )
        self.log_message("✖ Browser closed", self.error_color)
    
    def open_banner_folder(self):
        """Open banner folder in file explorer"""
        try:
            if not self.config:
                self.log_message("⚠ Configuration not loaded!", self.error_color)
                return
            
            banner_path = self.config['Storage']['banner_storage_path']
            
            # Get absolute path
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            full_path = application_path / banner_path
            
            # Create folder if it doesn't exist
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Open in file explorer
            if sys.platform == 'win32':
                os.startfile(str(full_path))
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{full_path}"')
            else:  # Linux
                os.system(f'xdg-open "{full_path}"')
            
            self.log_message(f"✓ Opened banner folder: {banner_path}", self.success_color)
        except Exception as e:
            self.log_message(f"✗ Error opening banner folder: {e}", self.error_color)
    
    def open_icon_folder(self):
        """Open icon folder in file explorer"""
        try:
            if not self.config:
                self.log_message("⚠ Configuration not loaded!", self.error_color)
                return
            
            icon_path = self.config['Storage']['icon_storage_path']
            
            # Get absolute path
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            full_path = application_path / icon_path
            
            # Create folder if it doesn't exist
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Open in file explorer
            if sys.platform == 'win32':
                os.startfile(str(full_path))
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{full_path}"')
            else:  # Linux
                os.system(f'xdg-open "{full_path}"')
            
            self.log_message(f"✓ Opened icon folder: {icon_path}", self.success_color)
        except Exception as e:
            self.log_message(f"✗ Error opening icon folder: {e}", self.error_color)
    
    def recalculate_stats(self):
        """Recalculate stats from screenshot log (backup/recovery feature)"""
        # Confirm with user
        response = messagebox.askyesno(
            "Recalculate Stats",
            "This will REBUILD stats_data.json from screenshot_log.json.\n\n"
            "Use this feature as a backup/recovery if stats become corrupted.\n\n"
            "This will CLEAR existing stats and recalculate from the log.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not response:
            self.log_message("Stats recalculation cancelled", self.accent_color)
            return
        
        try:
            # Get path to files
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            # Import and create StatsManager
            from ocr.stats_manager import StatsManager
            stats_manager = StatsManager(data_file=str(application_path / "ocr" / "stats_data.json"))
            
            # Recalculate
            self.log_message("🔧 Recalculating stats from screenshot log...", self.admin_color)
            success, message, player_count = stats_manager.recalculate_all_stats_from_log()
            
            if success:
                self.log_message(f"✓ {message}", self.success_color)
                self.log_message(f"✓ Rebuilt stats for {player_count} players", self.success_color)
                messagebox.showinfo(
                    "Recalculation Complete",
                    f"{message}\n\nRebuilt stats for {player_count} players."
                )
            else:
                self.log_message(f"✗ {message}", self.error_color)
                messagebox.showerror("Recalculation Failed", message)
            
            # Refresh stats display
            self.refresh_ocr_stats()
            
        except Exception as e:
            self.log_message(f"✗ Error recalculating stats: {e}", self.error_color)
            messagebox.showerror("Error", f"Failed to recalculate stats:\n{str(e)}")
    
    def rebuild_database(self):
        """Rebuild the OCR stats database from scratch"""
        # Confirm with user
        response = messagebox.askyesno(
            "Rebuild Database",
            "This will DELETE all existing stats and rebuild from scratch by scanning the RecZone channel.\n\n"
            "This prevents duplicate entries.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not response:
            self.log_message("Database rebuild cancelled", self.accent_color)
            return
        
        try:
            # Get path to stats file
            if getattr(sys, 'frozen', False):
                application_path = Path(sys.executable).parent
            else:
                application_path = Path(__file__).parent
            
            stats_file = application_path / "ocr" / "stats_data.json"
            
            # Delete existing stats file
            if stats_file.exists():
                stats_file.unlink()
                self.log_message("✓ Deleted existing stats database", self.success_color)
            
            # Delete screenshot log as well
            screenshot_log_file = application_path / "ocr" / "screenshot_log.json"
            if screenshot_log_file.exists():
                screenshot_log_file.unlink()
                self.log_message("✓ Deleted screenshot log", self.success_color)
            
            # Update display
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, "Database cleared!\n\nPost new victory screenshots\nto the RecZone channel.\n\nThe bot will automatically\nprocess them and rebuild stats.")
            self.stats_text.config(state=tk.DISABLED)
            
            self.log_message("✓ Database rebuild complete - ready for new screenshots", self.success_color)
            
            # Refresh stats display
            self.refresh_ocr_stats()
            
        except Exception as e:
            self.log_message(f"✗ Error rebuilding database: {e}", self.error_color)
            messagebox.showerror("Error", f"Failed to rebuild database:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
