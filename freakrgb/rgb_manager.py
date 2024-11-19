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
        self.current_color_index = 0

    def start(self):
        """Start the RGB cycling"""
        self.cycle_role_color.start()

    def stop(self):
        """Stop the RGB cycling"""
        self.cycle_role_color.cancel()

    @tasks.loop(seconds=1)
    async def cycle_role_color(self):
        """Cycle through colors for the specified role"""
        if not self.client.guilds:
            return
            
        guild = self.client.guilds[0]
        role = guild.get_role(self.ROLE_ID)
        
        if role:
            new_color = self.colors[self.current_color_index]
            await role.edit(color=new_color)
            print(f"Role: {role.name} | Changed to color: R{new_color.r}, G{new_color.g}, B{new_color.b}")
            
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)
            
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
