"""Configuration-related constants for Ottotone.

This module contains constants related to application configuration,
file paths, and storage.
"""

import os
import appdirs
from .app_constants import APP_NAME, APP_AUTHOR

# Configuration file names and paths
CONFIG_FILE_NAME = "config.json"
CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

# Configuration domain names
CONFIG_DOMAIN_UI = "ui"
CONFIG_DOMAIN_AUDIO = "audio"
CONFIG_DOMAIN_HOTKEYS = "hotkeys"

# Configuration keys
CONFIG_KEY_SELECTED_MODEL = "selected_model"
CONFIG_KEY_OUTPUT_ACTION = "output_action"
CONFIG_KEY_SILENCE_THRESHOLD = "silence_threshold_db"
CONFIG_KEY_SILENCE_DURATION = "silence_duration_seconds"
CONFIG_KEY_LANGUAGE = "language"
CONFIG_KEY_BEAM_SIZE = "beam_size"
CONFIG_KEY_VAD_FILTER = "vad_filter"
CONFIG_KEY_VAD_PARAMETERS = "vad_parameters"
CONFIG_KEY_TEMPERATURE = "temperature"
CONFIG_KEY_CONDITION_ON_PREVIOUS_TEXT = "condition_on_previous_text"
CONFIG_KEY_RECORDING_TOGGLE_HOTKEY = "recording_toggle_hotkey"

# Default VAD parameters
DEFAULT_VAD_PARAMETERS = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "max_speech_duration_s": 30,
    "min_silence_duration_ms": 500
}
