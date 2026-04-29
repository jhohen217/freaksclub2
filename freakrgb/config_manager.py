import configparser
import os

class ConfigManager:
    def __init__(self, config_path=None):
        """
        Initialize ConfigManager with optional config path.
        If no path is provided, it uses config.ini from the project root.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """
        Load configuration from INI file.
        If file doesn't exist or is invalid, return an empty config.
        """
        try:
            self.config.read(self.config_path, encoding='utf-8')
        except Exception as e:
            print(f"Error loading config: {e}")

    def get(self, key, default=None):
        """
        Get a configuration value by key.
        Supports dot notation for nested sections (e.g., 'Discord.bot_token').
        """
        # Handle dot notation for INI sections
        if '.' in key:
            section, option = key.split('.', 1)
            try:
                value = self.config.get(section, option)
                if value is None:
                    return default
                return value
            except (configparser.NoSectionError, configparser.NoOptionError):
                return default
        else:
            # Direct key access - search all sections
            for section in self.config.sections():
                try:
                    value = self.config.get(section, key)
                    if value:
                        return value
                except configparser.NoOptionError:
                    continue
            return default

    def set(self, key, value):
        """
        Set a configuration value.
        Creates a State section if it doesn't exist.
        """
        if not self.config.has_section('State'):
            self.config.add_section('State')
        self.config.set('State', key, str(value))
        self._save_config()

    def _save_config(self):
        """
        Save current configuration to INI file.
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")
