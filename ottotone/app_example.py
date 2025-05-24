"""Example app.py implementation using the new modular configuration system.

This is an example of how the main application class could be updated
to use the new modular configuration system.
"""

import rumps
import os
import sys
import logging

from .config import AppConfig
from .audio import AudioRecorder
from .hotkeys import HotkeyManager
from .paste import paste_text_at_cursor
from .permissions import (
    PermissionsManager,
    PERM_KEY_MICROPHONE, PERM_KEY_ACCESSIBILITY, PERM_KEY_INPUT_MONITORING,
    AUTH_STATUS_AUTHORIZED
)

# Constants remain the same
APP_NAME = "Ottotone"
# ... other constants ...

class OttotoneApp(rumps.App):
    def __init__(self):
        # Initialize modular configuration system
        self.config = AppConfig()
        
        # Initialize managers and permissions
        self.permissions_manager = PermissionsManager()
        self.raw_microphone_status = None
        self.permissions_status = {
            PERM_KEY_MICROPHONE: False,
            PERM_KEY_ACCESSIBILITY: False,
            PERM_KEY_INPUT_MONITORING: False,
        }
        
        # These will be set up later
        self.audio_recorder = None
        self.hotkey_manager = None
        self.is_recording = False
        self.is_bundled = hasattr(sys, 'frozen')
        
        # Setup icon properties
        self._setup_icon()
        
        super(OttotoneApp, self).__init__(
            name=APP_NAME,
            title=self.title,
            icon=self.icon,
            template=self.template
        )
        
        # Build menu and check permissions
        self._build_menu()
        self._check_permissions_and_setup_features()
        self._update_all_menus()
    
    def _update_all_menus(self):
        """Update all menu items to reflect current configuration state."""
        self._update_model_menu()
        self._update_output_action_menu()
        self._update_silence_threshold_menu()
        self._update_max_silence_duration_menu()
        self._update_language_menu()
        # ... other menu updates ...
    
    def _update_output_action_menu(self):
        """Update the output action menu to reflect current configuration."""
        current_action = self.config.ui.get_output_action()
        
        # Get menu items
        copy_menu = self.menu.get(MENU_COPY_TO_CLIPBOARD)
        paste_menu = self.menu.get(MENU_PASTE_AT_CURSOR)
        
        if copy_menu and paste_menu:
            copy_menu.state = (current_action == "clipboard")
            paste_menu.state = (current_action == "paste_at_cursor")
    
    def _update_model_menu(self):
        """Update the model selection menu to reflect current configuration."""
        current_model = self.config.audio.get_selected_model()
        
        # Get the model submenu
        model_menu = self.menu.get(MENU_SELECT_MODEL)
        if model_menu and isinstance(model_menu, rumps.MenuItem):
            for model_name in AVAILABLE_MODELS:
                if model_name in model_menu:
                    model_menu[model_name].state = (model_name == current_model)
    
    def _update_silence_threshold_menu(self):
        """Update the silence threshold menu to reflect current configuration."""
        current_threshold = self.config.audio.get_silence_threshold_db()
        
        # Update menu items
        threshold_menu = self.menu.get(MENU_SILENCE_THRESHOLD)
        if threshold_menu:
            for threshold in SILENCE_THRESHOLDS_DB:
                menu_item_name = f"{threshold} dB"
                if menu_item_name in threshold_menu:
                    threshold_menu[menu_item_name].state = (threshold == current_threshold)
    
    def _setup_audio_recorder(self):
        """Set up the audio recorder with the current configuration."""
        try:
            logger.info("Initializing AudioRecorder...")
            self.audio_recorder = AudioRecorder(
                self.config,  # Pass the AppConfig instance
                self.handle_transcription_output
            )
            logger.info("AudioRecorder initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AudioRecorder: {e}", exc_info=True)
            self.audio_recorder = None
            return False
    
    def _setup_hotkey_manager(self):
        """Set up the hotkey manager with the current configuration."""
        try:
            temp_hotkey_manager = HotkeyManager(
                self.config.hotkeys,  # Pass the HotkeyConfig instance
                self._handle_hotkey_toggle_recording
            )
            
            if temp_hotkey_manager.start_listening():
                self.hotkey_manager = temp_hotkey_manager
                self.permissions_status[PERM_KEY_INPUT_MONITORING] = True
                logger.info("HotkeyManager initialized and listening successfully.")
                return True
            else:
                logger.warning("HotkeyManager.start_listening() failed.")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize or start HotkeyManager: {e}", exc_info=True)
            return False
    
    def select_output_action_action(self, sender, action_name):
        """Handle output action selection."""
        if self.config.ui.set_output_action(action_name):
            logger.info(f"Output action set to {action_name}")
            self._update_output_action_menu()
            
            # Additional UI feedback if needed
            if action_name == "paste_at_cursor":
                # Check if we have accessibility permission for paste
                if not self.permissions_status[PERM_KEY_ACCESSIBILITY]:
                    self.permissions_manager.request_accessibility_permission()
    
    def _select_model_action(self, sender):
        """Handle model selection."""
        model_name = sender.title
        current_model = self.config.audio.get_selected_model()
        
        if model_name != current_model:
            logger.info(f"Changing model from {current_model} to {model_name}")
            self.config.audio.set_selected_model(model_name)
            
            # Reload the model in the audio recorder
            if self.audio_recorder:
                self.audio_recorder.reload_model()
            
            self._update_model_menu()
    
    def _select_silence_threshold_action(self, sender, value_db):
        """Handle silence threshold selection."""
        current_threshold = self.config.audio.get_silence_threshold_db()
        
        if value_db != current_threshold:
            logger.info(f"Changing silence threshold from {current_threshold} to {value_db} dB")
            self.config.audio.set_silence_threshold_db(value_db)
            
            # Update the audio recorder
            if self.audio_recorder:
                self.audio_recorder._load_transcription_parameters()
            
            self._update_silence_threshold_menu()
    
    def _process_transcription_complete(self, data):
        """Process completed transcription."""
        text = data.get("text", "")
        
        if text:
            # Get the output action from UI config
            output_action = self.config.ui.get_output_action()
            
            if output_action == "clipboard":
                # Copy to clipboard logic
                rumps.notification(
                    title=APP_NAME,
                    subtitle="Transcription Copied to Clipboard",
                    message=f"{text[:50]}..." if len(text) > 50 else text
                )
            elif output_action == "paste_at_cursor":
                # Paste at cursor logic
                if self.permissions_status[PERM_KEY_ACCESSIBILITY]:
                    try:
                        paste_text_at_cursor(text)
                        rumps.notification(
                            title=APP_NAME,
                            subtitle="Text Pasted",
                            message="Transcription pasted at cursor position."
                        )
                    except Exception as e:
                        logger.error(f"Failed to paste text: {e}", exc_info=True)
                else:
                    # Fall back to clipboard if accessibility permission is missing
                    rumps.notification(
                        title=APP_NAME,
                        subtitle="Paste Failed - Missing Accessibility Permission",
                        message="Text copied to clipboard instead."
                    )
    
    # ... other methods ...

if __name__ == '__main__':
    logger.info(f"Starting {APP_NAME}...")
    app = OttotoneApp()
    app.run()
