from setuptools import setup, find_packages

setup(
    name="freakrgb",
    version="1.1.0",
    packages=find_packages(),
    install_requires=[
        'discord.py',
        'python-dotenv',
        'aiohttp'
    ],
)