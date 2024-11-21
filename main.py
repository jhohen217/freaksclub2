import discord
from discord import app_commands
import os
import sys
import traceback
from dotenv import load_dotenv
import freakrgb.rgb_manager as rgb_manager
import freakrgb.banner_manager as banner_manager
import freakrgb.config_manager as config_manager

# Load environment variables from .env file in the same directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

class FreakBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        
        # Command tree for slash commands
        self.tree = app_commands.CommandTree(self)
        
        # Flag to track if commands have been registered
        self.commands_registered = False
        
        # Load configuration
        try:
            self.config = config_manager.ConfigManager()
            
            # Verify required config values exist
            required_configs = [
                'rgb_role_id',
                'booster_role_id',
                'color_change_interval',
                'banner_change_interval',
                'banner_storage_path',
                'designated_channel_id',
                'admin_id'
            ]
            
            missing_configs = []
            for config in required_configs:
                if self.config.get(config) is None:
                    missing_configs.append(config)
            
            if missing_configs:
                print("Error: Missing required configuration values:")
                for config in missing_configs:
                    print(f"- {config}")
                print("\nPlease check your config.json file and ensure all required values are set.")
                self.handle_error()
            
            # Initialize managers
            self.rgb_manager = rgb_manager.RGBManager(self)
            self.banner_manager = banner_manager.BannerManager(self)
            self.VERSION = "1.9.0"
            
        except Exception as e:
            print(f"Error during initialization: {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            self.handle_error()

    def handle_error(self):
        """Interactive error handling"""
        while True:
            print("\nType 'exit' to close the application")
            user_input = input(">>> ").strip().lower()
            if user_input == 'exit':
                sys.exit(1)
            else:
                print("Invalid command. Type 'exit' to close.")

    async def setup_hook(self):
        """Set up background tasks"""
        self.rgb_manager.start()
        self.banner_manager.start()

    async def register_commands(self):
        """Register commands once"""
        if self.commands_registered:
            return
            
        if self.guilds:
            guild = self.guilds[0]
            
            try:
                # Clear existing commands
                self.tree.clear_commands(guild=guild)
                print("Cleared existing commands")
                
                # Register commands from managers
                self.rgb_manager.register_commands(self.tree, guild)
                self.banner_manager.register_commands(self.tree, guild)
                
                # Sync commands with the guild
                print(f"Syncing commands for guild: {guild.name}")
                await self.tree.sync(guild=guild)
                print("Command sync complete!")
                
                # Set flag to prevent re-registration
                self.commands_registered = True
                
            except Exception as e:
                print(f"Error registering commands: {str(e)}")
                print("\nFull error details:")
                traceback.print_exc()

    async def on_ready(self):
        """Handle bot ready event"""
        print("Bot is connected and ready.")
        
        # Load existing images for banner cycling
        await self.banner_manager.load_existing_images()
        
        # Register commands only once
        await self.register_commands()
        
        if self.guilds:
            # Send startup message
            designated_channel_id = int(self.config.get('designated_channel_id'))
            channel = self.get_channel(designated_channel_id)
            if channel:
                embed = discord.Embed(
                    title="Bot Started",
                    description=f"freakrgb v{self.VERSION} started!",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
                print(f"Sent startup message to channel ID: {designated_channel_id}")

    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author.bot:
            return
            
        # Handle banner image uploads
        if await self.banner_manager.handle_message(message):
            return

    async def on_error(self, event_method, *args, **kwargs):
        """Handle errors globally"""
        error_info = sys.exc_info()
        exception = error_info[1]

        if isinstance(exception, discord.HTTPException) and exception.status == 429:
            # Rate limit encountered
            designated_channel_id = int(self.config.get('designated_channel_id'))
            admin_id = self.config.get('admin_id')
            channel = self.get_channel(designated_channel_id)
            if channel and admin_id:
                await channel.send(f"<@{admin_id}> The bot has hit a rate limit!")
                print(f"Rate limit hit. Notified admin ID: {admin_id} in channel ID: {designated_channel_id}")
        else:
            # Log other exceptions
            print(f"An error occurred: {exception}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        # Set the configuration path relative to the script's location
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if not os.path.exists(config_path):
            print(f"Error: config.json not found at {config_path}!")
            print("Please copy config.json.example to config.json and update the values.")
            FreakBot().handle_error()
            
        # Load the Discord bot token from environment variables
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
            print("Please ensure your .env file exists and contains a valid token.")
            FreakBot().handle_error()
            
        client = FreakBot()
        client.run(token)
    except Exception as e:
        print(f"\nError starting bot: {str(e)}")
        print("\nFull error details:")
        traceback.print_exc()
        FreakBot().handle_error()
