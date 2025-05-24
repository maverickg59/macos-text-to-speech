import rumps
import os
import sys
import subprocess
import logging
import platform
from AppKit import NSApplication, NSImage, NSRunningApplication

from .config import ConfigManager
from .audio import AudioRecorder
from .permissions import (
    PermissionsManager,
    PERM_KEY_MICROPHONE, PERM_KEY_ACCESSIBILITY, PERM_KEY_INPUT_MONITORING,
    URL_MICROPHONE, URL_ACCESSIBILITY, URL_INPUT_MONITORING,
    AUTH_STATUS_AUTHORIZED, AUTH_STATUS_NOT_DETERMINED, 
    AUTH_STATUS_DENIED, AUTH_STATUS_RESTRICTED
)
from .hotkeys import HotkeyManager
from .paste import paste_text_at_cursor

# --- Constants ---
APP_NAME = "Ottotone"
DEFAULT_TITLE = "OTT"
MENU_ICON_FILE = "ottotone.png"
APP_ICON_FILE = "ottotone.icns"
RESOURCES_DIR = "resources"
PLATFORM_DARWIN = "Darwin"

AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]

MENU_RECORD = "Record"
MENU_SELECT_MODEL = "Select Model"
MENU_OUTPUT_ACTION = "Output Action"
MENU_COPY_TO_CLIPBOARD = "Copy to Clipboard"
MENU_PASTE_AT_CURSOR = "Paste at Cursor"
MENU_CHECK_PERMISSIONS = "Check Permissions"
MENU_OPEN_SETTINGS = "Settings"
MENU_QUIT = "Quit Ottotone"

MENU_SILENCE_THRESHOLD = "Silence Threshold (dB)"
MENU_MAX_SILENCE_DURATION = "Max Silence Duration (s)"
MENU_TRANSCRIPTION_LANGUAGE = "Transcription Language"
MENU_COMPUTE_TYPE = "Compute Type (Quality/Speed)"
MENU_BEAM_SIZE = "Beam Size"
MENU_VAD_FILTER = "VAD Filter"
MENU_TEMPERATURE = "Temperature"
MENU_CONDITION_ON_PREV_TEXT = "Condition on Previous Text"

DEFAULT_SILENCE_THRESHOLD_DB = -30.0
DEFAULT_MAX_SILENCE_DURATION_S = 2.0
DEFAULT_LANGUAGE = "en"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 1
DEFAULT_VAD_FILTER = False
DEFAULT_TEMPERATURE = 0.0
DEFAULT_CONDITION_ON_PREV_TEXT = False

SILENCE_THRESHOLDS_DB = [-20.0, -25.0, -30.0, -35.0, -40.0, -50.0]
MAX_SILENCE_DURATIONS_S = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 5.0, 10.0]
TRANSCRIPTION_LANGUAGES = {
    "Auto Detect": None, "English": "en", "Spanish": "es", "French": "fr", 
    "German": "de", "Italian": "it", "Portuguese": "pt", "Russian": "ru",
    "Japanese": "ja", "Korean": "ko", "Chinese": "zh"
}
DEFAULT_COMPUTE_TYPE = "int8"
BEAM_SIZES = [1, 2, 3, 5]
TEMPERATURE_VALUES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

OUTPUT_ACTION_CLIPBOARD = "clipboard"
OUTPUT_ACTION_PASTE_AT_CURSOR = "paste_at_cursor"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    stream=sys.stdout  
)
logger = logging.getLogger(__name__)


class OttotoneApp(rumps.App):
    def __init__(self):
        # Initialize managers and settings first
        self.config_manager = ConfigManager() # Settings are loaded within ConfigManager's __init__
        self.permissions_manager = PermissionsManager()
        self.raw_microphone_status = None # Will store the detailed AVFoundation status
        self.permissions_status = {
            PERM_KEY_MICROPHONE: False,
            PERM_KEY_ACCESSIBILITY: False,
            PERM_KEY_INPUT_MONITORING: False, # This will be set by _setup_hotkey_manager
        }
        self.audio_recorder = None # Will be set up in _check_permissions_and_setup_features
        self.hotkey_manager = None # Will be set up in _check_permissions_and_setup_features
        self.is_recording = False
        self.selected_model = None # Will be set by _setup_audio_recorder or config

        # Setup icon properties (self.icon, self.template, self.title)
        # and set the dock icon *before* initializing rumps.App
        self._setup_icon()

        super(OttotoneApp, self).__init__(
            name=APP_NAME,
            title=self.title,      # Text in menu bar (None if icon is used)
            icon=self.icon,        # Path to menu bar icon (e.g., PNG)
            template=self.template # True for menu bar icons (monochrome, adapts to theme)
        )

        # Perform initial permission checks and setup features dependent on them
        self._check_permissions_and_setup_features()

        # Setup other components after rumps.App is initialized
        self._build_menu()
        self._update_all_menus() # Consolidated menu update calls

    def _update_all_menus(self):
        self._update_model_menu()
        self._update_output_action_menu()
        self._update_silence_threshold_menu()
        self._update_max_silence_duration_menu()
        self._update_language_menu()
        self._update_beam_size_menu()
        self._update_vad_filter_menu()
        self._update_temperature_menu()
        self._update_condition_on_prev_text_menu()
        # Add any other menu update calls here, potentially for hotkey status

    def _check_permissions_and_setup_features(self):
        logger.debug("Performing initial permission checks and setting up features.")
        
        # Initialize all statuses to False, they will be updated by checks/setups
        self.permissions_status = {
            PERM_KEY_MICROPHONE: False,
            PERM_KEY_ACCESSIBILITY: False,
            PERM_KEY_INPUT_MONITORING: False, # This will be set by _setup_hotkey_manager
        }

        # Step 1: Check Microphone (passive) and Accessibility directly
        self.raw_microphone_status = self.permissions_manager.check_microphone_permission()
        self.permissions_status[PERM_KEY_MICROPHONE] = (self.raw_microphone_status == AUTH_STATUS_AUTHORIZED)
        
        self.permissions_status[PERM_KEY_ACCESSIBILITY] = self.permissions_manager.check_accessibility_permission(prompt_if_needed=False)

        # Step 2: Setup Audio Recorder (depends on microphone permission status)
        self._setup_audio_recorder()

        # Step 3: Setup Hotkey Manager (this will attempt to listen and set input_monitoring status)
        self._setup_hotkey_manager()

        # Step 4: Compile list of missing permissions and guide user
        missing_permissions_details = []

        # Microphone permission guidance is now based on whether AudioRecorder was successfully set up
        if not self.audio_recorder:
            logger.info("AudioRecorder not available, indicating potential microphone permission issue.")
            missing_permissions_details.append({
                'key': PERM_KEY_MICROPHONE,
                'name': "Microphone",
                'instruction': f"System Settings > Privacy & Security > Microphone > Ottotone",
                'url': URL_MICROPHONE
            })

        if not self.permissions_status[PERM_KEY_ACCESSIBILITY]:
            missing_permissions_details.append({
                'key': PERM_KEY_ACCESSIBILITY,
                'name': "Accessibility",
                'instruction': f"System Settings > Privacy & Security > Accessibility > Ottotone",
                'url': URL_ACCESSIBILITY
            })

        if not self.permissions_status[PERM_KEY_INPUT_MONITORING]:
            current_process_app_name = "Ottotone" # Default for bundled app
            additional_note = "(A restart of Ottotone is recommended after granting.)"
            if not getattr(sys, 'frozen', False): # Development mode
                try:
                    current_process_app_name = NSRunningApplication.currentApplication().localizedName()
                    if not current_process_app_name: # Fallback if localizedName is empty
                         current_process_app_name = "your Terminal/Python environment"
                except Exception:
                    current_process_app_name = "your Terminal/Python environment"
                additional_note = f"(Ensure {current_process_app_name} is enabled. A restart of Ottotone is recommended after granting.)"
            
            input_monitoring_instruction = f"System Settings > Privacy & Security > Input Monitoring > {current_process_app_name}. {additional_note}"
            missing_permissions_details.append({
                'key': PERM_KEY_INPUT_MONITORING,
                'name': "Input Monitoring",
                'instruction': input_monitoring_instruction,
                'url': URL_INPUT_MONITORING
            })

        if missing_permissions_details:
            logger.info(f"Missing permissions: {[p['name'] for p in missing_permissions_details]}. Guiding user.")
            self.permissions_manager.guide_user_to_grant_permissions(missing_permissions_details)
            # Re-check basic permissions after guidance. 
            # For microphone, the key is whether audio_recorder could be setup on a subsequent attempt (e.g. toggle_recording)
            self.permissions_status[PERM_KEY_ACCESSIBILITY] = self.permissions_manager.check_accessibility_permission(prompt_if_needed=False)
            # Input Monitoring relies on restart/re-tap attempt, user is advised.
            # Passive mic check can be updated too, but self.audio_recorder status is more telling for app functionality.
            # Update raw status and boolean flag after guidance
            self.raw_microphone_status = self.permissions_manager.check_microphone_permission()
            self.permissions_status[PERM_KEY_MICROPHONE] = (self.raw_microphone_status == AUTH_STATUS_AUTHORIZED)

    def _update_model_menu(self):
        # Placeholder for model menu update logic
        # This should be similar to _update_output_action_menu
        # but for the model selection submenu.
        selected_model = self.config_manager.get_selected_model()
        if hasattr(self, 'menu_model_selector') and isinstance(self.menu_model_selector, rumps.MenuItem):
            # Ensure submenu is populated if not already
            if not self.menu_model_selector.items():
                for model_name in AVAILABLE_MODELS:
                    self.menu_model_selector.add(rumps.MenuItem(model_name, callback=self._select_model_action))
            
            for item_title, item_obj in self.menu_model_selector.items():
                item_obj.state = (item_title == selected_model)
        else:
            logger.debug("Model selector menu item not ready for update.")

    def _update_output_action_menu(self):
        current_action = self.config_manager.get_setting("output_action", OUTPUT_ACTION_CLIPBOARD)
        if hasattr(self, 'menu_output_copy') and hasattr(self, 'menu_output_paste'):
            self.menu_output_copy.state = (current_action == OUTPUT_ACTION_CLIPBOARD)
            self.menu_output_paste.state = (current_action == OUTPUT_ACTION_PASTE_AT_CURSOR)
        else:
            logger.debug("Output action menu items not yet initialized for state update.")

    def _update_silence_threshold_menu(self):
        current_threshold = self.config_manager.get_setting("silence_threshold_db", DEFAULT_SILENCE_THRESHOLD_DB)
        for val_db, item in self.menu_silence_threshold_items.items():
            item.state = (abs(val_db - current_threshold) < 0.01) # Compare floats carefully

    def _update_max_silence_duration_menu(self):
        current_duration = self.config_manager.get_setting("silence_duration_seconds", DEFAULT_MAX_SILENCE_DURATION_S)
        for val_s, item in self.menu_max_silence_duration_items.items():
            item.state = (abs(val_s - current_duration) < 0.01) # Compare floats carefully

    def _update_language_menu(self):
        current_lang = self.config_manager.get_setting("transcription_language", DEFAULT_LANGUAGE)
        # Handle if None is stored as string 'None' from older configs potentially
        if current_lang == 'None': current_lang = None 
        for lang_code, item in self.menu_language_items.items():
            item.state = (lang_code == current_lang)


    def _update_beam_size_menu(self):
        current_bs = self.config_manager.get_setting("transcription_beam_size", DEFAULT_BEAM_SIZE)
        for bs_val, item in self.menu_beam_size_items.items():
            item.state = (bs_val == current_bs)

    def _update_vad_filter_menu(self):
        current_vad = self.config_manager.get_setting("transcription_vad_filter", DEFAULT_VAD_FILTER)
        if hasattr(self, 'menu_vad_filter_toggle'):
            self.menu_vad_filter_toggle.state = current_vad

    def _update_temperature_menu(self):
        current_temp = self.config_manager.get_setting("transcription_temperature", DEFAULT_TEMPERATURE)
        for temp_val, item in self.menu_temperature_items.items():
            item.state = (abs(temp_val - current_temp) < 0.01)

    def _update_condition_on_prev_text_menu(self):
        current_copt = self.config_manager.get_setting("transcription_condition_on_previous_text", DEFAULT_CONDITION_ON_PREV_TEXT)
        if hasattr(self, 'menu_condition_prev_text_toggle'):
            self.menu_condition_prev_text_toggle.state = current_copt

    def _select_model_action(self, sender):
        selected_model_name = sender.title
        if selected_model_name != self.selected_model:
            self.selected_model = selected_model_name
            self.config_manager.set_setting("selected_model", self.selected_model)
            logger.info(f"Model selected: {self.selected_model}")
            self.audio_recorder.reload_model() 
            self._update_model_menu() 

    def select_output_action_action(self, sender, action_name):
        self.config_manager.set_setting("output_action", action_name)
        logger.info(f"Output action set to: {action_name}")
        self._update_output_action_menu()

    @rumps.clicked(MENU_CHECK_PERMISSIONS)
    def check_permissions_action(self, sender):
        logger.info("'Check Permissions' clicked. Re-evaluating permissions.")
        self._check_permissions_and_setup_features() # This will re-check and guide if necessary
        self._update_all_menus() # Update UI based on any changes

    def open_settings_window_action(self, sender):
        logger.info("'Open Settings' clicked, but no window is implemented yet.")
        rumps.alert(title=APP_NAME, message="Settings window not yet implemented.")

    @rumps.clicked(MENU_RECORD)
    def toggle_recording_action(self, sender):
        logger.debug(f"Toggle recording action called. Current recording state: {self.is_recording}")

        if not self.audio_recorder:
            logger.warning("Record action attempted, but AudioRecorder is not initialized. Re-checking permissions.")
            self._check_permissions_and_setup_features() # This will guide the user if permissions are missing
            if not self.audio_recorder:
                logger.error("AudioRecorder still not available after permission check. Recording cannot start.")
                rumps.notification(
                    title=APP_NAME,
                    subtitle="Recording Failed",
                    message="Microphone access is required. Please grant permission and try again."
                )
                self._update_recording_ui_state(is_recording=False, reason="AudioRecorder unavailable")
                return
            else:
                logger.info("AudioRecorder became available after permission check.")

        if not self.is_recording:
            logger.debug("APP Hotkey: Starting recording.")
            self.audio_recorder.start_recording()
        else:
            logger.debug("APP Hotkey: Stopping recording.")
            self.audio_recorder.stop_recording()

    def _process_transcription_complete(self, data):
        transcribed_text = data.get("text", "")
        # language_detected = data.get("language", "unknown")
        logger.info(f"Transcription successful: '{transcribed_text}'")
        self._update_all_menus() # Ensures menu reflects that recording has stopped

        if not transcribed_text.strip():
            logger.info("Transcription is empty or whitespace, not processing further.")
            return

        output_action = self.config_manager.get_output_action()
        final_text = data.get("text", "")

        if not final_text:
            logger.info("Transcription result is empty.")
            rumps.notification(APP_NAME, "Transcription Empty", "No speech detected or result was empty.")
            return

        if output_action == OUTPUT_ACTION_CLIPBOARD:
            try:
                subprocess.run("pbcopy", text=True, input=final_text, check=True)
                logger.info("Text copied to clipboard.")
                rumps.notification(APP_NAME, "Copied to Clipboard", final_text)
            except Exception as e_clipboard:
                logger.error(f"Failed to copy to clipboard: {e_clipboard}", exc_info=True)
                rumps.notification(APP_NAME, "Copy Error", str(e_clipboard))
        elif output_action == OUTPUT_ACTION_PASTE_AT_CURSOR:
            if self.permissions_manager.check_accessibility_permission(prompt_if_needed=False):
                logger.info("Pasting text at cursor.")
                paste_text_at_cursor(final_text)
                rumps.notification(APP_NAME, "Pasted at Cursor", final_text)
            else:
                logger.warning("Paste at cursor failed: Accessibility permission not granted. Falling back to clipboard.")
                # Guide user specifically for Accessibility
                missing_accessibility = [{
                    'key': PERM_KEY_ACCESSIBILITY,
                    'name': "Accessibility",
                    'instruction': f"System Settings > Privacy & Security > Accessibility > {APP_NAME}",
                    'url': URL_ACCESSIBILITY
                }]
                self.permissions_manager.guide_user_to_grant_permissions(missing_accessibility)
                
                # Fallback to clipboard
                try:
                    subprocess.run("pbcopy", text=True, input=final_text, check=True)
                    logger.info("Text copied to clipboard as fallback.")
                    rumps.notification(APP_NAME, "Paste Failed: Permission Needed", "Accessibility permission required. Text copied to clipboard instead.")
                except Exception as e_clipboard_fallback:
                    logger.error(f"Fallback to clipboard failed: {e_clipboard_fallback}", exc_info=True)
                    rumps.notification(APP_NAME, "Action Failed", "Accessibility permission needed and could not copy to clipboard.")
        else:
            logger.error(f"Unknown output action: {output_action}")
            rumps.notification(APP_NAME, "Error", f"Unknown output action: {output_action}")

    def _process_error_status(self, data):
        error_message = data.get("message", "An unknown error occurred.")
        logger.error(f"Transcription error: {error_message}")
        self._update_recording_ui_state(False) # Error, so not actively recording
        rumps.notification(APP_NAME, "Transcription Error", error_message)

    def _process_recording_started(self, data):
        logger.info("APP: Recording started.")
        self.is_recording = True
        self._update_all_menus() # Replaced _update_menu_state() and removed _update_menu_icon()
        # Update VAD status if provided
        if data and "vad_status" in data:
            self._process_vad_status_change(data["vad_status"])

    def _process_recording_stopped(self, data):
        reason = data.get("reason", "unknown")
        logger.info(f"Recording stopped. Reason: {reason}")
        # If recording stopped for reasons other than silence detection (which leads to transcription),
        # reset the UI to its default non-recording state.
        # If due to silence, '_process_transcribing_status' will handle the UI update.
        if reason not in ["silence_detected"]:
            self._update_recording_ui_state(False)

    def _process_transcribing_status(self, data):
        reason = data.get("reason", "unknown")
        logger.info(f"Transcription started. Reason: {reason}")
        if reason == "silence_detected":
            self._update_recording_ui_state(True, "Transcribing (silence)...") # Still 'recording' from user perspective until text ready
        else: # manual_stop or other reasons
            self._update_recording_ui_state(True, "Transcribing...")

    def _process_silence_detected_stopping(self, data):
        logger.info("Silence detected, recording is stopping...")
        self._update_recording_ui_state(True, "Stopping (silence)...") # Intermediate state

    def _process_no_audio_recorded(self, data):
        logger.info("No audio was recorded or audio was too short.")
        self._update_recording_ui_state(False)
        rumps.notification(APP_NAME, "No Audio", "No audio was recorded.")

    def _process_silence_limit_reached(self, data):
        reason = data.get("reason", "unknown")
        logger.info(f"AudioRecorder reported: silence_limit_reached. Reason: {reason if reason else 'N/A'}. Data: {data}")
        # This is purely informational from audio.py, no UI state change needed here.

    def _process_unhandled_status(self, data):
        status = data.get("status")
        reason = data.get("reason", "unknown")
        logger.warning(f"Unhandled status from AudioRecorder: {status}, Reason: {reason}, Data: {data}")

    def handle_transcription_output(self, output_data):
        logger.debug(f"APP: Raw output_data received: {output_data}")
        status_val = output_data.get("status")
        logger.debug(f"APP: Extracted status_val: {repr(status_val)}, type: {type(status_val)}")

        status_handlers = {
            "transcription_complete": self._process_transcription_complete,
            "error": self._process_error_status,
            "recording_started": self._process_recording_started,
            "recording_stopped": self._process_recording_stopped,
            "transcribing": self._process_transcribing_status,
            "silence_detected_stopping": self._process_silence_detected_stopping,
            "no_audio_recorded": self._process_no_audio_recorded,
            "silence_limit_reached": self._process_silence_limit_reached,
        }

        handler = status_handlers.get(status_val, self._process_unhandled_status)
        try:
            handler(output_data)
        except Exception as e:
            logger.error(f"Error processing status '{status_val}': {e}", exc_info=True)
            # Ensure UI is reset if something goes wrong during status processing
            if status_val in ["recording_started", "recording_stopped"]: 
                # It's generally safer to set is_recording to False if an error occurs
                # during start/stop, and then update UI.
                self.is_recording = False # Ensure a known state
                self._update_all_menus() # Replaced _update_menu_state() and removed _update_menu_icon()
            # Optionally, display a user-friendly error message via rumps.alert
            # self.show_alert("Error", f"An internal error occurred: {str(e)[:100]}...")

    @rumps.clicked(MENU_QUIT)
    def quit_app(self, sender):
        logger.info("Quit clicked. Cleaning up...")
        if self.audio_recorder:
            logger.info("Shutting down AudioRecorder...")
            self.audio_recorder.shutdown()
        
        if self.hotkey_manager:
            logger.info("Stopping HotkeyManager listener...")
            self.hotkey_manager.stop_listening()

        logger.info("Quitting application.")
        rumps.quit_application()

    def _start_hotkey_listener(self):
        if self.hotkey_manager:
            logger.info("Attempting to start hotkey listener...")
            if not self.hotkey_manager.start_listening():
                logger.warning("Failed to start hotkey listener, guiding user for Input Monitoring permissions.")
                self.permissions_manager.guide_user_to_grant_permissions(permission_type="input_monitoring")
            else:
                logger.info("Hotkey listener started successfully.")

    def _handle_hotkey_toggle_recording(self):
        logger.debug("APP Hotkey: Toggle recording requested by hotkey.")
        # Check for microphone permission first
        if not self.permissions_manager.check_microphone_permission(): # Corrected method name
            logger.warning("APP Hotkey: Microphone permission not granted. Cannot record.")
            self.permissions_manager.alert_missing_microphone_permission()
        if not self.audio_recorder:
            logger.warning("AudioRecorder not available, cannot toggle recording via hotkey.")
            # Optionally, provide user feedback, e.g., a notification
            # rumps.notification(title=APP_NAME, subtitle="Audio Error", message="Cannot toggle recording. Audio system not ready.")
            return

        if self.audio_recorder.is_recording:
            logger.debug("APP Hotkey: Stopping recording.")
            self.audio_recorder.stop_recording()
        else:
            # Before starting, ensure permissions are still valid, especially microphone
            # This is a good place for a quick re-check if it's not too expensive
            # or rely on AudioRecorder to handle errors if mic is lost.
            logger.debug("APP Hotkey: Starting recording.")
            self.audio_recorder.start_recording()

    def _select_silence_threshold_action(self, sender, value_db):
        logger.info(f"Silence threshold selected: {value_db} dB")
        self.config_manager.set_setting("silence_threshold_db", value_db)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_silence_threshold_menu()

    def _select_max_silence_duration_action(self, sender, value_s):
        logger.info(f"Max silence duration selected: {value_s} s")
        self.config_manager.set_setting("silence_duration_seconds", value_s)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_max_silence_duration_menu()

    def _select_language_action(self, sender, lang_code):
        logger.info(f"Transcription language selected: {lang_code if lang_code else 'Auto-detect'}")
        self.config_manager.set_setting("transcription_language", lang_code)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters() # Language change doesn't strictly need model reload, just params
            # However, if changing from/to auto-detect or a specific language, a model reload might be beneficial if model internal state is lang-specific
            # For simplicity, we can opt to reload model to be safe, or trust faster-whisper handles it via params.
            # self.audio_recorder.reload_model() # Optional: consider if model reload is better
        self._update_language_menu()


    def _select_beam_size_action(self, sender, beam_size_value):
        logger.info(f"Beam size selected: {beam_size_value}")
        self.config_manager.set_setting("transcription_beam_size", beam_size_value)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_beam_size_menu()

    def _toggle_vad_filter_action(self, sender):
        current_vad = self.config_manager.get_setting("transcription_vad_filter", DEFAULT_VAD_FILTER)
        new_vad = not current_vad
        logger.info(f"VAD Filter toggled to: {new_vad}")
        self.config_manager.set_setting("transcription_vad_filter", new_vad)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_vad_filter_menu()

    def _select_temperature_action(self, sender, temp_value):
        logger.info(f"Temperature selected: {temp_value}")
        self.config_manager.set_setting("transcription_temperature", temp_value)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_temperature_menu()

    def _toggle_condition_on_prev_text_action(self, sender):
        current_copt = self.config_manager.get_setting("transcription_condition_on_previous_text", DEFAULT_CONDITION_ON_PREV_TEXT)
        new_copt = not current_copt
        logger.info(f"Condition on Previous Text toggled to: {new_copt}")
        self.config_manager.set_setting("transcription_condition_on_previous_text", new_copt)
        if self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
        self._update_condition_on_prev_text_menu()

    def _setup_icon(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            app_icon_path = os.path.join(base_path, RESOURCES_DIR, APP_ICON_FILE)    # For Dock (app.icns)
            menu_icon_path = os.path.join(base_path, RESOURCES_DIR, MENU_ICON_FILE) # For Menu Bar (ottotone.png)

            self.icon = None
            self.template = False # Default, will be True if menu_icon_path is valid PNG

            if os.path.exists(menu_icon_path):
                self.icon = menu_icon_path  # Used by rumps for menu bar icon
                self.template = True        # Crucial for menu bar icon rendering (template image)
                logger.info(f"Menu icon will be set to: {menu_icon_path} with template mode.")
            else:
                logger.warning(f"Menu icon file not found: {menu_icon_path}. Ottotone will use text title in menu bar.")

            # Attempt to set the dock icon regardless of menu icon status
            if os.path.exists(app_icon_path):
                self._set_dock_icon(app_icon_path)
            else:
                logger.warning(f"Dock icon file not found: {app_icon_path}. System default dock icon will be used.")

            # Determine title for menu bar (text if no icon, None if icon is present)
            if self.icon is None:
                self.title = DEFAULT_TITLE
            else:
                self.title = None

        except Exception as e:
            logger.error(f"Error during icon setup: {e}", exc_info=True)
            # Fallback to defaults
            self.icon = None
            self.template = False
            self.title = DEFAULT_TITLE

    def _set_dock_icon(self, icon_path):
        """Sets the application's dock icon on macOS."""
        if platform.system() == PLATFORM_DARWIN:
            try:
                app = NSApplication.sharedApplication()
                #initWithContentsOfFile: is the correct method for loading an image from a path.
                image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                if image:
                    app.setApplicationIconImage_(image)
                    logger.info(f"Successfully set dock icon to {icon_path}")
                else:
                    logger.error(f"Failed to load NSImage from path: {icon_path}. Dock icon not set.")
            except Exception as e:
                logger.error(f"Exception setting dock icon: {e}", exc_info=True)
        else:
            logger.debug("Dock icon setting is only applicable on macOS.")

    def _build_menu(self):
        self.menu_record_stop = rumps.MenuItem(MENU_RECORD, callback=self.toggle_recording_action)
        self.menu_model_selector = rumps.MenuItem(MENU_SELECT_MODEL)
        self.menu_check_permissions = rumps.MenuItem(MENU_CHECK_PERMISSIONS, callback=self.check_permissions_action)
        self.menu_quit = rumps.MenuItem(MENU_QUIT)

        # --- Output Action Submenu Items ---
        self.menu_output_copy = rumps.MenuItem(
            MENU_COPY_TO_CLIPBOARD,
            callback=lambda s: self.select_output_action_action(s, OUTPUT_ACTION_CLIPBOARD)
        )
        self.menu_output_paste = rumps.MenuItem(
            MENU_PASTE_AT_CURSOR,
            callback=lambda s: self.select_output_action_action(s, OUTPUT_ACTION_PASTE_AT_CURSOR)
        )

        # --- Settings Submenu: Silence Threshold ---
        self.menu_silence_threshold_items = {}
        threshold_submenu_items = []
        for val_db in SILENCE_THRESHOLDS_DB:
            item = rumps.MenuItem(f"{val_db:.1f} dB", callback=lambda s, v=val_db: self._select_silence_threshold_action(s, v))
            self.menu_silence_threshold_items[val_db] = item
            threshold_submenu_items.append(item)

        # --- Settings Submenu: Max Silence Duration ---
        self.menu_max_silence_duration_items = {}
        duration_submenu_items = []
        for val_s in MAX_SILENCE_DURATIONS_S:
            item = rumps.MenuItem(f"{val_s:.1f} s", callback=lambda s, v=val_s: self._select_max_silence_duration_action(s, v))
            self.menu_max_silence_duration_items[val_s] = item
            duration_submenu_items.append(item)

        self.menu_settings_submenu = rumps.MenuItem(MENU_OPEN_SETTINGS)
        self.menu_settings_submenu.add(rumps.MenuItem(MENU_SILENCE_THRESHOLD))
        self.menu_settings_submenu[MENU_SILENCE_THRESHOLD].update(threshold_submenu_items)
        self.menu_settings_submenu.add(rumps.MenuItem(MENU_MAX_SILENCE_DURATION))
        self.menu_settings_submenu[MENU_MAX_SILENCE_DURATION].update(duration_submenu_items)

        # --- Settings Submenu: Transcription Language ---
        self.menu_language_items = {}
        language_submenu_items = []
        for display_name, lang_code in TRANSCRIPTION_LANGUAGES.items():
            item = rumps.MenuItem(display_name, callback=lambda s, lc=lang_code: self._select_language_action(s, lc))
            self.menu_language_items[lang_code] = item # Use lang_code as key, including None
            language_submenu_items.append(item)
        self.menu_settings_submenu.add(rumps.MenuItem(MENU_TRANSCRIPTION_LANGUAGE))
        self.menu_settings_submenu[MENU_TRANSCRIPTION_LANGUAGE].update(language_submenu_items)

        # --- Settings Submenu: Beam Size ---
        self.menu_beam_size_items = {}
        beam_size_submenu_items = []
        for val_bs in BEAM_SIZES:
            item = rumps.MenuItem(str(val_bs), callback=lambda s, v=val_bs: self._select_beam_size_action(s, v))
            self.menu_beam_size_items[val_bs] = item
            beam_size_submenu_items.append(item)
        self.menu_settings_submenu.add(rumps.MenuItem(MENU_BEAM_SIZE))
        self.menu_settings_submenu[MENU_BEAM_SIZE].update(beam_size_submenu_items)
        
        # --- Settings Submenu: Temperature ---
        self.menu_temperature_items = {}
        temperature_submenu_items = []
        for val_temp in TEMPERATURE_VALUES:
            item = rumps.MenuItem(f"{val_temp:.1f}", callback=lambda s, v=val_temp: self._select_temperature_action(s, v))
            self.menu_temperature_items[val_temp] = item
            temperature_submenu_items.append(item)
        self.menu_settings_submenu.add(rumps.MenuItem(MENU_TEMPERATURE))
        self.menu_settings_submenu[MENU_TEMPERATURE].update(temperature_submenu_items)

        # --- Settings Submenu: Condition on Previous Text (Toggle) ---
        self.menu_condition_prev_text_toggle = rumps.MenuItem(MENU_CONDITION_ON_PREV_TEXT, callback=self._toggle_condition_on_prev_text_action)
        self.menu_settings_submenu.add(self.menu_condition_prev_text_toggle)
        
        # --- Settings Submenu: VAD Filter (Toggle) ---
        self.menu_vad_filter_toggle = rumps.MenuItem(MENU_VAD_FILTER, callback=self._toggle_vad_filter_action)
        self.menu_settings_submenu.add(self.menu_vad_filter_toggle)

        self.menu = [
            self.menu_record_stop,
            self.menu_model_selector,
            rumps.separator,
            (MENU_OUTPUT_ACTION, [
                self.menu_output_copy,
                self.menu_output_paste
            ]),
            rumps.separator,
            self.menu_settings_submenu,
            self.menu_check_permissions,
            rumps.separator,
            self.menu_quit
        ]
        self._update_output_action_menu() # Set initial checkmarks
        self._update_model_menu() # Set initial model checkmark
        self._update_silence_threshold_menu() # Set initial threshold checkmark
        self._update_max_silence_duration_menu() # Set initial duration checkmark
        self._update_language_menu()
        self._update_beam_size_menu()
        self._update_vad_filter_menu()
        self._update_temperature_menu()
        self._update_condition_on_prev_text_menu()

    def _setup_audio_recorder(self):
        # Validate and set the model *before* AudioRecorder uses it
        current_selected_model = self.config_manager.get_selected_model()
        default_model = self.config_manager._default_settings().get("selected_model", AVAILABLE_MODELS[0] if AVAILABLE_MODELS else "tiny")

        if current_selected_model not in AVAILABLE_MODELS:
            logger.warning(
                f"Loaded model '{current_selected_model}' from settings is not in available models {AVAILABLE_MODELS}. "
                f"Defaulting to '{default_model}'."
            )
            self.selected_model = default_model
            self.config_manager.set_setting("selected_model", self.selected_model)
        else:
            self.selected_model = current_selected_model
        
        # Use self.raw_microphone_status to make decisions
        if self.raw_microphone_status == AUTH_STATUS_DENIED or \
           self.raw_microphone_status == AUTH_STATUS_RESTRICTED:
            logger.warning(f"AudioRecorder setup: Microphone permission is denied or restricted (status: {self.raw_microphone_status}). AudioRecorder will not be initialized.")
            self.audio_recorder = None
            return

        # If status is AUTH_STATUS_AUTHORIZED or AUTH_STATUS_NOT_DETERMINED, proceed to initialize.
        # The AUTH_STATUS_NOT_DETERMINED case will trigger the system prompt when AudioRecorder initializes sounddevice.
        try:
            logger.info(f"Initializing AudioRecorder with model: {self.selected_model}. Mic status before init: {self.raw_microphone_status}")
            # This is where the system might prompt for microphone if status was 'not determined'
            self.audio_recorder = AudioRecorder(self.config_manager, transcription_callback=self.handle_transcription_output)
            logger.info("AudioRecorder initialized successfully.")
            # If successful, and if status *was* NotDetermined, it means user likely granted permission.
            # Re-fetch the raw status and update self.permissions_status[PERM_KEY_MICROPHONE]
            if self.raw_microphone_status == AUTH_STATUS_NOT_DETERMINED:
                self.raw_microphone_status = self.permissions_manager.check_microphone_permission() # Get fresh status
                self.permissions_status[PERM_KEY_MICROPHONE] = (self.raw_microphone_status == AUTH_STATUS_AUTHORIZED)
                logger.info(f"Mic permission status after AudioRecorder init (was NotDetermined): raw={self.raw_microphone_status}, granted_bool={self.permissions_status[PERM_KEY_MICROPHONE]}")

        except Exception as e:
            logger.critical(f"Failed to initialize AudioRecorder: {e}", exc_info=True)
            self.audio_recorder = None # Ensure it's None if init fails
            # Re-check and update the status as the failure might have changed it (e.g., from NotDetermined to Denied)
            self.raw_microphone_status = self.permissions_manager.check_microphone_permission()
            self.permissions_status[PERM_KEY_MICROPHONE] = (self.raw_microphone_status == AUTH_STATUS_AUTHORIZED)
            logger.info(f"Mic permission status after AudioRecorder init failure: raw={self.raw_microphone_status}, granted_bool={self.permissions_status[PERM_KEY_MICROPHONE]}")
            
            rumps.notification(
                title=APP_NAME, 
                subtitle="Audio System Problem", 
                message=f"Could not initialize audio recording. This might be a permission issue or a problem with your audio device."
            ) 

    def _setup_hotkey_manager(self):
        # This method will attempt to set up the hotkey manager and will update
        # self.permissions_status[PERM_KEY_INPUT_MONITORING] based on success/failure.
        self.hotkey_manager = None # Reset
        self.permissions_status[PERM_KEY_INPUT_MONITORING] = False # Assume failure until success

        if not self.audio_recorder:
            logger.error("Cannot initialize HotkeyManager because AudioRecorder is not available (likely due to missing microphone permission).")
            return

        try:
            temp_hotkey_manager = HotkeyManager(self.config_manager, self._handle_hotkey_toggle_recording)
            if temp_hotkey_manager.start_listening():
                self.hotkey_manager = temp_hotkey_manager
                self.permissions_status[PERM_KEY_INPUT_MONITORING] = True
                logger.info("HotkeyManager initialized and listening successfully.")
            else:
                logger.warning("HotkeyManager.start_listening() failed. Input Monitoring permission likely not granted or tap creation failed.")
                # self.permissions_status[PERM_KEY_INPUT_MONITORING] is already False
                rumps.notification(
                    title=APP_NAME, 
                    subtitle="Hotkey Activation Failed", 
                    message="Could not activate global hotkeys. Ensure 'Input Monitoring' is enabled and restart Ottotone if needed."
                )
        except Exception as e:
            logger.error(f"Failed to initialize or start HotkeyManager: {e}", exc_info=True)
            # self.permissions_status[PERM_KEY_INPUT_MONITORING] is already False
            rumps.notification(title=APP_NAME, subtitle="Hotkey Error", message="An error occurred setting up hotkeys. They will be disabled.")

if __name__ == '__main__':
    logger.info(f"Starting {APP_NAME}...")
    app = OttotoneApp()
    app.run()