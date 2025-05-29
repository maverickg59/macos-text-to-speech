"""Configuration management for Ottotone.

This package provides a modular configuration system for the Ottotone application.
Each module within this package handles a specific domain of configuration.
"""

from src.config.base import ConfigStorageManager
from src.config.audio_config import AudioConfig
from src.config.hotkey_config import HotkeyConfig
from src.config.ui_config import UIConfig
from src.config.app_config import AppConfig
from src.config.constants import (
    OUTPUT_ACTION_CLIPBOARD,
    OUTPUT_ACTION_PASTE_AT_CURSOR,
    APP_NAME,
    APP_AUTHOR,
    AVAILABLE_WHISPER_MODELS
)

__all__ = [
    'ConfigStorageManager',
    'AudioConfig',
    'HotkeyConfig', 
    'UIConfig',
    'AppConfig',
    'OUTPUT_ACTION_CLIPBOARD',
    'OUTPUT_ACTION_PASTE_AT_CURSOR',
    'APP_NAME',
    'APP_AUTHOR',
    'AVAILABLE_WHISPER_MODELS'
]
