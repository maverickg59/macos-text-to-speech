"""Constants used throughout the Ottotone application.

This module centralizes constants that are used across multiple modules to avoid
circular imports and duplicated definitions.
"""

# Output action constants
OUTPUT_ACTION_CLIPBOARD = "clipboard"
OUTPUT_ACTION_PASTE_AT_CURSOR = "paste_at_cursor"

# Application metadata
APP_NAME = "Ottotone"
APP_AUTHOR = "OttotoneDev"

# Whisper models available for selection
AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
