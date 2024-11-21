import discord
from discord.ext import tasks
import asyncio
import random
from .config_manager import ConfigManager

class RGBManager:
    def __init__(self, client):
        self.client = client
        self.config = ConfigManager()
        self.ROLE_ID = int(self.config.get('rgb_role_id'))  # Convert to int for comparison
        self.BOOSTER_ROLE_ID = int(self.config.get('booster_role_id'))  # Booster role for permission checks
        self.color_change_interval = self.config.get('color_change_interval')

        # Color configuration
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

        # Load the current color index from config, default to 0 if not set
        self.current_color_index = self.config.get('current_color_index', 0)
        if not isinstance(self.current_color_index, int) or not (0 <= self.current_color_index < len(self.colors)):
            self.current_color_index = 0

    def start(self):
        """Start the RGB cycling"""
        self.cycle_role_color.start()

    def stop(self):
        """Stop the RGB cycling"""
        self.cycle_role_color.cancel()

    async def rapid_cycle(self, role, current_color):
        """Perform rapid color cycling and return to current color"""
        total_duration = 8  # seconds
        num_colors = len(self.colors)
        time_per_color = total_duration / num_colors

        for color in self.colors:
            await role.edit(color=color)
            await asyncio.sleep(time_per_color)
        
        # Return to current color
        await role.edit(color=current_color)

    @tasks.loop()
    async def cycle_role_color(self):
        """Cycle through colors for the specified role with random rapid cycling effects"""
        if not self.client.guilds:
            return

        guild = self.client.guilds[0]
        role = guild.get_role(self.ROLE_ID)

        if role:
            # Get current color
            current_color = self.colors[self.current_color_index]

            # Calculate two random times during the interval for rapid cycles
            # Use 20% to 80% of the interval to ensure spacing
            min_time = self.color_change_interval * 0.2
            max_time = self.color_change_interval * 0.8
            
            # Generate two random times ensuring they're not too close together
            time1 = random.uniform(min_time, max_time * 0.4)  # First third
            time2 = random.uniform(max_time * 0.6, max_time)  # Last third

            # Wait until first random time
            await asyncio.sleep(time1)
            await self.rapid_cycle(role, current_color)

            # Wait until second random time
            await asyncio.sleep(time2 - time1)
            await self.rapid_cycle(role, current_color)

            # Wait for remaining time
            await asyncio.sleep(self.color_change_interval - time2)

            # Perform original rapid cycle before color change
            await self.rapid_cycle(role, current_color)

            # Update the current color index and save it to config
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)
            self.config.set('current_color_index', self.current_color_index)
            print(f"Role: {role.name} | Changed to color: R{current_color.r}, G{current_color.g}, B{current_color.b}")

    def register_commands(self, tree, guild):
        """Register RGB-related slash commands"""

        @tree.command(name="rgbhelp", description="Show RGB-related commands", guild=guild)
        async def rgb_help(interaction: discord.Interaction):
            help_text = """
**RGB Role Color Commands**
`/rgbhelp` - Show this help message
`/setrgbinterval` - Set RGB color change interval (Boosters only)
"""
            await interaction.response.send_message(help_text, ephemeral=True)

        @tree.command(name="setrgbinterval", description="Set RGB color change interval (Boosters only)", guild=guild)
        async def set_rgb_interval(interaction: discord.Interaction, seconds: float):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can modify RGB settings!", ephemeral=True)
                return

            if seconds <= 0:
                await interaction.response.send_message("Interval must be a positive number.", ephemeral=True)
                return

            self.color_change_interval = seconds
            self.config.set('color_change_interval', seconds)
            await interaction.response.send_message(f"RGB color change interval set to {seconds} seconds.", ephemeral=True)
