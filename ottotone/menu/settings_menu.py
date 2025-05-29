"""Settings menu component for Ottotone."""

import logging
import rumps
from typing import Dict, List, Any, Callable, Optional, Tuple, Union

from .menu_manager import BaseMenuComponent, MenuManager
from ..config import AppConfig

logger = logging.getLogger(__name__)

# Menu constants
MENU_OPEN_SETTINGS = "Settings"
MENU_SILENCE_THRESHOLD = "Silence Threshold"
MENU_MAX_SILENCE_DURATION = "Max Silence Duration"
MENU_LANGUAGE = "Transcription Language"
MENU_BEAM_SIZE = "Beam Size"
MENU_VAD_FILTER = "Use Voice Activity Detection"
MENU_TEMPERATURE = "Temperature"
MENU_CONDITION_ON_PREV_TEXT = "Condition on Previous Text"

# Default values for settings
SILENCE_THRESHOLDS_DB = [-10.0, -20.0, -25.0, -30.0, -35.0, -40.0, -50.0]
MAX_SILENCE_DURATIONS_S = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 5.0, 10.0]
BEAM_SIZES = [1, 2, 3, 5, 8]
TEMPERATURES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# Default transcription languages
TRANSCRIPTION_LANGUAGES = {
    "Auto-detect": "auto",
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese": "zh"
}

class SettingsMenu(BaseMenuComponent):
    """Menu component for application settings.
    
    This component manages the settings menu items and handles
    all settings-related operations.
    
    Attributes:
        settings_callbacks: Dictionary of callbacks for different settings
    """
    
    def __init__(self, menu_manager: MenuManager, config: AppConfig, settings_callbacks: Optional[Dict[str, Callable]] = None):
        """Initialize the SettingsMenu component.
        
        Args:
            menu_manager: The parent MenuManager instance
            config: The application configuration
            settings_callbacks: Optional dictionary of callbacks for settings changes
        """
        super().__init__(menu_manager, config)
        self.settings_callbacks = settings_callbacks or {}
        
        # Main settings menu
        self.settings_menu_item = None
        
        # Submenu containers
        self.silence_threshold_items = {}
        self.max_silence_duration_items = {}
        self.language_items = {}
        self.beam_size_items = {}
        self.temperature_items = {}
        
        # Toggle menu items
        self.vad_filter_item = None
        self.condition_on_prev_text_item = None
    
    def get_menu_items(self) -> List[Any]:
        """Create and return settings menu items.
        
        Returns:
            A list containing the settings menu
        """
        # Create main settings menu
        self.settings_menu_item = rumps.MenuItem(MENU_OPEN_SETTINGS)
        
        # Create silence threshold submenu
        silence_threshold_menu = rumps.MenuItem(MENU_SILENCE_THRESHOLD)
        for val_db in SILENCE_THRESHOLDS_DB:
            item = rumps.MenuItem(
                f"{val_db:.1f} dB", 
                callback=lambda sender, v=val_db: self._on_silence_threshold_selected(sender, v)
            )
            self.silence_threshold_items[val_db] = item
            silence_threshold_menu.add(item)
        
        # Create max silence duration submenu
        max_silence_duration_menu = rumps.MenuItem(MENU_MAX_SILENCE_DURATION)
        for val_s in MAX_SILENCE_DURATIONS_S:
            item = rumps.MenuItem(
                f"{val_s:.1f} s", 
                callback=lambda sender, v=val_s: self._on_max_silence_duration_selected(sender, v)
            )
            self.max_silence_duration_items[val_s] = item
            max_silence_duration_menu.add(item)
        
        # Create language submenu
        language_menu = rumps.MenuItem(MENU_LANGUAGE)
        for display_name, lang_code in TRANSCRIPTION_LANGUAGES.items():
            item = rumps.MenuItem(
                display_name, 
                callback=lambda sender, code=lang_code: self._on_language_selected(sender, code)
            )
            self.language_items[lang_code] = item
            language_menu.add(item)
        
        # Create beam size submenu
        beam_size_menu = rumps.MenuItem(MENU_BEAM_SIZE)
        for size in BEAM_SIZES:
            item = rumps.MenuItem(
                str(size), 
                callback=lambda sender, s=size: self._on_beam_size_selected(sender, s)
            )
            self.beam_size_items[size] = item
            beam_size_menu.add(item)
        
        # Create temperature submenu
        temperature_menu = rumps.MenuItem(MENU_TEMPERATURE)
        for temp in TEMPERATURES:
            item = rumps.MenuItem(
                f"{temp:.1f}", 
                callback=lambda sender, t=temp: self._on_temperature_selected(sender, t)
            )
            self.temperature_items[temp] = item
            temperature_menu.add(item)
        
        # Create toggle menu items with explicit initial states
        self.vad_filter_item = rumps.MenuItem(
            MENU_VAD_FILTER, 
            callback=self._on_vad_filter_toggled
        )
        # Set initial state
        self.vad_filter_item.state = 1 if self.config.audio.get_vad_filter() else 0
        
        self.condition_on_prev_text_item = rumps.MenuItem(
            MENU_CONDITION_ON_PREV_TEXT, 
            callback=self._on_condition_on_prev_text_toggled
        )
        # Set initial state
        self.condition_on_prev_text_item.state = 1 if self.config.audio.get_condition_on_previous_text() else 0
        
        # Log initial states
        logger.debug(f"Initial VAD filter state: {self.vad_filter_item.state}")
        logger.debug(f"Initial condition on prev text state: {self.condition_on_prev_text_item.state}")
        
        # Add all submenus to the main settings menu directly
        self.settings_menu_item.add(silence_threshold_menu)
        self.settings_menu_item.add(max_silence_duration_menu)
        self.settings_menu_item.add(language_menu)
        self.settings_menu_item.add(beam_size_menu)
        self.settings_menu_item.add(temperature_menu)
        self.settings_menu_item.add(self.vad_filter_item)
        self.settings_menu_item.add(self.condition_on_prev_text_item)
        
        # Update menu state initially
        self.update_menu_state()
        
        return [self.settings_menu_item]
    
    def update_menu_state(self):
        """Update all settings menu states based on current configuration."""
        self._update_silence_threshold_state()
        self._update_max_silence_duration_state()
        self._update_language_state()
        self._update_beam_size_state()
        self._update_temperature_state()
        self._update_vad_filter_state()
        self._update_condition_on_prev_text_state()
    
    def _update_silence_threshold_state(self):
        """Update silence threshold menu checkmarks."""
        current_threshold = self.config.audio.get_silence_threshold_db()
        for threshold, item in self.silence_threshold_items.items():
            # Use explicit state values: 1 for checked, 0 for unchecked
            item.state = 1 if abs(threshold - current_threshold) < 0.1 else 0  # Use small epsilon for float comparison
    
    def _update_max_silence_duration_state(self):
        """Update max silence duration menu checkmarks."""
        current_duration = self.config.audio.get_silence_duration_seconds()
        for duration, item in self.max_silence_duration_items.items():
            # Use explicit state values: 1 for checked, 0 for unchecked
            item.state = 1 if abs(duration - current_duration) < 0.1 else 0  # Use small epsilon for float comparison
    
    def _update_language_state(self):
        """Update language menu checkmarks."""
        current_language = self.config.audio.get_language()
        for code, item in self.language_items.items():
            # Use explicit state values: 1 for checked, 0 for unchecked
            item.state = 1 if code == current_language else 0
    
    def _update_beam_size_state(self):
        """Update beam size menu checkmarks."""
        current_beam_size = self.config.audio.get_beam_size()
        for size, item in self.beam_size_items.items():
            # Use explicit state values: 1 for checked, 0 for unchecked
            item.state = 1 if size == current_beam_size else 0
    
    def _update_temperature_state(self):
        """Update temperature menu checkmarks."""
        current_temp = self.config.audio.get_temperature()
        
        # Use a much smaller epsilon (0.01) for float comparison since we have temperatures at 0.1 increments
        epsilon = 0.01
        
        # First, uncheck all items
        for item in self.temperature_items.values():
            item.state = 0
            
        # Find exact match or closest temperature if no exact match
        if current_temp in self.temperature_items:
            # Exact match found
            self.temperature_items[current_temp].state = 1
        else:
            # Find closest match
            closest_temp = min(self.temperature_items.keys(), key=lambda x: abs(x - current_temp))
            if abs(closest_temp - current_temp) < epsilon:
                self.temperature_items[closest_temp].state = 1
                
        logger.debug(f"Updated temperature menu state to match {current_temp}")
        
    
    def _update_vad_filter_state(self):
        """Update VAD filter toggle state."""
        if self.vad_filter_item:
            # Use explicit state values: 1 for checked, 0 for unchecked
            self.vad_filter_item.state = 1 if self.config.audio.get_vad_filter() else 0
    
    def _update_condition_on_prev_text_state(self):
        """Update condition on previous text toggle state."""
        if self.condition_on_prev_text_item:
            # Use explicit state values: 1 for checked, 0 for unchecked
            self.condition_on_prev_text_item.state = 1 if self.config.audio.get_condition_on_previous_text() else 0
    
    def _on_silence_threshold_selected(self, sender: rumps.MenuItem, threshold: float):
        """Handle silence threshold selection.
        
        Args:
            sender: The menu item that was clicked
            threshold: The selected threshold value in dB
        """
        current_threshold = self.config.audio.get_silence_threshold_db()
        
        if abs(threshold - current_threshold) >= 0.1:  # Only update if value changed
            logger.info(f"Changing silence threshold from {current_threshold} to {threshold} dB")
            
            # Update configuration
            self.config.audio.set_silence_threshold_db(threshold)
            
            # Update menu state
            self._update_silence_threshold_state()
            
            # Notify listeners if callback is provided
            if "silence_threshold" in self.settings_callbacks:
                self.settings_callbacks["silence_threshold"](threshold)
    
    def _on_max_silence_duration_selected(self, sender: rumps.MenuItem, duration: float):
        """Handle max silence duration selection.
        
        Args:
            sender: The menu item that was clicked
            duration: The selected duration value in seconds
        """
        current_duration = self.config.audio.get_silence_duration_seconds()
        
        if abs(duration - current_duration) >= 0.1:  # Only update if value changed
            logger.info(f"Changing max silence duration from {current_duration} to {duration} s")
            
            # Update configuration
            self.config.audio.set_silence_duration_seconds(duration)
            
            # Update menu state
            self._update_max_silence_duration_state()
            
            # Notify listeners if callback is provided
            if "silence_duration" in self.settings_callbacks:
                self.settings_callbacks["silence_duration"](duration)
    
    def _on_language_selected(self, sender: rumps.MenuItem, language_code: str):
        """Handle language selection.
        
        Args:
            sender: The menu item that was clicked
            language_code: The selected language code
        """
        current_language = self.config.audio.get_language()
        
        if language_code != current_language:
            logger.info(f"Changing language from {current_language} to {language_code}")
            
            # Update configuration
            self.config.audio.set_language(language_code)
            
            # Update menu state
            self._update_language_state()
            
            # Notify listeners if callback is provided
            if "language" in self.settings_callbacks:
                self.settings_callbacks["language"](language_code)
    
    def _on_beam_size_selected(self, sender: rumps.MenuItem, beam_size: int):
        """Handle beam size selection.
        
        Args:
            sender: The menu item that was clicked
            beam_size: The selected beam size
        """
        current_beam_size = self.config.audio.get_beam_size()
        
        if beam_size != current_beam_size:
            logger.info(f"Changing beam size from {current_beam_size} to {beam_size}")
            
            # Update configuration
            self.config.audio.set_beam_size(beam_size)
            
            # Update menu state
            self._update_beam_size_state()
            
            # Notify listeners if callback is provided
            if "beam_size" in self.settings_callbacks:
                self.settings_callbacks["beam_size"](beam_size)
    
    def _on_temperature_selected(self, sender: rumps.MenuItem, temperature: float):
        """Handle temperature selection.
        
        Args:
            sender: The menu item that was clicked
            temperature: The selected temperature
        """
        current_temp = self.config.audio.get_temperature()
        
        if abs(temperature - current_temp) >= 0.1:  # Only update if value changed
            logger.info(f"Changing temperature from {current_temp} to {temperature}")
            
            # Update configuration
            self.config.audio.set_temperature(temperature)
            
            # Update menu state
            self._update_temperature_state()
            
            # Notify listeners if callback is provided
            if "temperature" in self.settings_callbacks:
                self.settings_callbacks["temperature"](temperature)
    
    def _on_vad_filter_toggled(self, sender: rumps.MenuItem):
        """Handle VAD filter toggle.
        
        Args:
            sender: The menu item that was clicked
        """
        current_state = self.config.audio.get_vad_filter()
        new_state = not current_state
        
        logger.info(f"Toggling VAD filter from {current_state} to {new_state}")
        
        # Update configuration
        self.config.audio.set_vad_filter(new_state)
        
        # Directly update the SENDER's state - this is crucial for visual feedback
        sender.state = 1 if new_state else 0
        logger.debug(f"VAD filter menu item state set to: {sender.state}")
        
        # Also update our stored reference if different from sender
        if self.vad_filter_item and self.vad_filter_item is not sender:
            self.vad_filter_item.state = 1 if new_state else 0
        
        # Notify listeners if callback is provided
        if "vad_filter" in self.settings_callbacks:
            self.settings_callbacks["vad_filter"](new_state)
    
    def _on_condition_on_prev_text_toggled(self, sender: rumps.MenuItem):
        """Handle condition on previous text toggle.
        
        Args:
            sender: The menu item that was clicked
        """
        current_state = self.config.audio.get_condition_on_previous_text()
        new_state = not current_state
        
        logger.info(f"Toggling condition on previous text from {current_state} to {new_state}")
        
        # Update configuration
        self.config.audio.set_condition_on_previous_text(new_state)
        
        # Directly update the SENDER's state - this is crucial for visual feedback
        sender.state = 1 if new_state else 0
        logger.debug(f"Condition on previous text menu item state set to: {sender.state}")
        
        # Also update our stored reference if different from sender
        if self.condition_on_prev_text_item and self.condition_on_prev_text_item is not sender:
            self.condition_on_prev_text_item.state = 1 if new_state else 0
        
        # Notify listeners if callback is provided
        if "condition_on_previous_text" in self.settings_callbacks:
            self.settings_callbacks["condition_on_previous_text"](new_state)
