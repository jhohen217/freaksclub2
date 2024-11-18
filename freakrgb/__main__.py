from .main import FreakBot
import os

if __name__ == "__main__":
    bot = FreakBot()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
