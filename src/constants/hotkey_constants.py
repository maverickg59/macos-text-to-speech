"""Hotkey-related constants for Ottotone.

This module contains constants related to global hotkey detection and configuration,
including modifier keys, default hotkey settings, and input monitoring requirements.
"""

# Modifier key names
MODIFIER_CMD = "cmd"
MODIFIER_SHIFT = "shift"

# Default hotkey configuration
DEFAULT_HOTKEY_KEY_CODE = 49  # Space key
DEFAULT_HOTKEY_MODIFIERS = [MODIFIER_CMD, MODIFIER_SHIFT]  # Command+Shift

# Hotkey configuration keys
HOTKEY_CONFIG_KEY = "hotkey"
HOTKEY_KEY_CODE = "key_code"
HOTKEY_MODIFIERS = "modifiers"
