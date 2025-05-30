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
import os
import sys

# Import centralized constants
from src.constants import (
    APP_NAME, PERM_KEY_MICROPHONE, PERM_KEY_ACCESSIBILITY, PERM_KEY_INPUT_MONITORING, AUTH_STATUS_AUTHORIZED, AUTH_STATUS_DENIED
)

logger = logging.getLogger(__name__)

# Import these at module level to ensure they're available everywhere
NSURL = None
NSFont = None
NSColor = None
NSRunningApplication = None
NSAlert = None
NSWorkspace = None
NSApplicationActivateIgnoringOtherApps = None
NSApplicationActivateAllWindows = None
NSImage = None
NSMutableParagraphStyle = None
NSTextField = None
NSMutableAttributedString = None

if platform.system() == "Darwin":
    from AppKit import NSRunningApplication, NSAlert, NSWorkspace, NSApplicationActivateIgnoringOtherApps, NSImage
    from AppKit import NSTextField, NSFont, NSMakeSize, NSApplication, NSTextField
    from Foundation import NSURL, NSMutableAttributedString
    
    # Application activation options
    NSApplicationActivateAllWindows = 1 << 0  # Activating all windows of the application
    
    # Make these available at module level
    globals()["NSURL"] = NSURL
    globals()["NSFont"] = NSFont
    globals()["NSColor"] = NSColor
    globals()["NSRunningApplication"] = NSRunningApplication
    globals()["NSAlert"] = NSAlert
    globals()["NSWorkspace"] = NSWorkspace
    globals()["NSApplicationActivateIgnoringOtherApps"] = NSApplicationActivateIgnoringOtherApps
    globals()["NSImage"] = NSImage
    globals()["NSMutableParagraphStyle"] = NSMutableParagraphStyle
    globals()["NSTextField"] = NSTextField
    globals()["NSMutableAttributedString"] = NSMutableAttributedString
    
    # Application activation options
    NSApplicationActivateAllWindows = 1 << 0  # Activating all windows of the application
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
        Creates a completely custom alert dialog with guaranteed centered icon positioning.

        Args:
            missing_permissions_details: List of dictionaries with permission details
                Each dictionary should have: 'key', 'name', 'instruction', 'url'
        """
        if self.os_type != "Darwin" or not missing_permissions_details:
            return

        # Get the URLs for all missing permissions
        permission_urls = [p['url'] for p in missing_permissions_details]
        first_permission_url = permission_urls[0] if permission_urls else None
        
        # Create a simplified, user-friendly permission guide
        title = f"{APP_NAME} Needs Permissions"
        
        # Clear and concise permission explanations
        permission_explanations = {
            PERM_KEY_MICROPHONE: {
                "title": "Microphone Access",
                "reason": "To record and transcribe speech",
                "instruction": "System Settings → Privacy & Security → Microphone → Ottotone"
            },
            PERM_KEY_ACCESSIBILITY: {
                "title": "Accessibility Access",
                "reason": "To paste text at the cursor location",
                "instruction": "System Settings → Privacy & Security → Accessibility → Ottotone"
            },
            PERM_KEY_INPUT_MONITORING: {
                "title": "Input Monitoring",
                "reason": "To detect keyboard shortcuts while in background",
                "instruction": "System Settings → Privacy & Security → Input Monitoring → Ottotone"
            }
        }
        
        # Special handling for Input Monitoring in dev mode
        if not self.is_running_bundled():
            permission_explanations[PERM_KEY_INPUT_MONITORING]["instruction"] = (
                "System Settings → Privacy & Security → Input Monitoring → " 
                "Enable for your Terminal or IDE (VSCode, iTerm, etc.)"
            )
        
        # Construct message parts for the dialog content
        message_parts = []
        
        # Add a header if there are multiple permissions needed
        if len(missing_permissions_details) > 1:
            secondary_permissions = []
            for i, perm_info in enumerate(missing_permissions_details):
                if i > 0:  # Skip the first one
                    perm_key = perm_info['key']
                    if perm_key in permission_explanations:
                        secondary_permissions.append(permission_explanations[perm_key]["title"])
            
            if secondary_permissions:
                message_parts.append(f"After granting the first permission, you'll also need:\n{', '.join(secondary_permissions)}")
                message_parts.append("---")  # Short divider
        
        # Add each permission's details with clear formatting
        for i, perm_info in enumerate(missing_permissions_details):
            perm_key = perm_info['key']
            if perm_key in permission_explanations:
                explanation = permission_explanations[perm_key]
                
                # Add a separator between permissions if needed
                if i > 0:
                    message_parts.append("---")  # Short divider
                
                # Format each permission section clearly with proper capitalization
                message_parts.append(f"{explanation['title']}\n\nWhy:\n  {explanation['reason']}\n\nHow:\n  {explanation['instruction']}")
        
        # Join all parts with appropriate spacing (minimal)
        message_text = "\n\n".join(message_parts)

        # Create a custom alert dialog using NSAlert with proper styling
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message_text)
        alert.addButtonWithTitle_("Open Settings")
        alert.addButtonWithTitle_("Not Now")
        alert.setAlertStyle_(1)  # NSAlertStyleWarning

        # Load and set the app icon with fixed dimensions
        icon_path = "/Users/christopherwhite/Develop/projects/ottobots/ottotone/src/resources/ottotone.icns"
        icon = None
        if os.path.exists(icon_path):
            icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
            if icon:
                # Force the icon to a consistent size to help with centering
                icon.setSize_(NSMakeSize(64, 64))
                # Apply the icon to the alert
                alert.setIcon_(icon)
                logger.debug("Set custom icon for permissions dialog")

        # Force the application to the foreground to ensure visibility
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        
        # Open the system settings immediately, alongside the alert
        if first_permission_url:
            logger.info(f"Opening permission settings: {first_permission_url}")
            url = NSURL.URLWithString_(first_permission_url)
            NSWorkspace.sharedWorkspace().openURL_(url)

        # Show alert and handle response
        response = alert.runModal()

        # Log if user clicked "Not Now"
        if response != 1000:  # 1000 = first button ("Open Settings")
            logger.debug("User deferred permission settings")
            
    def _show_follow_up_instructions(self, remaining_permissions):
        """Shows a follow-up alert with instructions for remaining permissions.
        
        Args:
            remaining_permissions: List of remaining permission details to guide the user through
        """
        if not remaining_permissions:
            return
            
        # Create a simple follow-up alert
        alert = NSAlert.alloc().init()
        
        # Apply the same icon as the main permissions dialog
        icon_path = "/Users/christopherwhite/Develop/projects/ottobots/ottotone/src/resources/ottotone.icns"
        if os.path.exists(icon_path):
            try:
                icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
                if icon:
                    logger.debug("Applied icon to follow-up dialog")
                    alert.setIcon_(icon)
            except Exception as e:
                logger.warning(f"Error loading icon for follow-up dialog: {e}")
                
        alert.setMessageText_("Additional Permissions Needed")
        
        # Create a list of the remaining permissions
        perm_names = [p['name'] for p in remaining_permissions]
        perm_list = ", ".join(perm_names)
        
        informative_text = f"After granting the first permission, you'll also need to enable: {perm_list}\n\n"
        informative_text += "You can access these from the same Privacy & Security section in System Settings."
        
        alert.setInformativeText_(informative_text)
        alert.addButtonWithTitle_("Got It")
        alert.setAlertStyle_(0)  # NSAlertStyleInformational
        
        # Force the application to the foreground with the highest possible level
        app = NSRunningApplication.currentApplication()
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps | NSApplicationActivateAllWindows)
        
        # Small delay to ensure activation takes effect
        import time
        time.sleep(0.5)
        
        # Show the alert
        alert.runModal()