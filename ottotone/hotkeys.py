import platform

if platform.system() == "Darwin":
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

import logging
logger = logging.getLogger(__name__)


class HotkeyManager:
    MODIFIER_MAP = {
        "cmd": NSCommandKeyMask,
        "shift": NSShiftKeyMask,
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
        # Check if we're using the new HotkeyConfig or the legacy ConfigManager
        if hasattr(self.hotkey_config_manager, 'get_recording_toggle_hotkey'):
            # New HotkeyConfig
            self.hotkey_data = self.hotkey_config_manager.get_recording_toggle_hotkey()
            logger.info(f"Hotkey loaded from HotkeyConfig: {self.get_current_hotkey_display()}")
        else:
            # Legacy ConfigManager
            default_hotkey = {"key_code": 49, "modifiers": ["cmd", "shift"]}
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
        flags = 0
        if self.hotkey_data and self.hotkey_data.get("modifiers"):
            for mod_name in self.hotkey_data["modifiers"]:
                flags |= self.MODIFIER_MAP.get(mod_name, 0)
        return flags

    def event_tap_callback(self, proxy, type, event, refcon):
        if type == kCGEventKeyDown or type == kCGEventFlagsChanged:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            event_flags = CGEventGetFlags(event)
            target_flags = self._calculate_modifier_flags()

            if keycode == self.hotkey_data.get("key_code") and type == kCGEventKeyDown:
                if (event_flags & 0xFFFF0000) == target_flags:
                    logger.debug(f"Hotkey pressed: KeyCode {keycode}, Modifiers {event_flags:#x}")
                    if self.callback:
                        logger.debug("Attempting to execute hotkey callback...")
                        try:
                            self.callback()
                            logger.debug("Hotkey callback executed successfully.")
                        except Exception as e:
                            logger.error(f"Error during hotkey callback execution: {e}", exc_info=True)
                    else:
                        logger.warning("Hotkey callback is not set!")
        return event

    def start_listening(self):
        if not QUARTZ_AVAILABLE:
            logger.info("Hotkey listening is not supported on this platform (Quartz not available).")
            return False
            
        if not self.hotkey_data or not self.callback:
            logger.info("Hotkey not properly configured or no callback. Cannot start listener.")
            return False
        
        if self.is_listening:
            logger.info("Hotkey listener is already running.")
            return True
        

        logger.info(f"Attempting to start hotkey listener for: {self.get_current_hotkey_display()}")
        try:
            event_mask = (CGEventMaskBit(kCGEventKeyDown) |
                          CGEventMaskBit(kCGEventFlagsChanged))

            self.tap = CGEventTapCreate(kCGHIDEventTap, 
                                        kCGHeadInsertEventTap, 
                                        0, 
                                        event_mask,
                                        self.event_tap_callback, 
                                        None)

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
        self.hotkey_data = {"key_code": key_code, "modifiers": modifiers}
        self._save_hotkey_config()

    def get_current_hotkey_display(self):
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