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

    async def handle_command(self, message):
        """Handle RGB-related commands"""
        if not message.content.startswith('/'):
            return False

        command = message.content.lower().split()[0]

        # Help command is always allowed
        if command == '/rgbhelp':
            help_text = """
**RGB Role Color Commands**
`/rgbhelp` - Show this help message
`/setrgbinterval <seconds>` - Set RGB color change interval (Boosters only)

**Note**: Only server boosters can modify the RGB color change interval.
"""
            await message.channel.send(help_text)
            return True

        # Check if the user is a booster for other commands
        if not any(role.id == self.BOOSTER_ROLE_ID for role in message.author.roles):
            await message.channel.send(
                f"{message.author.mention} Only server boosters can modify RGB settings!",
                delete_after=10
            )
            return True

        # Set RGB interval command
        if command == '/setrgbinterval':
            try:
                parts = message.content.split()
                if len(parts) < 2:
                    await message.channel.send("Please provide an interval in seconds. Usage: `/setrgbinterval <seconds>`")
                    return True

                seconds = float(parts[1])
                if seconds <= 0:
                    await message.channel.send("Interval must be a positive number.")
                    return True

                self.color_change_interval = seconds
                self.config.set('color_change_interval', seconds)
                await message.channel.send(f"RGB color change interval set to {seconds} seconds.")
                return True
            except ValueError:
                await message.channel.send("Invalid interval. Please provide a valid number of seconds.")
                return True

        return False
