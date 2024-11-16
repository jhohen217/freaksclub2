import discord
from discord.ext import tasks
import asyncio
import random
import aiohttp
from typing import List
from freakrgb.config_manager import ConfigManager

class AvatarManager:
    def __init__(self, client):
        self.client = client
        self.config = ConfigManager()
        self.ICON_CHANNEL_ID = self.config.get('icon_channel_id')
        self.ROLE_ID = self.config.get('role_id')  # Using same role ID for permissions
        self.ICON_CHANGE_INTERVAL = self.config.get('icon_change_interval', 20)  # seconds
        self.image_urls: List[str] = []

    def start(self):
        """Start the avatar cycling"""
        self.cycle_server_icon.start()

    def stop(self):
        """Stop the avatar cycling"""
        self.cycle_server_icon.cancel()

    async def download_image(self, url: str) -> bytes:
        """Download image from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                return None

    async def load_existing_images(self):
        """Load existing images from the specified channel"""
        channel = self.client.get_channel(self.ICON_CHANNEL_ID)
        if channel:
            async for message in channel.history(limit=100):
                if message.attachments:
                    for attachment in message.attachments:
                        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                            self.image_urls.append(attachment.url)
        print(f"Loaded {len(self.image_urls)} existing images")

    @tasks.loop()
    async def cycle_server_icon(self):
        """Periodically change the server icon"""
        await asyncio.sleep(self.ICON_CHANGE_INTERVAL)  # Wait first
        
        if not self.image_urls:
            print("No images available to set as server icon")
            return

        image_url = random.choice(self.image_urls)
        
        try:
            image_data = await self.download_image(image_url)
            if image_data:
                guild = self.client.guilds[0]
                await guild.edit(icon=image_data)
                print(f"Successfully changed server icon to {image_url}")
            else:
                print(f"Failed to download image from {image_url}")
                self.image_urls.remove(image_url)
        except Exception as e:
            print(f"Error changing server icon: {e}")
            self.image_urls.remove(image_url)

    async def handle_message(self, message):
        """Handle messages in the icon channel"""
        if message.channel.id == self.ICON_CHANNEL_ID:
            if not any(role.id == self.ROLE_ID for role in message.author.roles):
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Only server boosters can post in this channel!",
                    delete_after=5
                )
                return True

            if message.attachments:
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                        self.image_urls.append(attachment.url)
                        print(f"Added new image: {attachment.url}")
            else:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Only image posts are allowed in this channel!",
                    delete_after=5
                )
            return True
        return False
