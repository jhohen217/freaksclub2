import json
import os
import sys
import traceback
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        try:
            # Config should be in /home/freaksclub2/config.json
            self.config_path = '/home/freaksclub2/config.json'
            
            # For Windows development, check current directory
            if os.name == 'nt' and not os.path.exists(self.config_path):
                self.config_path = 'config.json'
            
            # Load environment variables
            load_dotenv()
            self.config: Dict[str, Any] = self.load_config()
            
        except Exception as e:
            print(f"\nError in ConfigManager initialization: {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables"""
        try:
            if not os.path.exists(self.config_path):
                print(f"\nError: Config file not found at {self.config_path}")
                print("\nPlease ensure config.json exists in one of these locations:")
                print("1. /home/freaksclub2/config.json (for Pi)")
                print("2. ./config.json (for local development)")
                print("\nYou can copy config.json.example to create your config file.")
                input("\nPress Enter to exit...")
                sys.exit(1)
                
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                print(f"\nError: Invalid JSON in config file: {str(e)}")
                print("Please check your config.json file for syntax errors.")
                input("\nPress Enter to exit...")
                sys.exit(1)
            except Exception as e:
                print(f"\nError reading config file: {str(e)}")
                input("\nPress Enter to exit...")
                sys.exit(1)
            
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
                print("\nError: Missing required configuration fields:")
                print("- " + "\n- ".join(missing_fields))
                print("\nPlease check config.json.example for the required format.")
                input("\nPress Enter to exit...")
                sys.exit(1)
            
            # Override token with environment variable if it exists
            token = os.getenv('DISCORD_BOT_TOKEN')
            if token:
                config['token'] = token
            
            return config
            
        except Exception as e:
            print(f"\nUnexpected error in load_config: {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        try:
            # Special handling for token
            if key == 'token':
                return os.getenv('DISCORD_BOT_TOKEN') or self.config.get(key, default)
            return self.config.get(key, default)
        except Exception as e:
            print(f"\nError getting config value '{key}': {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)

    def save(self):
        """Save current configuration to file, excluding sensitive data"""
        try:
            save_config = self.config.copy()
            # Don't save token to config file
            save_config.pop('token', None)
            
            with open(self.config_path, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            print(f"\nError saving config file: {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)

    def update(self, key: str, value: Any):
        """Update a configuration value and save"""
        try:
            if key == 'token':
                raise ValueError("Token should be set in .env file, not in config")
            self.config[key] = value
            self.save()
        except Exception as e:
            print(f"\nError updating config value '{key}': {str(e)}")
            print("\nFull error details:")
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)
