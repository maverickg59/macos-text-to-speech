"""Permissions management for Ottotone.

Handles checking and guiding the user for necessary macOS permissions.
"""

import platform
import rumps
import sounddevice as sd # Keep for AudioRecorder, but not for this specific check
import logging

logger = logging.getLogger(__name__)

if platform.system() == "Darwin":
    from AppKit import NSRunningApplication, NSAlert, NSWorkspace, NSApplicationActivateIgnoringOtherApps
    from Foundation import NSURL
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    # Import AVFoundation components for passive microphone check
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio, AVAuthorizationStatusAuthorized, \
                               AVAuthorizationStatusNotDetermined, AVAuthorizationStatusDenied, AVAuthorizationStatusRestricted
    except ImportError:
        logger.error("AVFoundation module not found. Microphone permission check will be unreliable.")
        AVCaptureDevice = None # Ensure it's defined to avoid NameError later

# Define constants for System Settings URLs
PRIVACY_SETTINGS_URL_BASE = "x-apple.systempreferences:com.apple.preference.security?Privacy_"
URL_MICROPHONE = f"{PRIVACY_SETTINGS_URL_BASE}Microphone"
URL_ACCESSIBILITY = f"{PRIVACY_SETTINGS_URL_BASE}Accessibility"
URL_INPUT_MONITORING = f"{PRIVACY_SETTINGS_URL_BASE}ListenEvent" # For older macOS, might be InputMonitoring

# Permission Keys (used by app.py to pass to guide_user_to_grant_permissions)
PERM_KEY_MICROPHONE = "microphone"
PERM_KEY_ACCESSIBILITY = "accessibility"
PERM_KEY_INPUT_MONITORING = "input_monitoring"

# Expose AVFoundation status constants if AVFoundation was imported successfully
if AVCaptureDevice:
    AUTH_STATUS_AUTHORIZED = AVAuthorizationStatusAuthorized
    AUTH_STATUS_NOT_DETERMINED = AVAuthorizationStatusNotDetermined
    AUTH_STATUS_DENIED = AVAuthorizationStatusDenied
    AUTH_STATUS_RESTRICTED = AVAuthorizationStatusRestricted
else: # Fallback values if AVFoundation is not available
    AUTH_STATUS_AUTHORIZED = 0 # Placeholder, actual value might vary but conceptually represents authorized
    AUTH_STATUS_NOT_DETERMINED = 1
    AUTH_STATUS_DENIED = 2
    AUTH_STATUS_RESTRICTED = 3

class PermissionsManager:
    """Manages macOS permissions for the application.

    Responsibilities:
    - Check for microphone access.
    - Check for accessibility access (for pasting).
    - Guide user to grant permissions based on a provided list.
    """
    def __init__(self):
        self.os_type = platform.system()
        logger.info("PermissionsManager initialized.")

    def check_microphone_permission(self):
        """Checks microphone permission status using AVFoundation.
        Returns the AVAuthorizationStatus (e.g., AVAuthorizationStatusAuthorized, etc.).
        Returns AVAuthorizationStatusAuthorized for non-Darwin platforms.
        """
        if self.os_type != "Darwin":
            logger.info("Microphone permission check skipped (not on macOS). Returning AUTH_STATUS_AUTHORIZED.")
            return AUTH_STATUS_AUTHORIZED
        
        if not AVCaptureDevice: # AVFoundation failed to import
            logger.error("Cannot check microphone permission: AVFoundation components not available. Returning AUTH_STATUS_DENIED as a fallback.")
            return AUTH_STATUS_DENIED # Treat as denied to be safe

        try:
            status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
            if status == AVAuthorizationStatusAuthorized:
                logger.info("Microphone permission is granted (AVFoundation check).")
            elif status == AVAuthorizationStatusNotDetermined:
                logger.info("Microphone permission is not determined (AVFoundation check). User will be prompted by system on first use.")
            elif status == AVAuthorizationStatusDenied:
                logger.warning("Microphone permission is denied (AVFoundation check).")
            elif status == AVAuthorizationStatusRestricted:
                logger.warning("Microphone permission is restricted (AVFoundation check).")
            else:
                logger.warning(f"Unknown microphone permission status: {status} (AVFoundation check). Treating as denied.")
                return AUTH_STATUS_DENIED # Treat unknown as denied
            return status
        except Exception as e:
            logger.error(f"Error checking microphone permission with AVFoundation: {e}", exc_info=True)
            logger.warning("AVFoundation check failed. Returning AUTH_STATUS_DENIED for microphone permission to trigger guidance.")
            return AUTH_STATUS_DENIED

    def check_accessibility_permission(self, prompt_if_needed=True):
        """Checks if the application has accessibility permissions.
        
        Args:
            prompt_if_needed (bool): If True, the system may prompt the user if permissions are not granted.
                       If False, it only checks the current status without prompting.
        """
        if self.os_type != "Darwin":
            logger.info("Accessibility permission check skipped (not on macOS).")
            return True
        try:
            options = {kAXTrustedCheckOptionPrompt: True} if prompt_if_needed else None
            trusted = AXIsProcessTrustedWithOptions(options)
            if trusted:
                logger.info("Accessibility permission is granted.")
            else:
                logger.info("Accessibility permission is NOT granted." + (" System may prompt." if prompt_if_needed else ""))
            return trusted
        except Exception as e:
            logger.error(f"Could not determine accessibility status: {e}", exc_info=True)
            return False

    def guide_user_to_grant_permissions(self, missing_permissions_details):
        """Guides the user to grant permissions based on a provided list of missing ones.

        Args:
            missing_permissions_details (list): A list of dictionaries. Each dictionary
                should have: 'key' (str, e.g., PERM_KEY_MICROPHONE),
                             'name' (str, e.g., "Microphone"),
                             'instruction' (str, e.g., "System Settings > ... > Ottotone"),
                             'url' (str, e.g., URL_MICROPHONE).
        """
        if self.os_type != "Darwin":
            logger.info("Permission guidance skipped (not on macOS).")
            return

        if not missing_permissions_details:
            logger.info("guide_user_to_grant_permissions called, but no missing permissions provided.")
            return

        first_missing_permission_url = missing_permissions_details[0]['url'] # URL of the first in the list

        title = "Ottotone: Action Required"
        
        instruction_lines = []
        for i, perm_info in enumerate(missing_permissions_details):
            instruction_lines.append(f"Permission {i+1} ({perm_info['name']}):\n{perm_info['instruction']}")
        
        informative_text = "Ottotone needs the following permission(s) to function correctly:\n\n"
        informative_text += "\n\n".join(instruction_lines)
        informative_text += "\n\nClick 'Open System Settings' to go to the first missing permission, or 'Later' to dismiss."
        informative_text += "\nAfter granting Input Monitoring permission, a restart of Ottotone is recommended."

        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(informative_text)
        alert.addButtonWithTitle_("Open System Settings")
        alert.addButtonWithTitle_("Later")
        alert.setAlertStyle_(1) # NSAlertStyleWarning
        
        # Activate the application to ensure the alert is on top
        if platform.system() == "Darwin":
            NSRunningApplication.currentApplication().activateWithOptions_(NSApplicationActivateIgnoringOtherApps)

        response = alert.runModal()

        if response == 1000: # NSAlertFirstButtonReturn (value for first button)
            if first_missing_permission_url:
                logger.info(f"User clicked 'Open System Settings'. Opening URL: {first_missing_permission_url}")
                url = NSURL.URLWithString_(first_missing_permission_url)
                NSWorkspace.sharedWorkspace().openURL_(url)
            else:
                logger.warning("Attempted to open System Settings, but no specific permission URL was identified.")
                # Fallback to general Privacy & Security if a specific URL wasn't found (shouldn't happen)
                url = NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security")
                NSWorkspace.sharedWorkspace().openURL_(url)
        else:
            logger.info("User clicked 'Later' on the permission guidance alert.")