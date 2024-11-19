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
        self.image_urls: List[str] = []
        self.banners_dir = self.config.get('banner_storage_path', '/home/freaksclub2/banners')
        os.makedirs(self.banners_dir, exist_ok=True)

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
        """Load existing images from the radio channel"""
        for guild in self.client.guilds:
            for channel in guild.text_channels:
                if 'radio' in channel.name.lower():
                    async for message in channel.history(limit=100):
                        if message.attachments:
                            for attachment in message.attachments:
                                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                                    self.image_urls.append(attachment.url)
                    break
        print(f"Loaded {len(self.image_urls)} existing banner images")

    @tasks.loop()
    async def cycle_server_banner(self):
        """Periodically change the server banner"""
        await asyncio.sleep(self.banner_change_interval)
        
        if not self.image_urls:
            print("No images available to set as server banner")
            return

        image_url = random.choice(self.image_urls)
        
        try:
            image_data = await self.download_image(image_url)
            if image_data:
                guild = self.client.guilds[0]
                await guild.edit(banner=image_data)
                print(f"Successfully changed server banner to {image_url}")
            else:
                print(f"Failed to download image from {image_url}")
                self.image_urls.remove(image_url)
        except Exception as e:
            print(f"Error changing server banner: {e}")
            if "Banner is too small" not in str(e):  # Don't remove if it's just a size issue
                self.image_urls.remove(image_url)

    def get_saved_banners(self):
        """Get list of all saved banner images"""
        return [f for f in os.listdir(self.banners_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    async def change_banner_manually(self):
        """Manually change the server banner"""
        if not self.image_urls:
            return False, "No images available to set as server banner"

        image_url = random.choice(self.image_urls)
        
        try:
            image_data = await self.download_image(image_url)
            if image_data:
                guild = self.client.guilds[0]
                await guild.edit(banner=image_data)
                return True, f"Successfully changed server banner to {image_url}"
            else:
                self.image_urls.remove(image_url)
                return False, f"Failed to download image from {image_url}"
        except Exception as e:
            print(f"Error changing server banner: {e}")
            if "Banner is too small" not in str(e):  # Don't remove if it's just a size issue
                self.image_urls.remove(image_url)
            return False, str(e)

    async def handle_message(self, message):
        """Handle messages in the radio channel"""
        if 'radio' in message.channel.name.lower():
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
                        self.image_urls.append(attachment.url)
                        # Download and save locally
                        image_data = await self.download_image(attachment.url)
                        if image_data:
                            await self.save_banner_locally(image_data, attachment.filename)
                            await message.channel.send(
                                f"Banner image from {message.author.mention} has been added to the rotation!",
                                delete_after=10
                            )
                        print(f"Added new banner image: {attachment.url}")
            return True
        return False

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

**Adding New Banners**
To add a new banner image:
1. Post an image in the radio channel
2. Tag the bot in your message
3. You must have the server booster role to add images

**Note**: Banner images are stored in {0} and cycle every {1} seconds
""".format(self.banners_dir, self.banner_change_interval)
            await interaction.response.send_message(help_text, ephemeral=True)

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
            # Also remove from URLs if present
            self.image_urls = [url for url in self.image_urls if filename not in url]
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
