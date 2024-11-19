import json
import os

class ConfigManager:
    def __init__(self, config_path=None):
        """
        Initialize ConfigManager with optional config path.
        If no path is provided, it uses the default path.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """
        Load configuration from JSON file.
        If file doesn't exist or is invalid, return an empty dictionary.
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}")
            return {}

    def get(self, key, default=None):
        """
        Get a configuration value.
        If the key doesn't exist, return the default value.
        
        Special handling for banner_change_interval to default to 3600 if not set.
        """
        if key == 'banner_change_interval' and key not in self.config:
            return 3600  # Default to 1 hour
        
        return self.config.get(key, default)

    def set(self, key, value):
        """
        Set a configuration value and save to file.
        """
        self.config[key] = value
        self._save_config()

    def _save_config(self):
        """
        Save current configuration to JSON file.
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
