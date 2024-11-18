import discord
import os
import sys
import traceback
from dotenv import load_dotenv
import freakrgb.rgb_manager as rgb_manager
import freakrgb.banner_manager as banner_manager
import freakrgb.config_manager as config_manager

# Load environment variables
load_dotenv()

class FreakBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        
        # Load configuration
        try:
            self.config = config_manager.ConfigManager()
            
            # Verify required config values exist
            required_configs = [
                'rgb_role_id',
                'booster_role_id',
                'color_change_interval',
                'banner_change_interval',
                'banner_storage_path'
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
            self.VERSION = "1.1.0"
            
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

    async def on_ready(self):
        """Handle bot ready event"""
        print("Bot is connected and ready.")
        
        # Load existing images for banner cycling
        await self.banner_manager.load_existing_images()
        
        if self.guilds:
            guild = self.guilds[0]
            
            # Send startup message
            for channel in guild.text_channels:
                if 'radio' in channel.name.lower():
                    embed = discord.Embed(
                        title="Bot Started",
                        description=f"freakrgb v{self.VERSION} started!",
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
            
        # Then try handling with Banner manager
        if await self.banner_manager.handle_command(message):
            return
            
        # Then try handling banner image uploads
        if await self.banner_manager.handle_message(message):
            return

if __name__ == "__main__":
    try:
        config_path = '/home/freaksclub2/config.json'
        if not os.path.exists(config_path):
            print(f"Error: config.json not found at {config_path}!")
            print("Please copy config.json.example to config.json and update the values.")
            FreakBot().handle_error()
            
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
