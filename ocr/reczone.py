"""
RecZone manager for monitoring victory screenshots and tracking player stats
"""

import discord
from discord.ext import commands
import configparser
import aiohttp
from ocr.parser import OCRParser
from ocr.stats_manager import StatsManager


class RecZoneManager:
    """Manage RecZone screenshot monitoring and stats tracking"""
    
    def __init__(self, bot, config_path='config.ini'):
        """
        Initialize the RecZone manager
        
        Args:
            bot: Discord bot instance
            config_path: Path to config file
        """
        self.bot = bot
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # Get channel IDs from config
        try:
            self.read_channel_id = int(self.config['RecZone']['reczone_read_channel_id'])
            self.write_channel_id = int(self.config['RecZone']['reczone_write_channel_id'])
            self.bot_channel_id = int(self.config['Discord']['designated_channel_id'])
        except (KeyError, ValueError) as e:
            print(f"Error reading RecZone config: {e}")
            self.read_channel_id = None
            self.write_channel_id = None
            self.bot_channel_id = None
        
        # Initialize OCR and stats
        self.parser = OCRParser()
        self.stats_manager = StatsManager()
        
        # Track rebuilding state
        self.is_rebuilding = False  # Flag to track if we're rebuilding database
        
        print(f"RecZone manager initialized with EasyOCR support")
        print(f"Channels - Read: {self.read_channel_id}, Write: {self.write_channel_id}")
    
    async def process_message(self, message):
        """
        Process a message from the RecZone channel
        Check for image attachments and parse them
        
        Args:
            message: Discord message object
            
        Returns:
            bool: True if message was processed, False otherwise
        """
        # Only process messages in the read channel
        if message.channel.id != self.read_channel_id:
            return False
        
        print(f"📸 RecZone: Message detected in read channel from {message.author.name}")
        
        # Check for image attachments
        image_attachments = [
            att for att in message.attachments
            if att.content_type and att.content_type.startswith('image/')
        ]
        
        if not image_attachments:
            print(f"⚠ RecZone: No image attachments found in message")
            return False
        
        print(f"✓ RecZone: Found {len(image_attachments)} image(s) to process")
        
        # Process each image
        for attachment in image_attachments:
            await self._process_screenshot(attachment, message)
        
        return True
    
    async def _process_screenshot(self, attachment, original_message):
        """
        Download and process a screenshot attachment
        
        Args:
            attachment: Discord attachment object
            original_message: Original message containing the attachment
        """
        try:
            # Check if user typed "override" with their screenshot
            message_content = original_message.content.lower().strip()
            override_mode = "override" in message_content
            
            if override_mode:
                print(f"🔓 RecZone: OVERRIDE mode detected in message")
            
            # Check if already processed (prevent duplicates)
            if self.stats_manager.is_screenshot_processed(original_message.id, attachment.id):
                print(f"⚠ RecZone: Screenshot already processed: {attachment.filename} (skipping)")
                return
            
            # Clear bot's existing reactions before processing
            try:
                # Get bot's user ID
                bot_user = self.bot.user
                # Remove only the bot's reactions
                for reaction in original_message.reactions:
                    if reaction.me:  # If bot reacted
                        await original_message.remove_reaction(reaction.emoji, bot_user)
                print(f"  → Cleared bot's existing reactions")
            except Exception as e:
                print(f"⚠ Could not clear bot reactions: {e}")
            
            # Download image
            print(f"⬇ RecZone: Downloading screenshot: {attachment.filename}")
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        print(f"✗ RecZone: Failed to download image (HTTP {resp.status})")
                        await self._send_error(f"Failed to download image: {attachment.filename}")
                        return
                    
                    image_bytes = await resp.read()
            
            print(f"✓ RecZone: Download complete ({len(image_bytes)} bytes)")
            
            # Parse screenshot
            print(f"🔍 RecZone: Starting OCR parsing on {attachment.filename}...")
            parsed_data = await self.parser.parse_screenshot(image_bytes, override=override_mode)
            
            if not parsed_data:
                print(f"✗ RecZone: OCR parsing failed - no data extracted")
                await self._send_error(f"Failed to parse screenshot: {attachment.filename}", original_message)
                return
            
            # Display parsed results
            player_names = [p['name'] for p in parsed_data['players']]
            print(f"✓ RecZone: OCR parsing successful!")
            print(f"  → Found {len(parsed_data['players'])} player(s): {', '.join(player_names)}")
            print(f"  → Match time: {parsed_data['match_time']:.2f} minutes")
            
            # Update stats
            print(f"💾 RecZone: Updating player stats in database...")
            self.stats_manager.update_player_stats(parsed_data)
            
            # Log the screenshot
            self.stats_manager.log_screenshot(
                original_message.id,
                attachment.id,
                attachment.filename,
                parsed_data
            )
            
            print(f"✓ RecZone: Stats saved to database successfully")
            
            # Send confirmation
            await self._send_confirmation(parsed_data, attachment.filename, original_message)
            
        except Exception as e:
            print(f"✗ RecZone: Error processing screenshot: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error(f"Error processing {attachment.filename}: {str(e)}")
    
    async def _send_confirmation(self, parsed_data, filename, original_message):
        """Log confirmation message to console and add success emoji"""
        try:
            # Format player info for console
            player_names = [p['name'] for p in parsed_data['players']]
            match_time = parsed_data['match_time']
            total_kills = sum(p.get('kills', 0) for p in parsed_data['players'])
            
            # Log to console
            print(f"✓ RecZone: Victory confirmed - {filename}")
            print(f"  → Players: {', '.join(player_names) if player_names else 'None detected'}")
            if match_time > 0:
                minutes = int(match_time)
                seconds = int((match_time - minutes) * 60)
                print(f"  → Match Time: {minutes}:{seconds:02d}")
            print(f"  → Team Kills: {total_kills}")
            
            # Add green check emoji to the message
            try:
                await original_message.add_reaction('✅')
                print(f"  → Added ✅ reaction to message")
            except Exception as e:
                print(f"  ⚠ Could not add reaction: {e}")
            
            # Auto-post leaderboard after each screenshot (only if not rebuilding)
            if not self.is_rebuilding:
                print("🏆 RecZone: Auto-posting leaderboard...")
                await self._auto_post_leaderboard()
            
        except Exception as e:
            print(f"✗ RecZone: Error in confirmation: {e}")
    
    async def _auto_post_leaderboard(self):
        """Automatically post leaderboard sorted by score to READ channel - deletes all previous bot messages first"""
        try:
            # Auto-post to READ channel (RecZone), not write channel
            channel = self.bot.get_channel(self.read_channel_id)
            if not channel:
                print(f"Could not find read channel: {self.read_channel_id}")
                return
            
            # Delete ALL previous messages from the bot in this channel
            # Use bot ID directly for more reliable matching after restarts
            bot_id = self.bot.user.id if self.bot.user else None
            deleted_count = 0
            async for message in channel.history(limit=100):
                if message.author.id == bot_id or message.author.id == 1287512008966541312:
                    try:
                        await message.delete()
                        deleted_count += 1
                    except Exception as e:
                        print(f"  ⚠ Could not delete message {message.id}: {e}")
            
            if deleted_count > 0:
                print(f"  → Deleted {deleted_count} previous bot message(s) from RecZone")
            
            # Get leaderboard sorted by score
            embed_data = self.stats_manager.format_leaderboard_embed('score', min_games=2)
            
            embed = discord.Embed(
                description=embed_data.get('description', ''),
                color=embed_data['color']
            )
            
            # Add fields if present
            if 'fields' in embed_data:
                for field in embed_data['fields']:
                    embed.add_field(
                        name=field['name'],
                        value=field['value'],
                        inline=field.get('inline', False)
                    )
            
            # Post new leaderboard to READ channel (RecZone)
            new_message = await channel.send(embed=embed)
            print(f"Leaderboard posted to RecZone successfully (Message ID: {new_message.id})")
            
        except Exception as e:
            print(f"Error posting leaderboard: {e}")
    
    async def _send_error(self, error_message, original_message=None):
        """Log error message to terminal and add failure emoji"""
        try:
            print(f"✗ RecZone: {error_message}")
            
            # Add red X emoji to the message if available
            if original_message:
                try:
                    await original_message.add_reaction('❌')
                    print(f"  → Added ❌ reaction to message")
                except Exception as e:
                    print(f"  ⚠ Could not add reaction: {e}")
            
        except Exception as e:
            print(f"✗ RecZone: Error logging error message: {e}")
    
    async def scan_channel_history(self, limit=500, is_rebuild=False):
        """
        Scan channel history for existing screenshots and process them
        
        Args:
            limit: Number of messages to scan (default 500)
            is_rebuild: Whether this is a database rebuild (prevents auto-leaderboard)
        """
        try:
            # Auto-detect if this is a rebuild (no existing stats)
            if not is_rebuild and len(self.stats_manager.stats) == 0:
                is_rebuild = True
                print("Auto-detected database rebuild (no existing stats)")
            
            # Set rebuilding flag
            self.is_rebuilding = is_rebuild
            
            channel = self.bot.get_channel(self.read_channel_id)
            if not channel:
                print(f"Could not find read channel: {self.read_channel_id}")
                return
            
            print(f"Scanning last {limit} messages in channel {self.read_channel_id}")
            
            processed_count = 0
            async for message in channel.history(limit=limit):
                # Check for images
                image_attachments = [
                    att for att in message.attachments
                    if att.content_type and att.content_type.startswith('image/')
                ]
                
                for attachment in image_attachments:
                    await self._process_screenshot(attachment, message)
                    processed_count += 1
            
            print(f"Finished scanning. Processed {processed_count} images.")
            
            # Send summary
            if processed_count > 0:
                write_channel = self.bot.get_channel(self.write_channel_id)
                if write_channel:
                    await write_channel.send(
                        f"✅ Scanned channel history and processed {processed_count} screenshot(s)."
                    )
            
            # Reset rebuilding flag
            self.is_rebuilding = False
        
        except Exception as e:
            print(f"Error scanning channel history: {e}")
            import traceback
            traceback.print_exc()
            self.is_rebuilding = False
    
    async def scan_missed_messages(self, max_messages=100):
        """
        Scan backward through message history until hitting a processed message.
        This catches any screenshots missed during bot downtime.
        
        Args:
            max_messages: Maximum number of messages to scan (safety limit)
        """
        try:
            channel = self.bot.get_channel(self.read_channel_id)
            if not channel:
                print(f"Could not find read channel: {self.read_channel_id}")
                return
            
            print(f"🔍 Scanning for missed screenshots in channel {self.read_channel_id}...")
            
            # Set rebuilding flag to prevent individual leaderboard posts during scan
            self.is_rebuilding = True
            
            processed_count = 0
            scanned_count = 0
            found_processed_message = False
            
            # Scan backward through history
            async for message in channel.history(limit=max_messages, oldest_first=False):
                scanned_count += 1
                
                # Check for image attachments
                image_attachments = [
                    att for att in message.attachments
                    if att.content_type and att.content_type.startswith('image/')
                ]
                
                if not image_attachments:
                    continue
                
                # Check each attachment
                for attachment in image_attachments:
                    # Check if already processed
                    if self.stats_manager.is_screenshot_processed(message.id, attachment.id):
                        print(f"✓ Found already-processed screenshot: {attachment.filename} (stopping scan)")
                        found_processed_message = True
                        break
                    else:
                        # Found unprocessed screenshot - process it
                        print(f"📸 Found missed screenshot: {attachment.filename}")
                        await self._process_screenshot(attachment, message)
                        processed_count += 1
                
                # Stop scanning if we found a processed message
                if found_processed_message:
                    break
            
            # Log results
            if processed_count > 0:
                print(f"✅ Startup scan complete: Processed {processed_count} missed screenshot(s) from {scanned_count} messages")
                # Post leaderboard after batch processing
                print("🏆 RecZone: Posting leaderboard after startup scan...")
                await self._auto_post_leaderboard()
            else:
                print(f"✓ Startup scan complete: No missed screenshots found (scanned {scanned_count} messages)")
            
            # Reset rebuilding flag
            self.is_rebuilding = False
        
        except Exception as e:
            print(f"Error scanning for missed messages: {e}")
            import traceback
            traceback.print_exc()
            # Reset rebuilding flag even on error
            self.is_rebuilding = False
    
    async def check_for_deleted_screenshots(self, limit=10):
        """
        Check recent messages for deleted screenshots and remove their stats
        
        Args:
            limit: Number of recent messages to check (default 10)
        """
        try:
            channel = self.bot.get_channel(self.read_channel_id)
            if not channel:
                print(f"Could not find read channel: {self.read_channel_id}")
                return
            
            # Get current message IDs with attachments
            current_screenshots = set()
            async for message in channel.history(limit=limit):
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        key = f"{message.id}_{attachment.id}"
                        current_screenshots.add(key)
            
            # Check logged screenshots against current ones
            deleted_count = 0
            for log_key, log_entry in list(self.stats_manager.screenshot_log.items()):
                # Only check screenshots that would be in the recent messages
                if log_key not in current_screenshots:
                    # Check if the message exists at all
                    message_id = int(log_entry['message_id'])
                    try:
                        message = await channel.fetch_message(message_id)
                        # Message exists but attachment is missing
                        # (could be edited or attachment deleted)
                        has_matching_attachment = any(
                            att.id == int(log_entry['attachment_id'])
                            for att in message.attachments
                        )
                        if not has_matching_attachment:
                            print(f"Screenshot deleted: {log_entry['filename']}")
                            self.stats_manager.remove_screenshot_stats(log_entry)
                            del self.stats_manager.screenshot_log[log_key]
                            deleted_count += 1
                    except discord.NotFound:
                        # Message was deleted entirely
                        print(f"Message with screenshot deleted: {log_entry['filename']}")
                        self.stats_manager.remove_screenshot_stats(log_entry)
                        del self.stats_manager.screenshot_log[log_key]
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error checking message {message_id}: {e}")
            
            if deleted_count > 0:
                self.stats_manager.save_screenshot_log()
                print(f"Removed stats for {deleted_count} deleted screenshot(s)")
                
        except Exception as e:
            print(f"Error checking for deleted screenshots: {e}")
            import traceback
            traceback.print_exc()
    
    def register_commands(self, bot):
        """Register stats commands with the bot"""
        
        @bot.command(name='refresh', help='Force refresh of the RecZone leaderboard')
        async def refresh_command(ctx):
            """Force a refresh of the leaderboard in RecZone read channel"""
            # Allow command from EITHER bot channel OR RecZone read channel
            if ctx.channel.id not in [self.bot_channel_id, self.read_channel_id]:
                return  # Silently ignore commands from other channels
            
            try:
                # Delete the command message if it's in RecZone (keep clean)
                if ctx.channel.id == self.read_channel_id:
                    try:
                        await ctx.message.delete()
                        print(f"  → Deleted .refresh command message from RecZone")
                    except Exception as e:
                        print(f"  ⚠ Could not delete command message: {e}")
                
                # Reload screenshot log and rebuild stats from it
                print("🔄 Reloading screenshot log and rebuilding stats...")
                self.stats_manager.load_screenshot_log()
                success, message, stats_count = self.stats_manager.recalculate_all_stats_from_log()
                
                if success:
                    print(f"  ✓ {message}")
                    print(f"  → {stats_count} total players in stats")
                else:
                    print(f"  ✗ {message}")
                
                # Use existing auto-post leaderboard which handles cleanup
                print("🔄 Manual refresh requested - posting leaderboard...")
                await self._auto_post_leaderboard()
                
                # If command was from bot channel, send confirmation there
                if ctx.channel.id == self.bot_channel_id:
                    await ctx.send("✅ Leaderboard refreshed in RecZone!")
                    
            except Exception as e:
                error_msg = f"❌ Error refreshing leaderboard: {e}"
                print(error_msg)
                if ctx.channel.id == self.bot_channel_id:
                    await ctx.send(error_msg)
        
        @bot.command(name='stats', help='Display player stats leaderboard (sorted by score)')
        async def stats_command(ctx):
            """Display stats leaderboard sorted by score"""
            # Only allow commands from the designated bot channel
            if ctx.channel.id != self.bot_channel_id:
                return  # Silently ignore commands from other channels
            
            # Delete ALL previous messages from the bot in the BOT channel
            bot_channel = self.bot.get_channel(self.bot_channel_id)
            if not bot_channel:
                await ctx.send("❌ Could not find bot channel!")
                return
                
            # Use bot ID directly for more reliable matching after restarts
            bot_id = self.bot.user.id if self.bot.user else None
            deleted_count = 0
            async for message in bot_channel.history(limit=100):
                if message.author.id == bot_id or message.author.id == 1287512008966541312:
                    try:
                        await message.delete()
                        deleted_count += 1
                    except Exception as e:
                        print(f"  ⚠ Could not delete message {message.id}: {e}")
            
            if deleted_count > 0:
                print(f"  → Deleted {deleted_count} previous bot message(s) from bot channel")
            
            # Get leaderboard sorted by score (min 2 games like auto-post)
            embed_data = self.stats_manager.format_leaderboard_embed('score', min_games=2)
            
            embed = discord.Embed(
                description=embed_data.get('description', ''),
                color=embed_data['color']
            )
            
            # Add fields if present
            if 'fields' in embed_data:
                for field in embed_data['fields']:
                    embed.add_field(
                        name=field['name'],
                        value=field['value'],
                        inline=field.get('inline', False)
                    )
            
            # Post to the BOT channel
            await bot_channel.send(embed=embed)
        
        print("RecZone commands registered")
    
    async def handle_message_delete(self, message):
        """
        Handle message deletion event - automatically remove stats if it was a screenshot
        
        Args:
            message: Deleted message object
        """
        try:
            # Only process deletions from RecZone read channel
            if message.channel.id != self.read_channel_id:
                return
            
            # Check our screenshot log for this message ID
            # (message.attachments is often empty in deletion events)
            deleted_screenshots = []
            for log_key, log_entry in list(self.stats_manager.screenshot_log.items()):
                if str(message.id) == log_entry['message_id']:
                    deleted_screenshots.append((log_key, log_entry))
            
            if not deleted_screenshots:
                return
            
            # Process each deleted screenshot
            for log_key, log_entry in deleted_screenshots:
                print(f"Screenshot deleted: {log_entry['filename']} - removing stats")
                
                # Remove stats
                self.stats_manager.remove_screenshot_stats(log_entry)
                
                # Remove from log
                del self.stats_manager.screenshot_log[log_key]
                
                # Get player names for notification
                player_names = []
                for player in log_entry.get('players', []):
                    if isinstance(player, dict):
                        player_names.append(player.get('name', 'Unknown'))
                    else:
                        player_names.append(str(player))
                
                # Notify in write channel
                write_channel = self.bot.get_channel(self.write_channel_id)
                if write_channel and player_names:
                    embed = discord.Embed(
                        title="📉 Screenshot Deleted",
                        description=f"Removed stats for deleted screenshot: `{log_entry['filename']}`",
                        color=0xFF9900
                    )
                    embed.add_field(
                        name="Players Affected",
                        value=", ".join(player_names),
                        inline=False
                    )
                    await write_channel.send(embed=embed)
            
            # Save log changes
            self.stats_manager.save_screenshot_log()
            
            # Refresh leaderboard after all deletions processed
            if deleted_screenshots:
                print("🏆 RecZone: Refreshing leaderboard after deletion...")
                await self._auto_post_leaderboard()
                        
        except Exception as e:
            print(f"Error handling message deletion: {e}")
            import traceback
            traceback.print_exc()
