"""Settings window management for Ottotone."""

class SettingsManager:
    """Manages the settings window UI and interactions.
    
    Responsibilities:
    - Display settings window
    - Handle user input for changing settings
    - Coordinate with ConfigManager to save settings
    """
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.window = None # Placeholder for the settings window instance
        print("SettingsManager initialized.")

    def show_settings_window(self):
        if self.window and hasattr(self.window, 'is_visible') and self.window.is_visible():
            print("INFO: Settings window already open. Bringing to front (placeholder).")
            # self.window.bring_to_front() # If windowing library supports this
            return

        print("INFO: Showing settings window (placeholder).")
        # TODO: Implement actual settings window using a GUI library compatible with rumps
        # (e.g., custom tk.Toplevel, or a web view if going more complex).
        # For now, could use rumps.Window for very simple input, but architecture.md implies more.
        
        # Example of how it might interact with ConfigManager:
        # current_hotkey = self.config_manager.get_setting("hotkey")
        # Display current_hotkey in the UI
        
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

    def _save_setting(self, key, value):
        if self.config_manager:
            self.config_manager.set_setting(key, value)
            print(f"INFO: Setting '{key}' saved via SettingsManager.")
        else:
            print(f"WARNING: ConfigManager not available to SettingsManager. Cannot save setting '{key}'.")