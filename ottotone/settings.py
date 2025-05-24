"""Settings window management for Ottotone."""

import logging

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages the settings window UI and interactions.
    
    Responsibilities:
    - Display settings window
    - Handle user input for changing settings
    - Coordinate with AppConfig to save settings
    """
    def __init__(self, app_config=None):
        self.config = app_config
        self.window = None # Placeholder for the settings window instance
        logger.info("SettingsManager initialized.")

    def show_settings_window(self):
        if self.window and hasattr(self.window, 'is_visible') and self.window.is_visible():
            print("INFO: Settings window already open. Bringing to front (placeholder).")
            # self.window.bring_to_front() # If windowing library supports this
            return

        print("INFO: Showing settings window (placeholder).")
        # TODO: Implement actual settings window using a GUI library compatible with rumps
        # (e.g., custom tk.Toplevel, or a web view if going more complex).
        # For now, could use rumps.Window for very simple input, but architecture.md implies more.
        
        # Example of how it might interact with AppConfig:
        # if self.config:
        #     current_hotkey = self.config.hotkeys.get_recording_toggle_hotkey()
        #     # Display current_hotkey in the UI
        
        # For now, simulate a simple interaction or alert:
        if 'rumps' in globals(): # Check if rumps is available (it would be if called from OttotoneApp)
            import rumps
            response = rumps.alert(
                title="Ottotone Settings",
                message="Settings window placeholder. Configure via pyproject.toml or code for now.",
                ok="OK", cancel=False
            )
        else:
            print("WARNING: rumps not available to SettingsManager for UI alert.")

    def _save_setting(self, config_domain, setting_name, value):
        """Save a setting to the specified config domain.
        
        Args:
            config_domain: The domain to save to ('audio', 'hotkeys', 'ui')
            setting_name: The name of the setting method (without 'set_' prefix)
            value: The value to save
        """
        if not self.config:
            logger.warning(f"AppConfig not available to SettingsManager. Cannot save setting '{setting_name}'")
            return False
            
        # Get the appropriate config domain
        domain = getattr(self.config, config_domain, None)
        if not domain:
            logger.warning(f"Config domain '{config_domain}' not found")
            return False
            
        # Get the setter method
        setter_name = f"set_{setting_name}"
        setter = getattr(domain, setter_name, None)
        if not setter or not callable(setter):
            logger.warning(f"Setter method '{setter_name}' not found in domain '{config_domain}'")
            return False
            
        # Call the setter
        try:
            setter(value)
            logger.info(f"Setting '{config_domain}.{setting_name}' saved via SettingsManager")
            return True
        except Exception as e:
            logger.error(f"Error saving setting '{config_domain}.{setting_name}': {e}")
            return False