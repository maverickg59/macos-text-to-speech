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

    def __init__(self, config_manager, callback):
        self.config_manager = config_manager
        self.callback = callback
        self.hotkey_config = None
        self.tap = None
        self.run_loop_source = None
        self.is_listening = False
        self._load_hotkey_config()

    def _load_hotkey_config(self):
        default_hotkey = {"key_code": 49, "modifiers": ["cmd", "shift"]}
        config_hotkey = self.config_manager.get_setting("hotkey", default_hotkey)
        
        if isinstance(config_hotkey, dict) and \
           "key_code" in config_hotkey and isinstance(config_hotkey["key_code"], int) and \
           "modifiers" in config_hotkey and isinstance(config_hotkey["modifiers"], list):
            
            valid_modifiers = all(mod in self.MODIFIER_MAP for mod in config_hotkey["modifiers"])
            if valid_modifiers:
                self.hotkey_config = config_hotkey
                logger.info(f"Hotkey loaded: {self.get_current_hotkey_display()}")
            else:
                logger.warning(f"Invalid modifiers in hotkey config: {config_hotkey['modifiers']}. Using default.")
                self.hotkey_config = default_hotkey
                self._save_hotkey_config()
        else:
            logger.warning(f"Invalid hotkey configuration loaded: {config_hotkey}. Using default.")
            self.hotkey_config = default_hotkey
            self._save_hotkey_config()

    def _save_hotkey_config(self):
        if self.hotkey_config:
            self.config_manager.set_setting("hotkey", self.hotkey_config)
            logger.info(f"Hotkey configuration saved: {self.get_current_hotkey_display()}")
        else:
            logger.warning("Attempted to save None hotkey_config.")

    def _calculate_modifier_flags(self):
        flags = 0
        if self.hotkey_config and self.hotkey_config.get("modifiers"):
            for mod_name in self.hotkey_config["modifiers"]:
                flags |= self.MODIFIER_MAP.get(mod_name, 0)
        return flags

    def event_tap_callback(self, proxy, type, event, refcon):
        if type == kCGEventKeyDown or type == kCGEventFlagsChanged:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            event_flags = CGEventGetFlags(event)
            target_flags = self._calculate_modifier_flags()

            if keycode == self.hotkey_config.get("key_code") and type == kCGEventKeyDown:
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

        if self.is_listening:
            logger.info("Hotkey listener is already running.")
            return True
        
        if not self.hotkey_config or not self.callback:
            logger.warning("Hotkey not properly configured or no callback. Cannot start listener.")
            return False

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
        self.hotkey_config = {"key_code": key_code, "modifiers": modifiers}
        self._save_hotkey_config()

    def get_current_hotkey_display(self):
        if not self.hotkey_config:
            return "Not configured"
        key_code = self.hotkey_config.get("key_code")
        mods = self.hotkey_config.get("modifiers", [])
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