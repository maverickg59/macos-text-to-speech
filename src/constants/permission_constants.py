"""Permission-related constants for Ottotone.

This module contains constants related to system permissions required by the application,
including permission keys, URLs, and status codes.
"""

# Permission Keys
PERM_KEY_MICROPHONE = "microphone"
PERM_KEY_ACCESSIBILITY = "accessibility"
PERM_KEY_INPUT_MONITORING = "input_monitoring"

# System Settings URLs
PRIVACY_SETTINGS_URL_BASE = "x-apple.systempreferences:com.apple.preference.security?Privacy_"
URL_MICROPHONE = f"{PRIVACY_SETTINGS_URL_BASE}Microphone"
URL_ACCESSIBILITY = f"{PRIVACY_SETTINGS_URL_BASE}Accessibility"
URL_INPUT_MONITORING = f"{PRIVACY_SETTINGS_URL_BASE}ListenEvent"  # For older macOS, might be InputMonitoring

# Authorization status constants
# These values will be populated at runtime from AVFoundation if available
AUTH_STATUS_AUTHORIZED = 0
AUTH_STATUS_NOT_DETERMINED = 1
AUTH_STATUS_DENIED = 2
AUTH_STATUS_RESTRICTED = 3
