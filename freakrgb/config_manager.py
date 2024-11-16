import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Config file not found at {self.config_path}. "
                "Please copy config.json.example to config.json and update with your settings."
            )
            
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)

    def save(self):
        """Save current configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def update(self, key: str, value: Any):
        """Update a configuration value and save"""
        self.config[key] = value
        self.save()
