"""Paste-related constants for Ottotone.

This module contains constants related to the paste-at-cursor functionality,
including key codes, event flags, and timing parameters.
"""

# Key codes for keyboard simulation
KEY_CODE_V = 0x09  # Virtual keycode for 'V'
KEY_CODE_COMMAND = 0x37  # Virtual keycode for Command key

# Event flags for keyboard events
EVENT_FLAG_COMMAND = 0x100000  # Command key modifier flag (kCGEventFlagMaskCommand)

# Timing parameters
PASTE_DELAY_SEC = 0.01  # Small delay between key events in seconds
