"""Configuration management for Ottotone.

This package provides a modular configuration system for the Ottotone application.
Each module within this package handles a specific domain of configuration.
"""

from .base import ConfigStorageManager
from .audio_config import AudioConfig
from .hotkey_config import HotkeyConfig
from .ui_config import UIConfig
from .app_config import AppConfig

__all__ = [
    'ConfigStorageManager',
    'AudioConfig',
    'HotkeyConfig', 
    'UIConfig',
    'AppConfig',
]
