"""Ottotone - A macOS menubar application for speech-to-text transcription.

This package provides a fully-featured menubar application for macOS that enables
users to transcribe speech to text using the faster-whisper library. Key features include:

- Global hotkey support for toggling recording (default: Command+Shift+Space)
- Multiple Whisper model size options (tiny, base, small, medium, large)
- Configurable output actions: Copy to Clipboard or Paste at Cursor
- Comprehensive permission management for microphone, accessibility, and input monitoring
- Persistent configuration storage for user preferences

The application is designed specifically for macOS and relies on macOS-specific
APIs through pyobjc for functionality like global hotkeys and UI integration.

Note: faster-whisper does not support MPS (Apple Silicon) acceleration, so the
application forces CPU mode for transcription on all Macs to ensure compatibility.
"""

from src.app import OttotoneApp
from src.audio import AudioRecorder
from src.config.app_config import AppConfig
from src.hotkeys import HotkeyManager
from src.permissions import PermissionsManager

# Application metadata
__version__ = "0.1.0"  # First production-ready version
__author__ = "Ottobots Team"
__license__ = "MIT"

__all__ = [
    'OttotoneApp',
    'AudioRecorder',
    'AppConfig',
    'HotkeyManager',
    'PermissionsManager',
    '__version__',
    '__author__',
    '__license__',
]