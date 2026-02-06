import json
import os
from pathlib import Path
from typing import Dict, Any
from .logger import logger

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "default_bitrate_profile": "Balanced",  # High Quality, Balanced, Compact, Low Bitrate
    "output_mode": "auto",                  # auto (same folder), custom
    "custom_output_folder": "",
    "theme": "Dark",
    "color_theme": "blue",
    "delete_original": False,               # If true, prompts to delete. If false, keeps it.
    "last_folder": ""
}

class ConfigManager:
    def __init__(self, filename: str = CONFIG_FILE):
        self.filename = filename
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from JSON file."""
        if not os.path.exists(self.filename):
            logger.info("No config file found. Creating default.")
            self.save()
            return

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Update current config with loaded values (merging allows new defaults in future)
                self.config.update(loaded)
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using defaults.")

    def save(self):
        """Save current configuration to JSON file."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved.")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self, key: str, default=None):
        return self.config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save() # Auto-save on change for simplicity

# Global instance
config = ConfigManager()
