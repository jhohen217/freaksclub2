import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        # Load environment variables
        load_dotenv()
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Config file not found at {self.config_path}. "
                "Please copy config.json.example to config.json and update with your settings."
            )
            
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Override token with environment variable if it exists
        token = os.getenv('DISCORD_BOT_TOKEN')
        if token:
            config['token'] = token
        
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        # Special handling for token
        if key == 'token':
            return os.getenv('DISCORD_BOT_TOKEN') or self.config.get(key, default)
        return self.config.get(key, default)

    def save(self):
        """Save current configuration to file, excluding sensitive data"""
        save_config = self.config.copy()
        # Don't save token to config file
        save_config.pop('token', None)
        
        with open(self.config_path, 'w') as f:
            json.dump(save_config, f, indent=4)

    def update(self, key: str, value: Any):
        """Update a configuration value and save"""
        if key == 'token':
            raise ValueError("Token should be set in .env file, not in config")
        self.config[key] = value
        self.save()
