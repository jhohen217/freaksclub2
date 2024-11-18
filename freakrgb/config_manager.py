import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        # Config should be in /home/freaksclub2/config.json
        self.config_path = '/home/freaksclub2/config.json'
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
            
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading config file: {str(e)}")
        
        # Validate required fields
        required_fields = {
            'rgb_role_id': "Role ID for RGB color cycling",
            'booster_role_id': "Role ID for banner management permissions",
            'color_change_interval': "Interval (in seconds) for RGB color changes",
            'banner_change_interval': "Interval (in seconds) for banner changes",
            'banner_storage_path': "Path where banner images will be stored"
        }
        
        missing_fields = []
        for field, description in required_fields.items():
            if field not in config:
                missing_fields.append(f"{field} ({description})")
        
        if missing_fields:
            raise ValueError(
                "Missing required configuration fields:\n- " + 
                "\n- ".join(missing_fields) +
                "\n\nPlease check config.json.example for the required format."
            )
        
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
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            raise Exception(f"Error saving config file: {str(e)}")

    def update(self, key: str, value: Any):
        """Update a configuration value and save"""
        if key == 'token':
            raise ValueError("Token should be set in .env file, not in config")
        self.config[key] = value
        self.save()
