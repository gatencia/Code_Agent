import os
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Config')

class Config:
    """
    Configuration manager for the application
    Handles loading and saving settings from a JSON file
    """
    
    DEFAULT_CONFIG = {
        "server": {
            "port": 5000,
            "host": "0.0.0.0"
        },
        "ocr": {
            "tesseract_path": None,  # Will use system default if None
            "language": "eng"
        },
        "image": {
            "save_originals": True,
            "save_processed": True,
            "output_dir": "output"
        },
        "processing": {
            "capture_interval": 3,  # Seconds between captures
            "auto_detect_regions": True
        },
        "debug": {
            "verbose_logging": False,
            "save_debug_info": True
        },
        "paths": {
            "uploads": "received_images",
            "processed": "processed_images",
            "debug": "debug_output"
        }
    }
    
    def __init__(self, config_file="config.json"):
        """
        Initialize configuration
        
        Args:
            config_file (str): Path to config file
        """
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Create necessary directories
        self._create_directories()
        
        # Load configuration from file if exists
        self.load()
    
    def load(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Update config with loaded values, merging with defaults
                self._deep_update(self.config, loaded_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.info(f"No config file found at {self.config_file}, using defaults")
                # Create a default config file
                self.save()
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            logger.info("Using default configuration")
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
    
    def get(self, section, key=None):
        """
        Get configuration value
        
        Args:
            section (str): Configuration section
            key (str, optional): Configuration key within section
            
        Returns:
            The configuration value or section dict if key is None
        """
        if section not in self.config:
            return None
        
        if key is None:
            return self.config[section]
        
        if key not in self.config[section]:
            return None
        
        return self.config[section][key]
    
    def set(self, section, key, value):
        """
        Set configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key within section
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
    
    def _deep_update(self, target, source):
        """
        Recursively update a dict with another dict
        
        Args:
            target (dict): Dict to update
            source (dict): Dict with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _create_directories(self):
        """Create necessary directories from config"""
        dirs = [
            self.DEFAULT_CONFIG["paths"]["uploads"],
            self.DEFAULT_CONFIG["paths"]["processed"],
            self.DEFAULT_CONFIG["paths"]["debug"],
            self.DEFAULT_CONFIG["image"]["output_dir"]
        ]
        
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

# Singleton instance
config = Config()

# For testing or importing
if __name__ == "__main__":
    # Display current configuration
    print(json.dumps(config.config, indent=2))
    
    # Test changing a value
    old_port = config.get("server", "port")
    config.set("server", "port", 8080)
    print(f"Changed port from {old_port} to {config.get('server', 'port')}")
    
    # Save the config
    config.save()