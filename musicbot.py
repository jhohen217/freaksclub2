"""
Music Bot Manager Module
Handles automatic nickname changing for music bots based on currently playing songs
"""

import discord
from discord.ext import commands
import asyncio
import configparser
import re
from datetime import datetime


class MusicBotManager:
    """Manages music bot nickname changes based on currently playing songs"""
    
    def __init__(self, client, config_path='config.ini'):
        """
        Initialize the Music Bot Manager
        
        Args:
            client: Discord client instance
            config_path: Path to configuration file
        """
        self.client = client
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # Load configuration
        self.server_id = int(self.config['Discord']['server_id'])
        
        # Get music bot channel ID from MusicBots section
        if 'MusicBots' in self.config and 'music_bot_channel_id' in self.config['MusicBots']:
            self.music_bot_channel_id = int(self.config['MusicBots']['music_bot_channel_id'])
        else:
            self.music_bot_channel_id = None
            print("Warning: music_bot_channel_id not set in config!")
        
        # Parse music bot user IDs from config
        self.music_bot_ids = []
        if 'MusicBots' in self.config and 'bot_user_ids' in self.config['MusicBots']:
            bot_ids_str = self.config['MusicBots']['bot_user_ids']
            self.music_bot_ids = [int(id.strip()) for id in bot_ids_str.split(',') if id.strip()]
        
        # Store basenames for each bot (matched by index to bot_user_ids)
        self.basenames = {}  # {bot_id: basename}
        self.basename_list = []  # List matching indices of music_bot_ids
        
        # Track active timers for each bot
        self.active_timers = {}  # {bot_id: asyncio.Task}
        
        # Timer duration in seconds (8 minutes)
        self.reset_duration = 8 * 60  # 480 seconds
        
        print(f"MusicBotManager initialized with {len(self.music_bot_ids)} music bot(s)")
    
    async def capture_basenames(self):
        """Capture and save current nicknames as basenames on startup"""
        await self.client.wait_until_ready()
        
        guild = self.client.get_guild(self.server_id)
        if not guild:
            print(f"Error: Could not find guild with ID {self.server_id}")
            return
        
        if 'MusicBots' not in self.config:
            self.config['MusicBots'] = {}
        
        # Check if basenames already exist in config
        if 'bot_basenames' in self.config['MusicBots'] and self.config['MusicBots']['bot_basenames'].strip():
            # Load existing basenames from config (SKIP capturing new ones)
            print("🎵 Basenames already exist in config - using saved values (not capturing)")
            basename_str = self.config['MusicBots']['bot_basenames']
            self.basename_list = [name.strip() for name in basename_str.split(',')]
            
            # Map basenames to bot IDs by index
            for i, bot_id in enumerate(self.music_bot_ids):
                if i < len(self.basename_list) and self.basename_list[i]:
                    self.basenames[bot_id] = self.basename_list[i]
                    print(f"  ✓ Using saved basename for bot {bot_id}: '{self.basename_list[i]}'")
                else:
                    print(f"  ⚠ Warning: No basename found for bot ID {bot_id} at index {i}")
        else:
            # Capture basenames from current nicknames
            self.basename_list = []
            for bot_id in self.music_bot_ids:
                member = guild.get_member(bot_id)
                if member:
                    # Use nickname if set, otherwise use username
                    basename = member.nick if member.nick else member.name
                    self.basenames[bot_id] = basename
                    self.basename_list.append(basename)
                    print(f"Captured basename for bot {bot_id}: {basename}")
                else:
                    print(f"Warning: Could not find member for bot ID {bot_id}")
                    self.basename_list.append("")  # Empty placeholder
            
            # Save basenames as comma-separated list
            self.config['MusicBots']['bot_basenames'] = ', '.join(self.basename_list)
            
            # Save to config file with UTF-8 encoding to support emoji
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        
        # Reset all tracked bots to their basenames on startup (in case of crash)
        print("🔄 Resetting all music bots to basenames on startup...")
        for bot_id, basename in self.basenames.items():
            if basename:
                member = guild.get_member(bot_id)
                if member and member.nick != basename:
                    try:
                        await member.edit(nick=basename)
                        print(f"  ✓ Reset bot {bot_id} to basename: '{basename}'")
                    except discord.Forbidden:
                        print(f"  ⚠ No permission to reset bot {bot_id}")
                    except discord.HTTPException as e:
                        print(f"  ⚠ Error resetting bot {bot_id}: {e}")
                else:
                    print(f"  ✓ Bot {bot_id} already has correct name: '{basename}'")
    
    def parse_song_info(self, message_content):
        """
        Parse song information from music bot message
        
        Args:
            message_content: The message content to parse
            
        Returns:
            str: Formatted song name or None if not a valid song message
        """
        # Pattern 1: Markdown link with bold text (freakswim.FM format)
        # Example: "[**St. Catherine St.** **by** **Deltron 3030**](https://spotify...)"
        if "started playing" in message_content.lower() and "[**" in message_content:
            pattern_markdown = r'\[\*\*(.+?)\*\*\s+\*\*by\*\*\s+\*\*(.+?)\*\*\]'
            match = re.search(pattern_markdown, message_content, re.IGNORECASE)
            
            if match:
                song_title = match.group(1).strip()
                artist = match.group(2).strip()
                # Remove text in parentheses to save characters
                song_title = re.sub(r'\([^)]*\)', '', song_title).strip()
                artist = re.sub(r'\([^)]*\)', '', artist).strip()
                return f"{song_title} - {artist}"
        
        # Pattern 2: "Started playing [song] by [artist]" (Rythm bot format)
        # Example: "🎵 Started playing Little Lies by Fleetwood Mac"
        pattern_plain = r'Started playing\s+(.+?)\s+by\s+(.+?)(?:\s|$)'
        match = re.search(pattern_plain, message_content, re.IGNORECASE)
        
        if match:
            song_title = match.group(1).strip()
            artist = match.group(2).strip()
            
            # Remove text in parentheses to save characters
            song_title = re.sub(r'\([^)]*\)', '', song_title).strip()
            artist = re.sub(r'\([^)]*\)', '', artist).strip()
            
            # Clean up any emoji or extra characters at the end
            artist = re.sub(r'[^\w\s\-&.,\'].*$', '', artist).strip()
            
            return f"{song_title} - {artist}"
        
        # Pattern 3: "Now Playing" followed by "Title - Artist" (Pancake bot format)
        # Example: "Now Playing\nToxicity - System of A Down"
        if "now playing" in message_content.lower():
            # Look for pattern: text - text (song - artist)
            pattern_pancake = r'Now Playing[^\n]*\n+([^-\[\n]+)\s*-\s*([^\[\n]+)'
            match = re.search(pattern_pancake, message_content, re.IGNORECASE | re.DOTALL)
            
            if match:
                song_title = match.group(1).strip()
                artist = match.group(2).strip()
                # Remove text in parentheses to save characters
                song_title = re.sub(r'\([^)]*\)', '', song_title).strip()
                artist = re.sub(r'\([^)]*\)', '', artist).strip()
                return f"{song_title} - {artist}"
        
        return None
    
    async def reset_to_basename(self, bot_id):
        """
        Reset a bot's nickname to its basename after timer expires
        
        Args:
            bot_id: The user ID of the bot to reset
        """
        await asyncio.sleep(self.reset_duration)
        
        guild = self.client.get_guild(self.server_id)
        if not guild:
            return
        
        member = guild.get_member(bot_id)
        if not member:
            return
        
        basename = self.basenames.get(bot_id)
        if not basename:
            return
        
        try:
            await member.edit(nick=basename)
            print(f"Reset bot {bot_id} nickname to basename: {basename}")
        except discord.Forbidden:
            print(f"Error: No permission to change nickname for bot {bot_id}")
        except discord.HTTPException as e:
            print(f"Error resetting nickname for bot {bot_id}: {e}")
        finally:
            # Remove from active timers
            if bot_id in self.active_timers:
                del self.active_timers[bot_id]
    
    async def change_bot_nickname(self, bot_id, song_name):
        """
        Change a music bot's nickname to the currently playing song
        
        Args:
            bot_id: The user ID of the bot to rename
            song_name: The formatted song name
        """
        guild = self.client.get_guild(self.server_id)
        if not guild:
            print(f"Error: Could not find guild with ID {self.server_id}")
            return
        
        member = guild.get_member(bot_id)
        if not member:
            print(f"Error: Could not find member for bot ID {bot_id}")
            return
        
        # Cancel existing timer if any
        if bot_id in self.active_timers:
            self.active_timers[bot_id].cancel()
            print(f"Cancelled existing timer for bot {bot_id}")
        
        # Change nickname to song name
        try:
            await member.edit(nick=song_name)
            print(f"Changed bot {bot_id} nickname to: {song_name}")
        except discord.Forbidden:
            print(f"Error: No permission to change nickname for bot {bot_id}")
            return
        except discord.HTTPException as e:
            print(f"Error changing nickname for bot {bot_id}: {e}")
            return
        
        # Start new timer to reset to basename
        timer_task = asyncio.create_task(self.reset_to_basename(bot_id))
        self.active_timers[bot_id] = timer_task
        print(f"Started 8-minute reset timer for bot {bot_id}")
    
    async def process_message(self, message):
        """
        Process incoming messages for music bot activity
        
        Args:
            message: Discord message object
            
        Returns:
            bool: True if message was handled, False otherwise
        """
        print(f"[MusicBot] Checking message from bot {message.author.id}")
        print(f"[MusicBot] Tracked bot IDs: {self.music_bot_ids}")
        print(f"[MusicBot] Message channel: {message.channel.id}, Expected: {self.music_bot_channel_id}")
        
        # Check if message is from a tracked music bot
        if message.author.id not in self.music_bot_ids:
            print(f"[MusicBot] Bot {message.author.id} not in tracked list")
            return False
        
        print(f"[MusicBot] Bot ID matches! Checking channel...")
        
        # Check if message is in music bot channel (if configured)
        if self.music_bot_channel_id and message.channel.id != self.music_bot_channel_id:
            print(f"[MusicBot] Channel mismatch: {message.channel.id} != {self.music_bot_channel_id}")
            return False
        
        print(f"[MusicBot] Channel matches! Checking if bot message...")
        
        # Check if message is a bot message
        if not message.author.bot:
            print(f"[MusicBot] Not a bot message")
            return False
        
        # Try parsing from message content first
        print(f"[MusicBot] Parsing message content: '{message.content}'")
        song_name = self.parse_song_info(message.content)
        
        # If no song found in content, check embeds (Pancake bot uses embeds)
        if not song_name and message.embeds:
            print(f"[MusicBot] No song in content, checking {len(message.embeds)} embed(s)...")
            for embed in message.embeds:
                # Try to parse from embed title
                if embed.title:
                    print(f"[MusicBot] Checking embed title: '{embed.title}'")
                    song_name = self.parse_song_info(embed.title)
                    if song_name:
                        break
                
                # Try to parse from embed description
                if not song_name and embed.description:
                    print(f"[MusicBot] Checking embed description: '{embed.description}'")
                    song_name = self.parse_song_info(embed.description)
                    if song_name:
                        break
                
                # Try to parse from embed fields (freakswim.FM uses fields)
                if not song_name and embed.fields:
                    print(f"[MusicBot] Checking {len(embed.fields)} embed field(s)...")
                    for field in embed.fields:
                        field_text = f"{field.name}\n{field.value}"
                        print(f"[MusicBot] Checking field: '{field_text}'")
                        song_name = self.parse_song_info(field_text)
                        if song_name:
                            break
                    if song_name:
                        break
        
        if song_name:
            # Add music note emoji to the song name
            formatted_name = f"🎵{song_name}"
            
            # Discord has 32 character limit for nicknames
            if len(formatted_name) > 32:
                # Truncate to 32 chars (no ellipsis to save characters)
                formatted_name = formatted_name[:32]
                print(f"[MusicBot] ⚠ Name too long, truncated to: {formatted_name}")
            
            print(f"[MusicBot] ✓ Detected song from bot {message.author.id}: {formatted_name}")
            await self.change_bot_nickname(message.author.id, formatted_name)
            return True
        else:
            print(f"[MusicBot] Failed to parse song from message")
        
        return False
    
    def register_commands(self, bot):
        """Register music bot related commands (if needed in future)"""
        pass
