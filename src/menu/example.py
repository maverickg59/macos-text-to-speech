"""Example usage of the menu management system for Ottotone.

This module demonstrates how to integrate the menu management system
with the main application.
"""

import rumps
import logging
from typing import Dict, Any, Optional

from ..config import AppConfig
from .menu_manager import MenuManager
from .model_menu import ModelMenu
from .output_menu import OutputMenu
from .settings_menu import SettingsMenu
from .permissions_menu import PermissionsMenu

logger = logging.getLogger(__name__)

class ExampleMenuIntegration:
    """Example showing how to integrate the menu management system.
    
    This is a simplified example meant to show the key integration
    points between the application and the menu system.
    """
    
    def __init__(self, app: rumps.App, config: AppConfig):
        """Initialize the example integration.
        
        Args:
            app: The rumps application instance
            config: The application configuration
        """
        self.app = app
        self.config = config
        self.audio_recorder = None  # In real app, this would be the AudioRecorder instance
        
        # Create menu manager
        self.menu_manager = MenuManager(app, config)
        
        # Set up menu components
        self._setup_menu_components()
        
        # Build and assign menu
        self._build_menu()
    
    def _setup_menu_components(self):
        """Set up all menu components."""
        # Register model menu component
        model_menu = ModelMenu(
            self.menu_manager, 
            self.config, 
            model_callback=self._on_model_changed
        )
        self.menu_manager.register_component("model", model_menu)
        
        # Register output menu component
        output_menu = OutputMenu(
            self.menu_manager, 
            self.config, 
            output_action_callback=self._on_output_action_changed
        )
        self.menu_manager.register_component("output", output_menu)
        
        # Register settings menu component with callbacks
        settings_callbacks = {
            "silence_threshold": self._on_silence_threshold_changed,
            "silence_duration": self._on_silence_duration_changed,
            "language": self._on_language_changed,
            "beam_size": self._on_beam_size_changed,
            "vad_filter": self._on_vad_filter_changed,
            "temperature": self._on_temperature_changed,
            "condition_on_previous_text": self._on_condition_on_prev_text_changed
        }
        settings_menu = SettingsMenu(
            self.menu_manager, 
            self.config, 
            settings_callbacks=settings_callbacks
        )
        self.menu_manager.register_component("settings", settings_menu)
        
        # Register permissions menu component
        permissions_menu = PermissionsMenu(
            self.menu_manager, 
            self.config, 
            permissions_callback=self._on_check_permissions
        )
        self.menu_manager.register_component("permissions", permissions_menu)
    
    def _build_menu(self):
        """Build and assign the menu to the application."""
        # Create a record/stop menu item (not managed by menu manager)
        record_stop_item = rumps.MenuItem("Record", callback=self._on_record_toggle)
        
        # Get all items from menu manager
        menu_items = self.menu_manager.build_menu()
        
        # Add additional items and separators
        full_menu = [
            record_stop_item,
            # Add other main items here
        ]
        
        # Add menu manager items with appropriate separators
        full_menu.extend(menu_items)
        
        # Add quit item at the end
        full_menu.extend([
            rumps.separator,
            rumps.MenuItem("Quit", callback=rumps.quit_application)
        ])
        
        # Assign to app's menu
        self.app.menu = full_menu
    
    def update_all_menus(self):
        """Update the state of all menus."""
        self.menu_manager.update_all_menus()
    
    # Example callback handlers
    
    def _on_model_changed(self, model_name: str):
        """Handle model change event.
        
        Args:
            model_name: The new model name
        """
        logger.info(f"Model changed to: {model_name}")
        # In real app, call audio_recorder.reload_model() here
    
    def _on_output_action_changed(self, action: str):
        """Handle output action change event.
        
        Args:
            action: The new output action
        """
        logger.info(f"Output action changed to: {action}")
    
    def _on_silence_threshold_changed(self, threshold: float):
        """Handle silence threshold change event.
        
        Args:
            threshold: The new silence threshold in dB
        """
        logger.info(f"Silence threshold changed to: {threshold} dB")
        # In real app, update audio recorder settings
    
    def _on_silence_duration_changed(self, duration: float):
        """Handle silence duration change event.
        
        Args:
            duration: The new silence duration in seconds
        """
        logger.info(f"Silence duration changed to: {duration} s")
        # In real app, update audio recorder settings
    
    def _on_language_changed(self, language_code: str):
        """Handle language change event.
        
        Args:
            language_code: The new language code
        """
        logger.info(f"Language changed to: {language_code}")
        # In real app, update audio recorder settings
    
    def _on_beam_size_changed(self, beam_size: int):
        """Handle beam size change event.
        
        Args:
            beam_size: The new beam size
        """
        logger.info(f"Beam size changed to: {beam_size}")
        # In real app, update audio recorder settings
    
    def _on_vad_filter_changed(self, enabled: bool):
        """Handle VAD filter change event.
        
        Args:
            enabled: Whether VAD filter is enabled
        """
        logger.info(f"VAD filter {'enabled' if enabled else 'disabled'}")
        # In real app, update audio recorder settings
    
    def _on_temperature_changed(self, temperature: float):
        """Handle temperature change event.
        
        Args:
            temperature: The new temperature
        """
        logger.info(f"Temperature changed to: {temperature}")
        # In real app, update audio recorder settings
    
    def _on_condition_on_prev_text_changed(self, enabled: bool):
        """Handle condition on previous text change event.
        
        Args:
            enabled: Whether condition on previous text is enabled
        """
        logger.info(f"Condition on previous text {'enabled' if enabled else 'disabled'}")
        # In real app, update audio recorder settings
    
    def _on_check_permissions(self):
        """Handle check permissions event."""
        logger.info("Checking permissions...")
        # In real app, check permissions and show UI
    
    def _on_record_toggle(self, sender):
        """Handle record/stop toggle event.
        
        Args:
            sender: The menu item that was clicked
        """
        # Example of toggling record state
        if sender.title == "Record":
            sender.title = "Stop"
            logger.info("Starting recording...")
            # In real app, start recording
        else:
            sender.title = "Record"
            logger.info("Stopping recording...")
            # In real app, stop recording


# Example usage
def create_example_app():
    """Create an example app using the menu system."""
    app = rumps.App("OttotoneExample")
    config = AppConfig()
    menu_integration = ExampleMenuIntegration(app, config)
    return app, menu_integration
