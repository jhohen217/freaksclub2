"""
Banner Management Module
Handles automatic banner cycling and banner management for Discord servers
"""

import discord
from discord.ext import tasks, commands
import asyncio
import os
import configparser
import aiohttp
from pathlib import Path
from datetime import datetime


class BannerManager:
    """Manages server banner cycling and storage"""
    
    def __init__(self, client, config_path='config.ini'):
        """
        Initialize the Banner Manager
        
        Args:
            client: Discord client instance
            config_path: Path to configuration file
        """
        self.client = client
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # Load configuration
        self.server_id = int(self.config['Discord']['server_id'])
        self.update_interval = int(self.config['Timing']['update_interval'])  # seconds - UNIFIED with RGB/icon
        self.banner_storage_path = self.config['Storage']['banner_storage_path']
        self.designated_channel_id = int(self.config['Discord']['designated_channel_id'])
        self.admin_role_id = int(self.config['Roles']['admin_role_id'])
        self.booster_role_id = int(self.config['Roles']['booster_role_id'])
        
        # Create banner storage directory if it doesn't exist (Windows-compatible)
        Path(self.banner_storage_path).mkdir(parents=True, exist_ok=True)
        
        # List to store banner file paths
        self.banner_images = []
        self.current_banner_index = 0
        self.config_path = config_path
    
    async def load_existing_images(self):
        """Load existing banner images from storage directory"""
        self.banner_images = []
        
        if os.path.exists(self.banner_storage_path):
            for filename in os.listdir(self.banner_storage_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    # Use os.path.join for Windows compatibility
                    self.banner_images.append(os.path.join(self.banner_storage_path, filename))
        
        # Sort to maintain consistent ordering
        self.banner_images.sort()
        
        print(f"Loaded {len(self.banner_images)} banner images from storage")
        
        # Load last banner change timestamp and calculate correct position
        if self.banner_images:
            try:
                self.current_banner_index = int(self.config['State']['last_banner_index'])
                # Ensure it's within valid range
                if not (0 <= self.current_banner_index < len(self.banner_images)):
                    self.current_banner_index = 0
            except (KeyError, ValueError):
                self.current_banner_index = 0
            
            try:
                last_change_str = self.config['State']['last_banner_change_time']
                last_change_time = datetime.fromisoformat(last_change_str)
                
                # Calculate how much time has passed since last banner change
                now = datetime.now()
                time_passed = (now - last_change_time).total_seconds()
                
                # Calculate how many banner changes should have happened
                cycles_passed = int(time_passed // self.update_interval)
                
                if cycles_passed > 0:
                    # Update banner index based on missed cycles
                    self.current_banner_index = (self.current_banner_index + cycles_passed) % len(self.banner_images)
                    print(f"Resuming banner cycle: {cycles_passed} cycles passed during downtime")
                    print(f"Current banner index adjusted to: {self.current_banner_index}")
                    
                    # Calculate time until next banner change
                    time_into_current_cycle = time_passed % self.update_interval
                    self.time_until_next_change = self.update_interval - time_into_current_cycle
                    print(f"Next banner change in {self.time_until_next_change:.1f} seconds")
                else:
                    # Still within the same cycle
                    self.time_until_next_change = self.update_interval - time_passed
                    print(f"Continuing current cycle, next banner change in {self.time_until_next_change:.1f} seconds")
                    
            except (KeyError, ValueError) as e:
                # No timestamp found or invalid, start fresh
                print(f"No valid banner timestamp found, starting fresh cycle")
                self.time_until_next_change = self.update_interval
                # Save initial timestamp
                if 'State' not in self.config:
                    self.config['State'] = {}
                self.config['State']['last_banner_change_time'] = datetime.now().isoformat()
                try:
                    with open(self.config_path, 'w', encoding='utf-8') as configfile:
                        self.config.write(configfile)
                except Exception:
                    pass
    
    def _get_next_banner_number(self):
        """Get the next available banner number by checking existing files"""
        max_num = 0
        if os.path.exists(self.banner_storage_path):
            for filename in os.listdir(self.banner_storage_path):
                if filename.startswith('banner_') and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    try:
                        # Extract number from filename like "banner_3.png"
                        num_str = filename.split('_')[1].split('.')[0]
                        num = int(num_str)
                        max_num = max(max_num, num)
                    except (IndexError, ValueError):
                        continue
        return max_num + 1
    
    def start(self):
        """Start the banner cycling background task"""
        if self.banner_images:
            self.cycle_banners.start()
            print("Banner cycling started")
        else:
            print("No banners found. Banner cycling not started.")
    
    def stop(self):
        """Stop the banner cycling background task"""
        self.cycle_banners.cancel()
        print("Banner cycling stopped")
    
    @tasks.loop()
    async def cycle_banners(self):
        """
        Main banner cycling loop
        Cycles through banner images at the configured interval
        """
        if not self.banner_images:
            return
        
        # Wait for bot to be ready on first iteration
        await self.client.wait_until_ready()
        
        # Get the guild (server)
        guild = self.client.get_guild(self.server_id)
        if not guild:
            print(f"Error: Could not find guild with ID {self.server_id}")
            return
        
        # Use calculated time on first iteration, then use normal interval
        wait_time = getattr(self, 'time_until_next_change', self.update_interval)
        if hasattr(self, 'time_until_next_change'):
            delattr(self, 'time_until_next_change')  # Use only once
        
        # Wait before changing banner (synchronized with RGB schedule)
        await asyncio.sleep(wait_time)
        
        # Get current banner path
        banner_path = self.banner_images[self.current_banner_index]
        
        try:
            # Read and set the banner
            with open(banner_path, 'rb') as image_file:
                banner_data = image_file.read()
                await guild.edit(banner=banner_data)
                print(f"Banner changed to: {os.path.basename(banner_path)}")
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"Rate limited while changing banner. Retrying later...")
            else:
                print(f"Error changing banner: {e}")
        except Exception as e:
            print(f"Error reading banner file: {e}")
        
        # Move to next banner
        self.current_banner_index = (self.current_banner_index + 1) % len(self.banner_images)
        
        # Save current banner index and timestamp to config for persistence
        if 'State' not in self.config:
            self.config['State'] = {}
        self.config['State']['last_banner_index'] = str(self.current_banner_index)
        self.config['State']['last_banner_change_time'] = datetime.now().isoformat()
        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
    
    async def handle_message(self, message):
        """
        Handle messages for banner uploads
        
        Args:
            message: Discord message object
            
        Returns:
            bool: True if message was handled, False otherwise
        """
        # Check if message is in designated channel
        if message.channel.id != self.designated_channel_id:
            return False
        
        # Check if bot is mentioned and message contains "banner"
        if self.client.user not in message.mentions:
            return False
        
        if "banner" not in message.content.lower():
            return False
        
        # Check if user has booster role
        has_booster_role = any(role.id == self.booster_role_id for role in message.author.roles)
        if not has_booster_role:
            await message.channel.send("Only boosters can add banners!")
            return True
        
        # Check if message has attachments
        if not message.attachments:
            await message.channel.send("Please attach an image to add as a banner!")
            return True
        
        # Download and save the image
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                try:
                    # Generate filename with next available number
                    next_num = self._get_next_banner_number()
                    filename = f"banner_{next_num}{os.path.splitext(attachment.filename)[1]}"
                    filepath = os.path.join(self.banner_storage_path, filename)
                    
                    # Download image
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                with open(filepath, 'wb') as f:
                                    f.write(await resp.read())
                                
                                # Add to banner list
                                self.banner_images.append(filepath)
                                
                                await message.channel.send(f"Banner added successfully! Total banners: {len(self.banner_images)}")
                                
                                # Start cycling if not already started
                                if not self.cycle_banners.is_running():
                                    self.cycle_banners.start()
                                
                                print(f"New banner added: {filename}")
                            else:
                                await message.channel.send(f"Failed to download image: HTTP {resp.status}")
                except Exception as e:
                    await message.channel.send(f"Error saving banner: {str(e)}")
                    print(f"Error saving banner: {e}")
        
        return True
    
    def register_commands(self, bot):
        """Register banner-related text commands"""
        
        @bot.command(name='banners', help='List all saved banner images')
        async def list_banners(ctx):
            """List all banner images"""
            # Reload files from directory to get latest
            await self.load_existing_images()
            
            if not self.banner_images:
                await ctx.send("No banners found!")
                return
            
            banner_list = "\n".join([
                f"{i+1}. {os.path.basename(path)}"
                for i, path in enumerate(self.banner_images)
            ])
            
            embed = discord.Embed(
                title=f"Saved Banners ({len(self.banner_images)})",
                description=banner_list,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        
        @bot.command(name='banner', help='Set, display, or delete a banner (usage: !banner <file> [show/del])')
        async def banner_command(ctx, identifier: str, action: str = None):
            """Set, show, or delete a specific banner"""
            # Reload to get latest files
            await self.load_existing_images()
            
            if not self.banner_images:
                await ctx.send("No banners found!")
                return
            
            try:
                # Try to parse as index
                if identifier.isdigit():
                    index = int(identifier) - 1
                    if 0 <= index < len(self.banner_images):
                        banner_path = self.banner_images[index]
                    else:
                        await ctx.send("Invalid banner number!")
                        return
                else:
                    # Try to find by filename
                    banner_path = None
                    for path in self.banner_images:
                        if identifier in os.path.basename(path):
                            banner_path = path
                            break
                    
                    if not banner_path:
                        await ctx.send("Banner not found!")
                        return
                
                # Check action
                if action and action.lower() == 'del':
                    # Delete action
                    has_admin_role = any(role.id == self.admin_role_id for role in ctx.author.roles)
                    
                    if not has_admin_role:
                        await ctx.send("Only admins can delete banners!")
                        return
                    
                    # Delete the file
                    filename = os.path.basename(banner_path)
                    os.remove(banner_path)
                    self.banner_images.remove(banner_path)
                    
                    # Adjust current index if needed
                    if self.current_banner_index >= len(self.banner_images):
                        self.current_banner_index = 0
                    
                    await ctx.send(f"Banner '{filename}' deleted successfully! Remaining banners: {len(self.banner_images)}")
                    print(f"Banner deleted: {filename}")
                    
                    # Stop cycling if no icons left
                    if not self.banner_images and self.cycle_banners.is_running():
                        self.cycle_banners.cancel()
                        
                elif action and action.lower() == 'show':
                    # Show action - display the banner image
                    await ctx.send(
                        content=f"Banner: {os.path.basename(banner_path)}",
                        file=discord.File(banner_path)
                    )
                else:
                    # Default action - SET the server banner
                    guild = ctx.guild
                    if not guild:
                        await ctx.send("This command can only be used in a server!")
                        return
                    
                    try:
                        with open(banner_path, 'rb') as image_file:
                            banner_data = image_file.read()
                            await guild.edit(banner=banner_data)
                            await ctx.send(f"Server banner set to: {os.path.basename(banner_path)}")
                            print(f"Banner manually set to: {os.path.basename(banner_path)}")
                    except discord.HTTPException as e:
                        await ctx.send(f"Error setting banner: {e}")
                    except Exception as e:
                        await ctx.send(f"Error reading banner file: {e}")
            except Exception as e:
                await ctx.send(f"Error with banner: {str(e)}")
        
        @bot.command(name='deletebanner', help='Delete a specific banner image (DEPRECATED - use banner <file> del)')
        async def delete_banner(ctx, identifier: str):
            """Delete a specific banner"""
            # Check permissions
            has_admin_role = any(role.id == self.admin_role_id for role in ctx.author.roles)
            
            if not has_admin_role:
                await ctx.send("Only admins can delete banners!")
                return
            
            if not self.banner_images:
                await ctx.send("No banners found!")
                return
            
            try:
                # Try to parse as index
                if identifier.isdigit():
                    index = int(identifier) - 1
                    if 0 <= index < len(self.banner_images):
                        banner_path = self.banner_images[index]
                    else:
                        await ctx.send("Invalid banner number!")
                        return
                else:
                    # Try to find by filename
                    banner_path = None
                    for path in self.banner_images:
                        if identifier in os.path.basename(path):
                            banner_path = path
                            break
                    
                    if not banner_path:
                        await ctx.send("Banner not found!")
                        return
                
                # Delete the file
                filename = os.path.basename(banner_path)
                os.remove(banner_path)
                self.banner_images.remove(banner_path)
                
                # Adjust current index if needed
                if self.current_banner_index >= len(self.banner_images):
                    self.current_banner_index = 0
                
                await ctx.send(f"Banner '{filename}' deleted successfully! Remaining banners: {len(self.banner_images)}")
                print(f"Banner deleted: {filename}")
                
                # Stop cycling if no banners left
                if not self.banner_images and self.cycle_banners.is_running():
                    self.cycle_banners.cancel()
            except Exception as e:
                await ctx.send(f"Error deleting banner: {str(e)}")
        
        @bot.command(name='help', help='Show all available commands')
        async def help_command(ctx):
            """Show help information"""
            prefix = self.config['Commands']['command_prefix']
            help_text = f"""
**Banner Commands:**
`{prefix}banners` - List all saved banner images
`{prefix}banner <file>` - Set server banner to specific banner
`{prefix}banner <file> show` - Display a specific banner
`{prefix}banner <file> del` - Delete a banner (Admin only)

**Icon Commands:**
`{prefix}icons` - List all saved icon images
`{prefix}icon <file>` - Set server icon to specific icon
`{prefix}icon <file> show` - Display a specific icon
`{prefix}icon <file> del` - Delete an icon (Admin only)

**RGB Commands:**
`{prefix}timer <seconds>` - Set unified update interval (Admin only)
`{prefix}rgb [r] [g] [b]` - Change role color with animation (Admin only)

**Stats Commands:**
`{prefix}stats` - Display player stats leaderboard (sorted by score)

**Adding Banners/Icons (Boosters only):**
To add a banner: `@🌭freakswim.server banner` (with image attached)
To add an icon: `@🌭freakswim.server icon` (with image attached)
*Must be posted in the designated channel with an image attachment*
"""
            embed = discord.Embed(
                title="FreakSwim Server Commands",
                description=help_text,
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
