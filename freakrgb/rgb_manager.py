import discord
from discord.ext import tasks
import asyncio
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

    @tasks.loop()
    async def cycle_role_color(self):
        """Cycle through colors for the specified role with rapid cycling effect"""
        if not self.client.guilds:
            return

        guild = self.client.guilds[0]
        role = guild.get_role(self.ROLE_ID)

        if role:
            # Perform rapid color cycling over 8 seconds
            total_duration = 8  # seconds
            num_colors = len(self.colors)
            time_per_color = total_duration / num_colors

            for color in self.colors:
                await role.edit(color=color)
                await asyncio.sleep(time_per_color)

            # After rapid cycling, set to the next main color
            new_color = self.colors[self.current_color_index]
            await role.edit(color=new_color)
            print(f"Role: {role.name} | Changed to color: R{new_color.r}, G{new_color.g}, B{new_color.b}")

            # Update the current color index and save it to config
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)
            self.config.set('current_color_index', self.current_color_index)

        # Wait for the specified interval before next cycle
        await asyncio.sleep(self.color_change_interval)

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
