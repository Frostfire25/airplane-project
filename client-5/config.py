"""
Dynamic Configuration Module
Automatically reloads .env file when it changes, allowing real-time configuration updates.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from threading import Lock
from typing import Any, Optional


class DynamicConfig:
    """Configuration that automatically reloads when .env file changes."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.env_file = Path(__file__).parent / '.env'
        self._last_mtime = 0
        self._cache = {}
        self._load_env()
    
    def _load_env(self):
        """Load or reload the .env file."""
        try:
            if self.env_file.exists():
                # Get modification time
                mtime = self.env_file.stat().st_mtime
                
                # Only reload if file has changed
                if mtime != self._last_mtime:
                    load_dotenv(dotenv_path=self.env_file, override=True)
                    self._last_mtime = mtime
                    self._cache.clear()
                    
                    # Set timezone if specified
                    tz = os.getenv('TZ') or os.getenv('TIMEZONE')
                    if tz:
                        os.environ['TZ'] = tz
                        try:
                            if hasattr(time, 'tzset'):
                                time.tzset()
                        except Exception:
                            pass
        except Exception as e:
            print(f"Warning: Error loading .env file: {e}")
    
    def _check_reload(self):
        """Check if .env file has been modified and reload if needed."""
        try:
            if self.env_file.exists():
                current_mtime = self.env_file.stat().st_mtime
                if current_mtime != self._last_mtime:
                    print("🔄 Configuration file changed, reloading...")
                    self._load_env()
        except Exception as e:
            print(f"Warning: Error checking .env file: {e}")
    
    def get(self, key: str, default: Any = None, cast_type: type = str) -> Any:
        """
        Get configuration value with automatic reload check.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            cast_type: Type to cast the value to (str, int, float, bool)
        """
        with self._lock:
            self._check_reload()
            
            value = os.getenv(key)
            if value is None:
                return default
            
            # Cast to requested type
            try:
                if cast_type == bool:
                    return value.lower() in ('1', 'true', 'yes', 'on')
                elif cast_type == int:
                    return int(value)
                elif cast_type == float:
                    return float(value)
                else:
                    return value
            except (ValueError, AttributeError):
                return default
    
    def get_color(self, key: str, default: tuple = (255, 255, 255)) -> tuple:
        """Get color configuration as RGB tuple."""
        value = self.get(key)
        if not value:
            return default
        
        try:
            r, g, b = value.split(',')
            return (int(r.strip()), int(g.strip()), int(b.strip()))
        except:
            return default
    
    def reload(self):
        """Force reload the configuration."""
        with self._lock:
            self._last_mtime = 0  # Force reload
            self._load_env()


# Global configuration instance
_config = None


def get_config() -> DynamicConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = DynamicConfig()
    return _config


# Convenience functions for common config values
def get_latitude() -> float:
    return get_config().get('LATITUDE', 0.0, float)


def get_longitude() -> float:
    return get_config().get('LONGITUDE', 0.0, float)


def get_timezone() -> str:
    return get_config().get('TIMEZONE', 'America/New_York')


def get_adsb_host() -> str:
    return get_config().get('ADSB_HOST', '127.0.0.1')


def get_adsb_port() -> int:
    return get_config().get('ADSB_PORT', 30005, int)


def get_adsb_data_type() -> str:
    return get_config().get('ADSB_DATA_TYPE', 'beast')


def get_matrix_schedule_seconds() -> int:
    return get_config().get('MATRIX_SCHEDULE_SECONDS', 60, int)


def get_adsb_poll_schedule_seconds() -> int:
    return get_config().get('ADSB_POLL_SCHEDULE_SECONDS', 5, int)


def get_aircraft_display_duration() -> int:
    return get_config().get('AIRCRAFT_DISPLAY_DURATION', 10, int)


def get_matrix_width() -> int:
    return get_config().get('MATRIX_WIDTH', 64, int)


def get_matrix_height() -> int:
    return get_config().get('MATRIX_HEIGHT', 64, int)


def reload_config():
    """Force reload the configuration from .env file."""
    get_config().reload()
