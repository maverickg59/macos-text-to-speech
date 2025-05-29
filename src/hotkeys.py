"""Global hotkey management for Ottotone.

This module provides the HotkeyManager class which handles global hotkey detection
using macOS Quartz event taps. It enables the application to respond to user-defined
keyboard shortcuts even when the application is not in focus.

The HotkeyManager requires Input Monitoring permission on macOS to function correctly.
Without this permission, the application will not be able to detect global hotkeys.

Typical usage:
    hotkey_manager = HotkeyManager(config, toggle_recording_callback)
    hotkey_manager.start_listening()
"""

import platform
import logging

# Import centralized constants
from src.constants import (
    PLATFORM_DARWIN,
    DEFAULT_HOTKEY_KEY_CODE, DEFAULT_HOTKEY_MODIFIERS,
    MODIFIER_CMD, MODIFIER_SHIFT
)

# Set up platform-specific constants
if platform.system() == PLATFORM_DARWIN:
    from AppKit import NSCommandKeyMask, NSShiftKeyMask
    from Quartz import (
        CGEventTapCreate, kCGHIDEventTap, kCGHeadInsertEventTap, CGEventTapEnable,
        CFMachPortCreateRunLoopSource, CFRunLoopAddSource, CFRunLoopGetCurrent,
        kCFRunLoopCommonModes, CGEventMaskBit, kCGEventKeyDown, kCGEventFlagsChanged,
        CGEventGetFlags, CGEventGetIntegerValueField, kCGKeyboardEventKeycode
    )
    QUARTZ_AVAILABLE = True
else:
    NSCommandKeyMask = NSShiftKeyMask = 0
    kCGEventKeyDown = kCGEventFlagsChanged = 0
    QUARTZ_AVAILABLE = False

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Manages global hotkeys detection and configuration.
    
    This class uses Quartz event taps to detect global keyboard shortcuts, allowing
    the application to respond to hotkeys even when it doesn't have focus. It supports
    configurable hotkeys that can be saved and loaded from a configuration manager.
    
    Note:
        Requires Input Monitoring permission on macOS to function correctly.
        Without this permission, the start_listening() method will fail.
    
    Attributes:
        hotkey_config_manager: The configuration manager used to store and retrieve hotkey settings
        callback: Function to call when the configured hotkey is detected
        is_listening: Whether the hotkey manager is currently active and listening
    """
    
    # Map of modifier key names to their system-specific bit flags
    MODIFIER_MAP = {
        MODIFIER_CMD: NSCommandKeyMask,
        MODIFIER_SHIFT: NSShiftKeyMask,
    }

    def __init__(self, hotkey_config, callback):
        self.hotkey_config_manager = hotkey_config
        self.callback = callback
        self.hotkey_data = None  # Actual hotkey configuration data
        self.tap = None
        self.run_loop_source = None
        self.is_listening = False
        self._load_hotkey_config()

    def _load_hotkey_config(self):
        """Load and validate hotkey configuration from storage.
        
        This method supports both the modern config interface (with get_recording_toggle_hotkey)
        and the legacy ConfigManager interface. It includes comprehensive validation
        to ensure the hotkey data is in the correct format and contains valid modifiers.
        
        If invalid configuration is detected, it falls back to the default hotkey
        (Command+Shift+Space) and saves this default to prevent future issues.
        
        Default hotkey: key_code 49 (Space key) with cmd+shift modifiers
        """
        # Check if we're using the new HotkeyConfig or the legacy ConfigManager
        if hasattr(self.hotkey_config_manager, 'get_recording_toggle_hotkey'):
            # New HotkeyConfig
            self.hotkey_data = self.hotkey_config_manager.get_recording_toggle_hotkey()
            logger.info(f"Hotkey loaded from HotkeyConfig: {self.get_current_hotkey_display()}")
        else:
            # Legacy ConfigManager
            default_hotkey = {"key_code": DEFAULT_HOTKEY_KEY_CODE, "modifiers": DEFAULT_HOTKEY_MODIFIERS}
            self.hotkey_data = self.hotkey_config_manager.get_setting("hotkey", default_hotkey)
            
            # Validate hotkey format
            if not (isinstance(self.hotkey_data, dict) and 
                   "key_code" in self.hotkey_data and isinstance(self.hotkey_data["key_code"], int) and 
                   "modifiers" in self.hotkey_data and isinstance(self.hotkey_data["modifiers"], list)):
                logger.warning(f"Invalid hotkey configuration loaded: {self.hotkey_data}. Using default.")
                self.hotkey_data = default_hotkey
                self._save_hotkey_config()
                return
                
            # Validate modifiers
            valid_modifiers = all(mod in self.MODIFIER_MAP for mod in self.hotkey_data["modifiers"])
            if not valid_modifiers:
                logger.warning(f"Invalid modifiers in hotkey config: {self.hotkey_data['modifiers']}. Using default.")
                self.hotkey_data = default_hotkey
                self._save_hotkey_config()
                return
                
            logger.info(f"Hotkey loaded from legacy config: {self.get_current_hotkey_display()}")

    def _save_hotkey_config(self):
        """Save the current hotkey configuration to storage.
        
        This method supports both the modern config interface (with set_recording_toggle_hotkey)
        and the legacy ConfigManager interface. It ensures the hotkey configuration is
        properly persisted for future application sessions.
        
        The method handles extracting the key_code and modifiers from the hotkey_data
        dictionary before saving when using the modern interface.
        
        Note:
            No action is taken if hotkey_data is None or invalid.
        """
        if not self.hotkey_data:
            logger.warning("Attempted to save None hotkey_data.")
            return
            
        # Check if we're using the new HotkeyConfig or the legacy ConfigManager
        if hasattr(self.hotkey_config_manager, 'set_recording_toggle_hotkey'):
            # New HotkeyConfig
            key_code = self.hotkey_data.get("key_code")
            modifiers = self.hotkey_data.get("modifiers", [])
            self.hotkey_config_manager.set_recording_toggle_hotkey(key_code, modifiers)
            logger.info(f"Hotkey configuration saved to HotkeyConfig: {self.get_current_hotkey_display()}")
        else:
            # Legacy ConfigManager
            self.hotkey_config_manager.set_setting("hotkey", self.hotkey_data)
            logger.info(f"Hotkey configuration saved to legacy config: {self.get_current_hotkey_display()}")

    def _calculate_modifier_flags(self):
        """Calculate the combined modifier flags for the configured hotkey.
        
        This method converts the human-readable modifier names (e.g., "cmd", "shift")
        from the hotkey configuration into the system-specific bit flags required
        by the Quartz event system for detecting key combinations.
        
        Returns:
            int: Combined bit flags representing all modifiers for the hotkey
        """
        flags = 0
        if self.hotkey_data and self.hotkey_data.get("modifiers"):
            for mod_name in self.hotkey_data["modifiers"]:
                flags |= self.MODIFIER_MAP.get(mod_name, 0)
        return flags

    def event_tap_callback(self, proxy, type, event, refcon):
        """Callback function for the Quartz event tap that detects hotkey presses.
        
        This method is called by the Quartz event system whenever a monitored keyboard
        event occurs. It checks if the event matches the configured hotkey (both the
        key code and all required modifier flags) and invokes the callback if it does.
        
        Args:
            proxy: The Quartz event tap proxy
            type: The type of event (e.g., kCGEventKeyDown, kCGEventFlagsChanged)
            event: The Quartz event object containing event details
            refcon: Reference context (unused)
            
        Returns:
            event: The original event, allowing it to propagate to other applications
        """
        if not self.hotkey_data:
            return event

        target_key_code = self.hotkey_data.get("key_code")
        target_flags = self._calculate_modifier_flags()

        # For key down events, check if it matches our hotkey
        if type == kCGEventKeyDown:
            current_key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            current_flags = CGEventGetFlags(event)
            
            # Check if key code and all required modifier flags match
            if current_key_code == target_key_code and (current_flags & target_flags) == target_flags:
                logger.info(f"Hotkey detected: {self.get_current_hotkey_display()}")
                if self.callback:
                    self.callback()

                    logger.warning("Hotkey callback is not set!")
        return event

    def start_listening(self):
        """Start listening for the configured global hotkey.
        
        This method creates a Quartz event tap to monitor keyboard events system-wide,
        allowing the application to detect when the configured hotkey is pressed even
        when the application doesn't have focus.
        
        The hotkey detection requires Input Monitoring permission on macOS. If this
        permission is not granted, the event tap creation will fail.
        
        Returns:
            bool: True if the listener was started successfully, False otherwise
        
        Note:
            This method is macOS-specific and relies on Quartz event taps, which
            are only available on macOS.
        """
        if not QUARTZ_AVAILABLE:
            logger.warning("Hotkey listening is not available on this platform.")
            return False
            
        if self.is_listening:
            logger.debug("Hotkey listener is already active.")
            return True
            
        if not self.hotkey_data or not self.hotkey_data.get("key_code"):
            logger.warning("No hotkey configured. Cannot start listening.")
            return False

        logger.info(f"Starting hotkey listener for: {self.get_current_hotkey_display()}")
        try:
            event_mask = (1 << CGEventMaskBit(kCGEventKeyDown) | 
                        1 << CGEventMaskBit(kCGEventFlagsChanged))
            
            # Create a Quartz event tap to monitor key events
            self.tap = CGEventTapCreate(
                kCGHIDEventTap,  # Tap at the point where HID events enter the window server
                kCGHeadInsertEventTap,  # Insert at the beginning of the event stream
                0,  # Passive monitoring - events passed to other apps unmodified
                event_mask,  # Mask of events to monitor
                self.event_tap_callback,  # Callback to process events
                None  # User data (not used)
            )

            if not self.tap:
                logger.error("Failed to create event tap. This may be due to missing Input Monitoring permissions.")
                self.is_listening = False
                return False

            self.run_loop_source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), self.run_loop_source, kCFRunLoopCommonModes)
            
            CGEventTapEnable(self.tap, True)
            self.is_listening = True
            logger.info("Hotkey listener started successfully.")
            return True
        except Exception as e:
            logger.error(f"Exception while starting hotkey listener: {e}", exc_info=True)
            if self.tap:
                try: 
                    CGEventTapEnable(self.tap, False)
                except Exception as e_disable:
                    logger.error(f"Further exception while trying to disable tap during error handling: {e_disable}", exc_info=True)
            self.tap = None
            self.run_loop_source = None
            self.is_listening = False
            return False

    def stop_listening(self):
        """Stop listening for global hotkeys.
        
        This method disables the Quartz event tap and cleans up resources used
        for hotkey detection. It should be called when the application is closing
        or when hotkey detection is no longer needed.
        
        The method is safe to call even if listening hasn't been started or if
        the platform doesn't support Quartz event taps.
        """
        if not QUARTZ_AVAILABLE or not self.is_listening:
            return

        logger.info("Stopping hotkey listener...")
        if self.tap:
            try:
                CGEventTapEnable(self.tap, False)
            except Exception as e:
                logger.error(f"Exception while disabling event tap: {e}", exc_info=True)
            self.tap = None
            self.run_loop_source = None
        
        self.is_listening = False
        logger.info("Hotkey listener stopped.")

    def set_hotkey(self, key_code, modifiers):
        """Set a new hotkey configuration and save it to storage.
        
        This method allows changing the global hotkey used for activating recording.
        It creates a new hotkey configuration with the specified key code and modifiers,
        then persists it using the _save_hotkey_config method.
        
        Args:
            key_code (int): The virtual key code for the main key (e.g., 49 for Space)
            modifiers (list): List of modifier key names (e.g., ["cmd", "shift"])
        """
        self.hotkey_data = {"key_code": key_code, "modifiers": modifiers}
        self._save_hotkey_config()

    def get_current_hotkey_display(self):
        """Get a human-readable representation of the current hotkey.
        
        This method provides a user-friendly display of the configured hotkey.
        It attempts to use the config manager's display method if available,
        otherwise it falls back to a simple representation using the key code
        and modifier names.
        
        Returns:
            str: A human-readable representation of the current hotkey,
                 e.g., "CMD+SHIFT + [KeyCode: 49]" for Command+Shift+Space
        """
        if not self.hotkey_data:
            return "Not configured"
            
        # Check if we can use HotkeyConfig's display method
        if hasattr(self.hotkey_config_manager, 'get_hotkey_display'):
            return self.hotkey_config_manager.get_hotkey_display(self.hotkey_data)
            
        # Fallback to our own display logic
        key_code = self.hotkey_data.get("key_code")
        mods = self.hotkey_data.get("modifiers", [])
        mod_str = "+".join(m.upper() for m in mods)
        return f"{mod_str} + [KeyCode: {key_code}]"


if __name__ == '__main__':
    if platform.system() == "Darwin" and QUARTZ_AVAILABLE:
        logging.basicConfig(level=logging.INFO) 
        logger.info("Testing HotkeyManager...")
        class MockConfigManager:
            _hotkey_store = {}
            def get_setting(self, key, default=None):
                if key == "hotkey": return self._hotkey_store.get(key, default)
                return default
            def set_setting(self, key, value):
                logger.info(f"MockConfigManager: set {key} = {value}")
                if key == "hotkey": self._hotkey_store[key] = value
        def my_callback(): logger.info("CALLBACK: Hotkey Pressed!")
        mock_config = MockConfigManager()
        if not mock_config.get_setting("hotkey"):
             mock_config.set_setting("hotkey", {"key_code": 49, "modifiers": ["cmd", "shift"]})

        manager = HotkeyManager(mock_config, my_callback)
        logger.info(f"Attempting to listen for: {manager.get_current_hotkey_display()}")
        if manager.start_listening():
            logger.info("Hotkey listener started. Press the configured hotkey to test (e.g., Command+Shift+Space).")
            logger.info("Press Ctrl+C in console to stop this test.")
            try:
                from time import sleep
                while True: sleep(1) 
            except KeyboardInterrupt: logger.info("Stopping test due to KeyboardInterrupt...")
            finally: manager.stop_listening()
        else: logger.error("Failed to start hotkey listener. Check permissions (Input Monitoring) or console errors.")
    else: logger.info("HotkeyManager test skipped (not on macOS or Quartz not available).")