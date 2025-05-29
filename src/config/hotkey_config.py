"""Hotkey configuration management for Ottotone."""

import logging

logger = logging.getLogger(__name__)

class HotkeyConfig:
    """Manages hotkey configuration for the application.
    
    Responsibilities:
    - Store and retrieve hotkey mappings
    - Validate hotkey configuration
    """
    
    NAMESPACE = "hotkeys"
    
    # Default values
    DEFAULT_HOTKEY = {
        "key_code": 49,      # Space key
        "modifiers": ["cmd", "shift"]
    }
    
    # Valid modifier keys
    VALID_MODIFIERS = ["cmd", "shift"]
    
    def __init__(self, storage_manager):
        """Initialize with a ConfigStorageManager instance.
        
        Args:
            storage_manager: ConfigStorageManager instance for persistence
        """
        self.storage_manager = storage_manager
        
        # Initialize with defaults if needed
        if not self.storage_manager.get_setting(self.NAMESPACE):
            self._init_default_settings()
    
    def _init_default_settings(self):
        """Initialize default hotkey settings."""
        self.storage_manager.set_setting(self.NAMESPACE, {
            "recording_toggle": self.DEFAULT_HOTKEY
        })
    
    def get_recording_toggle_hotkey(self):
        """Get the hotkey configuration for toggling recording.
        
        Returns:
            Dictionary with key_code and modifiers
        """
        hotkeys = self.storage_manager.get_setting(self.NAMESPACE, {})
        return hotkeys.get("recording_toggle", self.DEFAULT_HOTKEY)
    
    def set_recording_toggle_hotkey(self, key_code, modifiers):
        """Set the hotkey configuration for toggling recording.
        
        Args:
            key_code: The key code to use
            modifiers: List of modifier keys (must be from VALID_MODIFIERS)
            
        Returns:
            True if successful, False if validation failed
        """
        # Validate modifiers
        valid_modifiers = all(mod in self.VALID_MODIFIERS for mod in modifiers)
        
        if not valid_modifiers:
            logger.warning(f"Invalid modifiers in hotkey config: {modifiers}. Not saving.")
            return False
        
        hotkeys = self.storage_manager.get_setting(self.NAMESPACE, {})
        hotkeys["recording_toggle"] = {
            "key_code": key_code,
            "modifiers": modifiers
        }
        self.storage_manager.set_setting(self.NAMESPACE, hotkeys)
        return True
    
    def get_hotkey_display(self, hotkey=None):
        """Get a human-readable representation of the hotkey.
        
        Args:
            hotkey: Optional hotkey dictionary. If None, uses recording_toggle hotkey.
            
        Returns:
            String representation of the hotkey
        """
        if hotkey is None:
            hotkey = self.get_recording_toggle_hotkey()
            
        key_code = hotkey.get("key_code")
        mods = hotkey.get("modifiers", [])
        mod_str = "+".join(m.upper() for m in mods)
        
        # Map common key codes to readable names
        key_name = {
            49: "SPACE",
            36: "RETURN",
            53: "ESC",
            # Add more key mappings as needed
        }.get(key_code, f"KeyCode:{key_code}")
        
        return f"{mod_str}+{key_name}"
