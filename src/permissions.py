"""Permissions management for Ottotone.

This module handles checking and guiding the user for necessary macOS permissions:
- Microphone access (for recording audio)
- Accessibility access (for pasting text at cursor)
- Input Monitoring (for global hotkeys with Quartz event taps)

It provides a comprehensive permissions management system that not only checks
the current permission status but also guides users through the process of granting
the necessary permissions with detailed instructions and direct links to System Settings.
"""

import platform
import logging
import sys

# Import centralized constants
from src.constants import (
    APP_NAME,
    PERM_KEY_MICROPHONE, PERM_KEY_ACCESSIBILITY, PERM_KEY_INPUT_MONITORING,
    PRIVACY_SETTINGS_URL_BASE, URL_MICROPHONE, URL_ACCESSIBILITY, URL_INPUT_MONITORING,
    AUTH_STATUS_AUTHORIZED, AUTH_STATUS_NOT_DETERMINED, AUTH_STATUS_DENIED, AUTH_STATUS_RESTRICTED
)

logger = logging.getLogger(__name__)

if platform.system() == "Darwin":
    from AppKit import NSRunningApplication, NSAlert, NSWorkspace, NSApplicationActivateIgnoringOtherApps
    from Foundation import NSURL
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio, AVAuthorizationStatusAuthorized, \
                               AVAuthorizationStatusNotDetermined, AVAuthorizationStatusDenied, AVAuthorizationStatusRestricted
    except ImportError:
        logger.error("AVFoundation module not found. Microphone permission check will be unreliable.")
        AVCaptureDevice = None

# Set authorization status constants to AVFoundation values if available
if AVCaptureDevice:
    AUTH_STATUS_AUTHORIZED = AVAuthorizationStatusAuthorized
    AUTH_STATUS_NOT_DETERMINED = AVAuthorizationStatusNotDetermined
    AUTH_STATUS_DENIED = AVAuthorizationStatusDenied
    AUTH_STATUS_RESTRICTED = AVAuthorizationStatusRestricted

class PermissionsManager:
    """Manages macOS permissions for the application.
    
    This class handles checking and guiding users through obtaining three critical permissions:
    1. Microphone access - Required for recording audio to transcribe
    2. Accessibility access - Required for the paste-at-cursor functionality
    3. Input Monitoring - Required for global hotkey detection
    
    It provides user-friendly guidance with specific instructions for each permission
    and direct links to the appropriate System Settings pages.
    """
    
    def __init__(self):
        self.os_type = platform.system()
        self.bundled = hasattr(sys, 'frozen')
        logger.debug(f"PermissionsManager initialized. Bundled: {self.bundled}")

    def is_running_bundled(self):
        """Returns True if the application is running as a bundled app."""
        return self.bundled

    def check_microphone_permission(self):
        """Checks microphone permission status.
        Returns the authorization status constant.
        """
        if self.os_type != "Darwin":
            return AUTH_STATUS_AUTHORIZED
        
        if not AVCaptureDevice:
            logger.error("Cannot check microphone permission: AVFoundation unavailable")
            return AUTH_STATUS_DENIED

        try:
            status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
            if status == AVAuthorizationStatusAuthorized:
                logger.debug("Microphone permission is granted")
            elif status == AVAuthorizationStatusNotDetermined:
                logger.debug("Microphone permission is not determined")
            elif status == AVAuthorizationStatusDenied:
                logger.warning("Microphone permission is denied")
            elif status == AVAuthorizationStatusRestricted:
                logger.warning("Microphone permission is restricted")
            else:
                logger.warning(f"Unknown microphone permission status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error checking microphone status: {e}", exc_info=True)
            return AUTH_STATUS_DENIED

    def check_accessibility_permission(self, prompt_if_needed=True):
        """Checks if the application has accessibility permissions.
        
        Args:
            prompt_if_needed: Whether to prompt the user if permission is not granted
            
        Returns:
            bool: True if permission is granted, False otherwise
        """
        if self.os_type != "Darwin":
            return True
        
        try:
            options = {kAXTrustedCheckOptionPrompt: True} if prompt_if_needed else None
            trusted = AXIsProcessTrustedWithOptions(options)
            log_level = logging.DEBUG if trusted else logging.WARNING
            logger.log(log_level, f"Accessibility permission: {'granted' if trusted else 'not granted'}{' (may prompt)' if prompt_if_needed and not trusted else ''}")
            return trusted
        except Exception as e:
            logger.error(f"Error checking accessibility status: {e}", exc_info=True)
            return False

    def guide_user_to_grant_permissions(self, missing_permissions_details):
        """Guides the user to grant permissions based on a provided list of missing ones.

        Args:
            missing_permissions_details: List of dictionaries with permission details
                Each dictionary should have: 'key', 'name', 'instruction', 'url'
        """
        if self.os_type != "Darwin" or not missing_permissions_details:
            return

        first_missing_permission_url = missing_permissions_details[0]['url']
        title = "Ottotone: Action Required"
        
        # Build instructions for each missing permission
        instruction_lines = []
        for i, perm_info in enumerate(missing_permissions_details):
            current_instruction = perm_info['instruction']
            
            # Special handling for Input Monitoring in dev mode
            if perm_info['key'] == PERM_KEY_INPUT_MONITORING and not self.is_running_bundled():
                current_instruction = (
                    f"System Settings > Privacy & Security > Input Monitoring.\n"
                    f"Enable Input Monitoring for your terminal or IDE (Terminal, iTerm, VSCode, etc.)."
                )
                
            instruction_lines.append(f"Permission {i+1} ({perm_info['name']}):\n{current_instruction}")
        
        # Compose alert text
        informative_text = "Ottotone needs the following permission(s) to function correctly:\n\n"
        informative_text += "\n\n".join(instruction_lines)
        informative_text += "\n\nClick 'Open System Settings' to go to the first missing permission, or 'Later' to dismiss."
        informative_text += "\nAfter granting Input Monitoring permission, a restart of Ottotone is recommended."

        # Create and configure alert
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(informative_text)
        alert.addButtonWithTitle_("Open System Settings")
        alert.addButtonWithTitle_("Later")
        alert.setAlertStyle_(1)  # NSAlertStyleWarning
        
        # Ensure alert is shown on top
        NSRunningApplication.currentApplication().activateWithOptions_(NSApplicationActivateIgnoringOtherApps)

        # Show alert and handle response
        response = alert.runModal()

        if response == 1000:  # First button: Open System Settings
            if first_missing_permission_url:
                logger.info(f"Opening permission settings: {first_missing_permission_url}")
                url = NSURL.URLWithString_(first_missing_permission_url)
                NSWorkspace.sharedWorkspace().openURL_(url)
            else:
                # Fallback to general Privacy & Security (shouldn't happen)
                url = NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security")
                NSWorkspace.sharedWorkspace().openURL_(url)
        else:
            logger.debug("User deferred permission settings")