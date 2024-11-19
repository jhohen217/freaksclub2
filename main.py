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
            self.BOOSTER_ROLE_ID = int(self.config.get('booster_role_id'))
            self.VERSION = "1.6.0"
            
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
        """Set up background tasks and register commands"""
        self.rgb_manager.start()
        self.banner_manager.start()
        
        # Register RGB commands
        @self.tree.command(name="rgbhelp", description="Show RGB-related commands")
        async def rgb_help(interaction: discord.Interaction):
            help_text = """
**RGB Role Color Commands**
`/rgbhelp` - Show this help message
`/setrgbinterval` - Set RGB color change interval (Boosters only)
"""
            await interaction.response.send_message(help_text, ephemeral=True)

        @self.tree.command(name="setrgbinterval", description="Set RGB color change interval (Boosters only)")
        async def set_rgb_interval(interaction: discord.Interaction, seconds: float):
            # Check booster role
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can modify RGB settings!", ephemeral=True)
                return

            if seconds <= 0:
                await interaction.response.send_message("Interval must be a positive number.", ephemeral=True)
                return

            self.rgb_manager.color_change_interval = seconds
            self.config.set('color_change_interval', seconds)
            await interaction.response.send_message(f"RGB color change interval set to {seconds} seconds.", ephemeral=True)

        # Register Banner commands
        @self.tree.command(name="bannerhelp", description="Show banner-related commands")
        async def banner_help(interaction: discord.Interaction):
            help_text = """
**Banner Management Commands**
`/bannerhelp` - Show this help message
`/banners` - List all saved banner images (Boosters only)
`/showbanner` - Display a specific banner image (Boosters only)
`/deletebanner` - Delete a specific banner image (Boosters only)
`/changebanner` - Manually change the server banner (Boosters only)
`/setbannerinterval` - Set banner change interval (Boosters only)
"""
            await interaction.response.send_message(help_text, ephemeral=True)

        @self.tree.command(name="banners", description="List saved banner images (Boosters only)")
        async def list_banners(interaction: discord.Interaction):
            # Check booster role
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can list banner images!", ephemeral=True)
                return

            banners = self.banner_manager.get_saved_banners()
            if not banners:
                await interaction.response.send_message("No saved banner images found.", ephemeral=True)
                return
            
            banner_list = "\n".join(f"{i+1}. {banner}" for i, banner in enumerate(banners))
            await interaction.response.send_message(f"Saved banner images:\n```\n{banner_list}\n```", ephemeral=True)

        @self.tree.command(name="changebanner", description="Manually change the server banner (Boosters only)")
        async def change_banner(interaction: discord.Interaction):
            # Check booster role
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can change the banner!", ephemeral=True)
                return

            success, result_message = await self.banner_manager.change_banner_manually()
            await interaction.response.send_message(result_message, ephemeral=True)

        @self.tree.command(name="setbannerinterval", description="Set banner change interval (Boosters only)")
        async def set_banner_interval(interaction: discord.Interaction, seconds: float):
            # Check booster role
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can modify banner settings!", ephemeral=True)
                return

            if seconds <= 0:
                await interaction.response.send_message("Interval must be a positive number.", ephemeral=True)
                return

            self.banner_manager.banner_change_interval = seconds
            self.config.set('banner_change_interval', seconds)
            await interaction.response.send_message(f"Banner change interval set to {seconds} seconds.", ephemeral=True)

        # Sync commands globally
        await self.tree.sync()

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

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle interactions"""
        await self.tree.process_app_commands(interaction)

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
