"""
FreakRGB Discord Bot Package

A Discord bot that manages role color cycling and server icon cycling.
"""

from .main import FreakBot
from .rgb_manager import RGBManager
from .avatar_manager import AvatarManager
from .config_manager import ConfigManager

__all__ = ['FreakBot', 'RGBManager', 'AvatarManager', 'ConfigManager']
