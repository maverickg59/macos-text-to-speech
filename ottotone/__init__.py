"""Ottotone - A simple menu bar app for speech-to-text.

This package provides a menu bar application for transcribing speech to text
using faster-whisper, with support for global hotkeys.
"""

from .app import OttotoneApp
from .audio import AudioRecorder
from .config import AppConfig
from .hotkeys import HotkeyManager
from .permissions import PermissionsManager

__version__ = "0.0.1"

__all__ = [
    'OttotoneApp',
    'AudioRecorder',
    'AppConfig',
    'HotkeyManager',
    'PermissionsManager',
    '__version__',
]