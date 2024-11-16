import discord
from discord.ext import tasks
import asyncio
from .rgb_manager import RGBManager
from .avatar_manager import AvatarManager
from .config_manager import ConfigManager

class FreakBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        
        # Load configuration
        self.config = ConfigManager()
        
        # Initialize managers
        self.rgb_manager = RGBManager(self)
        self.avatar_manager = AvatarManager(self)
        
        # Server configuration
        self.DEFAULT_SERVER_NAME = self.config.get('default_server_name', "🌭freaksTest")
        self.server_name = self.DEFAULT_SERVER_NAME

    async def setup_hook(self):
        """Set up background tasks"""
        self.rgb_manager.start()
        self.avatar_manager.start()

    async def on_ready(self):
        """Handle bot ready event"""
        print("Bot is connected and ready.")
        
        # Load existing images for avatar cycling
        await self.avatar_manager.load_existing_images()
        
        if self.guilds:
            guild = self.guilds[0]
            
            # Send startup message
            for channel in guild.text_channels:
                if 'radio' in channel.name.lower():
                    embed = discord.Embed(
                        title=self.server_name,
                        description="freakrgb started!",
                        color=discord.Color.green()
                    )
                    await channel.send(embed=embed)
                    print(f"Sent startup message to channel: {channel.name}")

    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author.bot:
            return
            
        # Try handling with RGB manager first
        if await self.rgb_manager.handle_command(message):
            return
            
        # Then try handling with Avatar manager
        if await self.avatar_manager.handle_message(message):
            return
            
        # Handle server name command
        if message.content.lower().startswith('rgb!'):
            parts = message.content.split(' ')
            if len(parts) > 1:
                new_name = ' '.join(parts[1:])
                self.server_name = new_name
                await self.guilds[0].edit(name=new_name)
                self.config.update('default_server_name', new_name)
                await message.channel.send(f"Server name updated to: {new_name}")
