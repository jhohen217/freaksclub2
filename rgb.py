"""
RGB Color Cycling Module
Handles automatic color cycling for a Discord role through the RGB spectrum
"""

import discord
from discord.ext import tasks, commands
import asyncio
import random
import configparser
from datetime import datetime, timedelta


class RGBManager:
    """Manages RGB color cycling for a Discord role"""
    
    def __init__(self, client, config_path='config.ini'):
        """
        Initialize the RGB Manager
        
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
        self.role_id = int(self.config['Roles']['rgb_role_id'])
        self.update_interval = int(self.config['Timing']['update_interval'])  # seconds - UNIFIED with banner/icon
        self.rapid_cycles_per_interval = int(self.config['Timing']['rapid_cycles_per_interval'])
        
        # 36-color RGB spectrum - smooth transition through the rainbow
        self.colors = [
            discord.Color.from_rgb(255, 0, 0), discord.Color.from_rgb(255, 42, 0),
            discord.Color.from_rgb(255, 85, 0), discord.Color.from_rgb(255, 128, 0),
            discord.Color.from_rgb(255, 170, 0), discord.Color.from_rgb(255, 212, 0),
            discord.Color.from_rgb(255, 255, 0), discord.Color.from_rgb(212, 255, 0),
            discord.Color.from_rgb(170, 255, 0), discord.Color.from_rgb(127, 255, 0),
            discord.Color.from_rgb(85, 255, 0), discord.Color.from_rgb(42, 255, 0),
            discord.Color.from_rgb(0, 255, 0), discord.Color.from_rgb(0, 255, 43),
            discord.Color.from_rgb(0, 255, 85), discord.Color.from_rgb(0, 255, 128),
            discord.Color.from_rgb(0, 255, 170), discord.Color.from_rgb(0, 255, 213),
            discord.Color.from_rgb(0, 255, 255), discord.Color.from_rgb(0, 212, 255),
            discord.Color.from_rgb(0, 170, 255), discord.Color.from_rgb(0, 127, 255),
            discord.Color.from_rgb(0, 85, 255), discord.Color.from_rgb(0, 42, 255),
            discord.Color.from_rgb(0, 0, 255), discord.Color.from_rgb(43, 0, 255),
            discord.Color.from_rgb(85, 0, 255), discord.Color.from_rgb(128, 0, 255),
            discord.Color.from_rgb(170, 0, 255), discord.Color.from_rgb(213, 0, 255),
            discord.Color.from_rgb(255, 0, 255), discord.Color.from_rgb(255, 0, 212),
            discord.Color.from_rgb(255, 0, 170), discord.Color.from_rgb(255, 0, 127),
            discord.Color.from_rgb(255, 0, 85), discord.Color.from_rgb(255, 0, 42)
        ]
        
        # Track current position in color array - load from config for persistence
        try:
            self.current_color_index = int(self.config['State']['last_color_index'])
            # Ensure it's within valid range
            if not (0 <= self.current_color_index < len(self.colors)):
                self.current_color_index = 0
        except (KeyError, ValueError):
            self.current_color_index = 0
        
        # Load last color change timestamp and calculate correct position
        # STALENESS_THRESHOLD: If state is older than 2 hours, consider it stale
        STALENESS_THRESHOLD_HOURS = 2
        STALENESS_THRESHOLD_SECONDS = STALENESS_THRESHOLD_HOURS * 3600
        
        try:
            last_change_str = self.config['State']['last_color_change_time']
            last_change_time = datetime.fromisoformat(last_change_str)
            
            # Calculate how much time has passed since last color change
            now = datetime.now()
            time_passed = (now - last_change_time).total_seconds()
            
            # Check if state is stale (older than threshold)
            if time_passed > STALENESS_THRESHOLD_SECONDS:
                print(f"⚠️ RGB state is STALE (last change {time_passed/3600:.1f} hours ago)")
                print(f"   Resetting to current time to prevent stuck colors")
                self.time_until_next_change = self.update_interval
                self.current_color_index = 0  # Start fresh at red
                self._save_state_immediate()
            else:
                # Calculate how many color changes should have happened
                cycles_passed = int(time_passed // self.update_interval)
                
                if cycles_passed > 0:
                    # Update color index based on missed cycles
                    self.current_color_index = (self.current_color_index + cycles_passed) % len(self.colors)
                    print(f"Resuming color cycle: {cycles_passed} cycles passed during downtime")
                    print(f"Current color index adjusted to: {self.current_color_index}")
                    
                    # Calculate time until next color change
                    time_into_current_cycle = time_passed % self.update_interval
                    self.time_until_next_change = self.update_interval - time_into_current_cycle
                    print(f"Next color change in {self.time_until_next_change:.1f} seconds")
                else:
                    # Still within the same cycle
                    self.time_until_next_change = self.update_interval - time_passed
                    print(f"Continuing current cycle, next change in {self.time_until_next_change:.1f} seconds")
                
        except (KeyError, ValueError) as e:
            # No timestamp found or invalid, start fresh
            print(f"No valid timestamp found, starting fresh cycle")
            self.time_until_next_change = self.update_interval
            self.current_color_index = 0  # Start at red
            self._save_state_immediate()
    
    def _save_state_immediate(self):
        """Save current state to config file immediately with error handling"""
        try:
            self.config['State']['last_color_index'] = str(self.current_color_index)
            self.config['State']['last_color_change_time'] = datetime.now().isoformat()
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            print(f"✅ RGB state saved: index={self.current_color_index}")
        except Exception as e:
            print(f"❌ ERROR: Failed to save RGB state to config: {e}")
    
    def _force_reset_state(self):
        """Force reset the RGB state to prevent stuck colors"""
        print("🔄 Force resetting RGB state...")
        self.current_color_index = 0  # Start at red
        self.time_until_next_change = self.update_interval
        self._save_state_immediate()
        print("✅ RGB state force reset complete")
    
    def start(self):
        """Start the RGB color cycling background task"""
        self.cycle_role_color.start()
        print("RGB color cycling started")
    
    def stop(self):
        """Stop the RGB color cycling background task"""
        self.cycle_role_color.cancel()
        print("RGB color cycling stopped")
    
    async def rapid_cycle(self, role, return_color):
        """
        Perform rapid color cycling through all colors
        
        Args:
            role: Discord role to modify
            return_color: Color to return to after cycling
        """
        # Duration for rapid cycle in seconds
        total_duration = 8  # seconds
        num_colors = len(self.colors)
        time_per_color = total_duration / num_colors  # seconds per color
        
        # Flash through all colors
        for color in self.colors:
            await role.edit(color=color)
            await asyncio.sleep(time_per_color)  # seconds
        
        # Return to the current color
        await role.edit(color=return_color)
    
    @tasks.loop()
    async def cycle_role_color(self):
        """
        Main color cycling loop
        Cycles through colors at the configured interval with random rapid cycles
        """
        try:
            # Wait for bot to be ready on first iteration
            await self.client.wait_until_ready()
            
            # Get the guild (server)
            guild = self.client.get_guild(self.server_id)
            if not guild:
                print(f"Error: Could not find guild with ID {self.server_id}")
                print(f"Available guilds: {[g.name for g in self.client.guilds]}")
                return
            
            # Get the role
            role = guild.get_role(self.role_id)
            if not role:
                print(f"Error: Could not find role with ID {self.role_id}")
                return
            
            # Get current color
            current_color = self.colors[self.current_color_index]
            
            # Use calculated time on first iteration, then use normal interval
            wait_time = getattr(self, 'time_until_next_change', self.update_interval)
            if hasattr(self, 'time_until_next_change'):
                delattr(self, 'time_until_next_change')  # Use only once
            
            # Heartbeat log
            print(f"🎨 RGB heartbeat: Current color index {self.current_color_index}, waiting {wait_time}s until next change")
            
            # Generate random times for rapid cycles during the interval
            # Distribute them evenly across the interval
            if self.rapid_cycles_per_interval > 0:
                # Calculate time slots for rapid cycles (in seconds)
                interval_segment = wait_time / (self.rapid_cycles_per_interval + 1)  # seconds
                rapid_cycle_times = []
                
                for i in range(self.rapid_cycles_per_interval):
                    # Random time within each segment (in seconds)
                    min_time = interval_segment * i + (interval_segment * 0.1)  # seconds
                    max_time = interval_segment * (i + 1) - (interval_segment * 0.1)  # seconds
                    rapid_cycle_times.append(random.uniform(min_time, max_time))  # seconds
                
                rapid_cycle_times.sort()  # Sort chronologically
                
                # Execute rapid cycles at the calculated times
                last_time = 0  # seconds
                for cycle_time in rapid_cycle_times:
                    sleep_duration = cycle_time - last_time  # seconds
                    await asyncio.sleep(sleep_duration)  # seconds
                    try:
                        await self.rapid_cycle(role, current_color)
                    except discord.HTTPException as e:
                        if e.status == 429:
                            print(f"⚠️ Rate limited during rapid cycle, skipping...")
                        else:
                            print(f"⚠️ HTTP error during rapid cycle: {e}")
                    last_time = cycle_time  # seconds
                
                # Wait for remaining time until color change
                remaining_time = wait_time - last_time  # seconds
                await asyncio.sleep(remaining_time)  # seconds
            else:
                # No rapid cycles, just wait for the full interval
                await asyncio.sleep(wait_time)  # seconds
            
            # Move to next color
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)
            next_color = self.colors[self.current_color_index]
            
            # Perform one final rapid cycle that ends on the NEXT color (the one we're changing to)
            # This creates a smooth transition effect
            try:
                await self.rapid_cycle(role, next_color)
            except discord.HTTPException as e:
                if e.status == 429:
                    print(f"⚠️ Rate limited during final rapid cycle, applying color directly...")
                    await role.edit(color=next_color)
                else:
                    print(f"⚠️ HTTP error during final cycle: {e}")
                    await role.edit(color=next_color)  # Try direct edit anyway
            
            # Save current color index and timestamp to config for persistence
            self._save_state_immediate()
            
            # Color is already set by rapid_cycle, just log it
            print(f"Role '{role.name}' color changed to RGB({next_color.r}, {next_color.g}, {next_color.b}) [Index: {self.current_color_index}]")
            
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"❌ RGB Cycle: Rate limited (429). Will retry on next cycle.")
            else:
                print(f"❌ RGB Cycle HTTP error: {e}")
        except Exception as e:
            print(f"❌ RGB Cycle error: {e}")
            import traceback
            traceback.print_exc()
    
    def register_commands(self, bot):
        """Register RGB-related text commands"""
        
        # Load admin role ID for permission checks
        admin_role_id = int(self.config['Roles']['admin_role_id'])
        
        @bot.command(name='timer', help='Set unified update interval in seconds (Admin role only)')
        async def timer_command(ctx, seconds: int):
            """Set unified interval for RGB, banner, and icon"""
            # Check if user has admin role
            has_admin_role = any(role.id == admin_role_id for role in ctx.author.roles)
            if not has_admin_role:
                await ctx.send("Only admins can modify settings!")
                return
            
            if seconds <= 0:
                await ctx.send("Interval must be a positive number.")
                return
            
            # Update the interval
            self.update_interval = seconds
            self.config['Timing']['update_interval'] = str(seconds)
            
            # Save to config file
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            
            await ctx.send(
                f"✅ Update interval set to **{seconds} seconds** ({round(seconds/60, 2)} minutes).\n"
                f"This affects RGB colors, banners, and icons."
            )
            print(f"Update interval changed to {seconds} seconds by {ctx.author.name}")
        
        @bot.command(name='rgbreset', help='Force reset RGB color cycle state (Admin only)')
        async def rgb_reset(ctx):
            """Force reset the RGB color cycle state to prevent stuck colors"""
            # Check if user has admin role
            has_admin_role = any(role.id == admin_role_id for role in ctx.author.roles)
            if not has_admin_role:
                await ctx.send("Only admins can reset RGB state!")
                return
            
            self._force_reset_state()
            await ctx.send("✅ RGB color state has been force reset to red. The cycle will resume from there.")
        
        @bot.command(name='rgbstatus', help='Check current RGB color cycle status (Admin only)')
        async def rgb_status(ctx):
            """Check the current RGB color cycle status"""
            # Check if user has admin role
            has_admin_role = any(role.id == admin_role_id for role in ctx.author.roles)
            if not has_admin_role:
                await ctx.send("Only admins can check RGB status!")
                return
            
            # Get current color info
            current_color = self.colors[self.current_color_index]
            
            # Check last change time
            try:
                last_change_str = self.config['State']['last_color_change_time']
                last_change_time = datetime.fromisoformat(last_change_str)
                now = datetime.now()
                time_passed = (now - last_change_time).total_seconds()
                hours = int(time_passed // 3600)
                minutes = int((time_passed % 3600) // 60)
                
                status_msg = (
                    f"🎨 **RGB Color Cycle Status:**\n"
                    f"• Current color index: `{self.current_color_index}`\n"
                    f"• Current color: `RGB({current_color.r}, {current_color.g}, {current_color.b})`\n"
                    f"• Last change: `{hours}h {minutes}m` ago\n"
                    f"• Update interval: `{self.update_interval}` seconds"
                )
            except (KeyError, ValueError):
                status_msg = (
                    f"🎨 **RGB Color Cycle Status:**\n"
                    f"• Current color index: `{self.current_color_index}`\n"
                    f"• Current color: `RGB({current_color.r}, {current_color.g}, {current_color.b})`\n"
                    f"• Last change: `Unknown`\n"
                    f"• Update interval: `{self.update_interval}` seconds"
                )
            
            await ctx.send(status_msg)
        
        @bot.command(name='rgb', help='Change role color (usage: !rgb OR !rgb <r> <g> <b>)')
        async def change_color(ctx, r: int = None, g: int = None, b: int = None):
            """Manually change the RGB role color with animation"""
            # Check if user has admin role
            has_admin_role = any(role.id == admin_role_id for role in ctx.author.roles)
            if not has_admin_role:
                await ctx.send("Only admins can change colors!")
                return
            
            # Get the guild and role
            guild = self.client.get_guild(self.server_id)
            if not guild:
                await ctx.send("Error: Could not find server!")
                return
            
            role = guild.get_role(self.role_id)
            if not role:
                await ctx.send("Error: Could not find role!")
                return
            
            # Determine target color
            if r is None and g is None and b is None:
                # Random color from palette
                target_color = random.choice(self.colors)
            elif r is not None and g is not None and b is not None:
                # Validate RGB values
                if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                    await ctx.send("❌ RGB values must be between 0 and 255!")
                    return
                target_color = discord.Color.from_rgb(r, g, b)
            else:
                await ctx.send("❌ Usage: `rgb` for random color OR `rgb <r> <g> <b>` for specific color")
                return
            
            # Perform rapid cycle through all colors
            rapid_duration = 4  # seconds for rapid cycle
            time_per_color = rapid_duration / len(self.colors)  # seconds per color
            
            for color in self.colors:
                await role.edit(color=color)
                await asyncio.sleep(time_per_color)
            
            # Smooth gradient transition to target color
            gradient_duration = 2  # seconds for smooth transition
            steps = 20  # number of gradient steps
            time_per_step = gradient_duration / steps  # seconds per step
            
            # Get current color (last color from rapid cycle)
            current = self.colors[-1]
            current_r, current_g, current_b = current.r, current.g, current.b
            target_r, target_g, target_b = target_color.r, target_color.g, target_color.b
            
            # Calculate step increments
            step_r = (target_r - current_r) / steps
            step_g = (target_g - current_g) / steps
            step_b = (target_b - current_b) / steps
            
            # Smooth transition
            for step in range(steps):
                intermediate_r = int(current_r + (step_r * step))
                intermediate_g = int(current_g + (step_g * step))
                intermediate_b = int(current_b + (step_b * step))
                
                # Ensure values stay in valid range
                intermediate_r = max(0, min(255, intermediate_r))
                intermediate_g = max(0, min(255, intermediate_g))
                intermediate_b = max(0, min(255, intermediate_b))
                
                intermediate_color = discord.Color.from_rgb(intermediate_r, intermediate_g, intermediate_b)
                await role.edit(color=intermediate_color)
                await asyncio.sleep(time_per_step)
            
            # Final color set (ensure exact target)
            await role.edit(color=target_color)
            
            # Find the closest color index in our palette and update config
            # This ensures the automatic cycling continues from the right position
            min_distance = float('inf')
            closest_index = self.current_color_index
            
            for i, color in enumerate(self.colors):
                # Calculate color distance using RGB difference
                distance = abs(color.r - target_color.r) + abs(color.g - target_color.g) + abs(color.b - target_color.b)
                if distance < min_distance:
                    min_distance = distance
                    closest_index = i
            
            # Update the current color index
            self.current_color_index = closest_index
            
            # Save to config for persistence (including timestamp to maintain schedule)
            self.config['State']['last_color_index'] = str(self.current_color_index)
            self.config['State']['last_color_change_time'] = datetime.now().isoformat()
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
            
            await ctx.send(f"🎨 Role color changed to RGB({target_color.r}, {target_color.g}, {target_color.b})")
            print(f"Role color manually changed to RGB({target_color.r}, {target_color.g}, {target_color.b}) by {ctx.author.name}")
            print(f"Updated color index to {self.current_color_index} with timestamp")
