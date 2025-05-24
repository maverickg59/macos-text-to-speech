"""UI configuration management for Ottotone."""

import logging

logger = logging.getLogger(__name__)

class UIConfig:
    """Manages UI-related configuration for the application.
    
    Responsibilities:
    - Store and retrieve UI preferences
    - Handle output action settings
    """
    
    NAMESPACE = "ui"
    
    # Default values
    DEFAULT_OUTPUT_ACTION = "paste_at_cursor"
    
    # Valid output actions
    VALID_OUTPUT_ACTIONS = ["clipboard", "paste_at_cursor"]
    
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
        """Initialize default UI settings."""
        self.storage_manager.set_setting(self.NAMESPACE, {
            "output_action": self.DEFAULT_OUTPUT_ACTION
        })
    
    def get_output_action(self):
        """Get the current output action setting.
        
        Returns:
            String representing the output action ("clipboard" or "paste_at_cursor")
        """
        ui_settings = self.storage_manager.get_setting(self.NAMESPACE, {})
        return ui_settings.get("output_action", self.DEFAULT_OUTPUT_ACTION)
    
    def set_output_action(self, action):
        """Set the output action.
        
        Args:
            action: The output action to set ("clipboard" or "paste_at_cursor")
            
        Returns:
            True if successful, False if validation failed
        """
        if action not in self.VALID_OUTPUT_ACTIONS:
            logger.warning(f"Invalid output action '{action}'. Not saving.")
            return False
            
        ui_settings = self.storage_manager.get_setting(self.NAMESPACE, {})
        ui_settings["output_action"] = action
        self.storage_manager.set_setting(self.NAMESPACE, ui_settings)
        return True
