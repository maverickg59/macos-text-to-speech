"""Ottotone - A simple menu bar app for speech-to-text.

This package provides a menu bar application for transcribing speech to text
using faster-whisper, with support for global hotkeys.
"""

from .app import OttotoneApp
from .audio import AudioRecorder
from .config import ConfigManager
from .hotkeys import HotkeyManager
from .permissions import PermissionsManager
from .settings import SettingsManager

__version__ = "0.0.1"

__all__ = [
    'OttotoneApp',
    'AudioRecorder',
    'ConfigManager',
    'HotkeyManager',
    'PermissionsManager',
    'SettingsManager',
    '__version__',
]