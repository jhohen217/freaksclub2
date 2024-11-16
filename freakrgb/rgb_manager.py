import discord
from discord.ext import tasks
import asyncio

class RGBManager:
    def __init__(self, client):
        self.client = client
        self.ROLE_ID = 1286862610280742933
        self.color_change_interval = 3600  # seconds
        
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
        if message.content.lower().startswith('rgb!'):
            parts = message.content.split(' ')
            if len(parts) > 1:
                try:
                    seconds = int(parts[1])
                    self.color_change_interval = seconds
                    await message.channel.send(f"Color change interval set to {seconds} seconds.")
                    print(f"Color change interval updated to {seconds} seconds.")
                    return True
                except ValueError:
                    return False  # Not a valid RGB command
            else:
                await message.channel.send("Invalid command. Use `rgb! [seconds]` to set the color change interval.")
                return True
        return False
