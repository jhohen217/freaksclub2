import discord
from discord.ext import tasks
import asyncio
import random
import aiohttp
import os
from typing import List, Optional
from .config_manager import ConfigManager

class BannerManager:
    def __init__(self, client):
        self.client = client
        self.config = ConfigManager()
        self.BOOSTER_ROLE_ID = int(self.config.get('booster_role_id'))  # Convert to int for comparison
        self.banner_change_interval = self.config.get('banner_change_interval')
        self.banners_dir = self.config.get('banner_storage_path', '/home/freaksclub2/banners')
        os.makedirs(self.banners_dir, exist_ok=True)
        self.image_paths: List[str] = []
        self.current_cycle: List[str] = []  # Track current cycle of images

        # Load designated channel ID from config
        self.designated_channel_id = int(self.config.get('designated_channel_id'))

    def start(self):
        """Start the banner cycling"""
        self.cycle_server_banner.start()

    def stop(self):
        """Stop the banner cycling"""
        self.cycle_server_banner.cancel()

    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                return None

    async def save_banner_locally(self, image_data: bytes, filename: str):
        """Save banner image to local storage"""
        filepath = os.path.join(self.banners_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filepath

    async def load_existing_images(self):
        """Load existing images from the local storage directory"""
        self.image_paths.clear()
        for filename in os.listdir(self.banners_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                filepath = os.path.join(self.banners_dir, filename)
                self.image_paths.append(filepath)
        print(f"Loaded {len(self.image_paths)} existing banner images from local storage")
        # Initialize current cycle with shuffled images
        self.current_cycle = random.sample(self.image_paths, len(self.image_paths)) if self.image_paths else []

    @tasks.loop()
    async def cycle_server_banner(self):
        """Periodically change the server banner"""
        await asyncio.sleep(self.banner_change_interval)
        
        if not self.image_paths:
            print("No images available to set as server banner")
            return

        # If current cycle is empty, create a new shuffled cycle
        if not self.current_cycle:
            self.current_cycle = random.sample(self.image_paths, len(self.image_paths))
            print("Created new shuffled cycle of banner images")

        # Get next image from current cycle
        image_path = self.current_cycle.pop(0)
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            guild = self.client.guilds[0]
            await guild.edit(banner=image_data)
            print(f"Successfully changed server banner to {image_path}")
        except Exception as e:
            print(f"Error changing server banner: {e}")
            # Remove the image from both lists if there's an error
            if image_path in self.image_paths:
                self.image_paths.remove(image_path)
            if image_path in self.current_cycle:
                self.current_cycle.remove(image_path)

    async def change_banner_manually(self):
        """Manually change the server banner"""
        if not self.image_paths:
            return False, "No images available to set as server banner"

        # If current cycle is empty, create a new shuffled cycle
        if not self.current_cycle:
            self.current_cycle = random.sample(self.image_paths, len(self.image_paths))

        image_path = self.current_cycle.pop(0)
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            guild = self.client.guilds[0]
            await guild.edit(banner=image_data)
            return True, f"Successfully changed server banner to {image_path}"
        except Exception as e:
            print(f"Error changing server banner: {e}")
            if image_path in self.image_paths:
                self.image_paths.remove(image_path)
            if image_path in self.current_cycle:
                self.current_cycle.remove(image_path)
            return False, str(e)

    async def handle_message(self, message):
        """Handle messages in the designated channel"""
        if message.channel.id == self.designated_channel_id:
            if message.attachments and self.client.user in message.mentions:
                # Check booster role
                if not any(role.id == self.BOOSTER_ROLE_ID for role in message.author.roles):
                    await message.channel.send(
                        f"{message.author.mention} Only server boosters can add banner images!",
                        delete_after=10
                    )
                    return True

                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                        # Download and save locally
                        image_data = await self.download_image(attachment.url)
                        if image_data:
                            filepath = await self.save_banner_locally(image_data, attachment.filename)
                            self.image_paths.append(filepath)
                            await message.channel.send(
                                f"Banner image from {message.author.mention} has been added to the rotation!",
                                delete_after=10
                            )
                            print(f"Added new banner image: {filepath}")
            return True
        return False

    def get_saved_banners(self):
        """Get list of all saved banner images"""
        return [f for f in os.listdir(self.banners_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    def register_commands(self, tree, guild):
        """Register banner-related slash commands"""
        
        @tree.command(name="bannerhelp", description="Show banner-related commands", guild=guild)
        async def banner_help(interaction: discord.Interaction):
            help_text = """
**Banner Management Commands**
`/bannerhelp` - Show this help message
`/banners` - List all saved banner images (Boosters only)
`/showbanner` - Display a specific banner image (Boosters only)
`/deletebanner` - Delete a specific banner image (Boosters only)
`/changebanner` - Manually change the server banner (Boosters only)
`/setbannerinterval` - Set banner change interval (Boosters only)
`/refreshbanners` - Refresh the banner image list (Boosters only)

**Adding New Banners**
To add a new banner image:
1. Post an image in the designated channel
2. Tag the bot in your message
3. You must have the server booster role to add images

**Note**: Banner images are stored in {0} and cycle every {1} seconds
""".format(self.banners_dir, self.banner_change_interval)
            await interaction.response.send_message(help_text, ephemeral=True)

        @tree.command(name="refreshbanners", description="Refresh the banner image list (Boosters only)", guild=guild)
        async def refresh_banners(interaction: discord.Interaction):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can refresh banner images!", ephemeral=True)
                return

            await self.load_existing_images()
            await interaction.response.send_message(f"Successfully refreshed banner images. Found {len(self.image_paths)} images.", ephemeral=True)

        @tree.command(name="banners", description="List saved banner images (Boosters only)", guild=guild)
        async def list_banners(interaction: discord.Interaction):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can list banner images!", ephemeral=True)
                return

            banners = self.get_saved_banners()
            if not banners:
                await interaction.response.send_message("No saved banner images found.", ephemeral=True)
                return
            
            banner_list = "\n".join(f"{i+1}. {banner}" for i, banner in enumerate(banners))
            await interaction.response.send_message(f"Saved banner images:\n```\n{banner_list}\n```", ephemeral=True)

        @tree.command(name="showbanner", description="Display a specific banner image (Boosters only)", guild=guild)
        async def show_banner(interaction: discord.Interaction, number: int):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can view banner images!", ephemeral=True)
                return

            banners = self.get_saved_banners()
            if not banners:
                await interaction.response.send_message("No saved banner images found.", ephemeral=True)
                return

            if number < 1 or number > len(banners):
                await interaction.response.send_message("Invalid banner number.", ephemeral=True)
                return

            filename = banners[number - 1]
            filepath = os.path.join(self.banners_dir, filename)
            await interaction.response.send_message(file=discord.File(filepath), ephemeral=True)

        @tree.command(name="deletebanner", description="Delete a specific banner image (Boosters only)", guild=guild)
        async def delete_banner(interaction: discord.Interaction, number: int):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can delete banner images!", ephemeral=True)
                return

            banners = self.get_saved_banners()
            if not banners:
                await interaction.response.send_message("No saved banner images found.", ephemeral=True)
                return

            if number < 1 or number > len(banners):
                await interaction.response.send_message("Invalid banner number.", ephemeral=True)
                return

            filename = banners[number - 1]
            filepath = os.path.join(self.banners_dir, filename)
            os.remove(filepath)
            # Remove from image paths and current cycle
            if filepath in self.image_paths:
                self.image_paths.remove(filepath)
            if filepath in self.current_cycle:
                self.current_cycle.remove(filepath)
            await interaction.response.send_message(f"Banner '{filename}' has been deleted.", ephemeral=True)

        @tree.command(name="changebanner", description="Manually change the server banner (Boosters only)", guild=guild)
        async def change_banner(interaction: discord.Interaction):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can change the banner!", ephemeral=True)
                return

            success, result_message = await self.change_banner_manually()
            await interaction.response.send_message(result_message, ephemeral=True)

        @tree.command(name="setbannerinterval", description="Set banner change interval (Boosters only)", guild=guild)
        async def set_banner_interval(interaction: discord.Interaction, seconds: float):
            if not any(role.id == self.BOOSTER_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("Only server boosters can modify banner settings!", ephemeral=True)
                return

            if seconds <= 0:
                await interaction.response.send_message("Interval must be a positive number.", ephemeral=True)
                return

            self.banner_change_interval = seconds
            self.config.set('banner_change_interval', seconds)
            await interaction.response.send_message(f"Banner change interval set to {seconds} seconds.", ephemeral=True)
