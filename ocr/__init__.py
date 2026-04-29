"""
OCR module for parsing Battle Royale Squads victory screenshots
and tracking player statistics.
"""

from .parser import OCRParser
from .stats_manager import StatsManager

__all__ = ['OCRParser', 'StatsManager']
