"""Callback methods for menu components in Ottotone.

This module contains all the callback implementations that the menu components
will call when menu items are activated.
"""

import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class MenuCallbacks:
    """Mixin class providing menu callbacks for OttotoneApp.
    
    This class is intended to be mixed into OttotoneApp to provide
    all the callback methods needed by the menu components.
    """
    
    def _on_model_changed(self, model_name: str):
        """Handle model change event.
        
        Args:
            model_name: The new model name
        """
        logger.info(f"Model changed to: {model_name}")
        
        # Update the audio recorder with the new model
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            logger.info(f"Reloading audio recorder with new model: {model_name}")
            self.audio_recorder.reload_model()
    
    def _on_output_action_changed(self, action: str):
        """Handle output action change event.
        
        Args:
            action: The new output action
        """
        logger.info(f"Output action changed to: {action}")
        # No further action needed as the config is already updated
        # and the menu state is handled by the component
    
    def _on_silence_threshold_changed(self, threshold: float):
        """Handle silence threshold change event.
        
        Args:
            threshold: The new silence threshold in dB
        """
        logger.info(f"Silence threshold changed to: {threshold} dB")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_silence_duration_changed(self, duration: float):
        """Handle silence duration change event.
        
        Args:
            duration: The new silence duration in seconds
        """
        logger.info(f"Silence duration changed to: {duration} s")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_language_changed(self, language_code: str):
        """Handle language change event.
        
        Args:
            language_code: The new language code
        """
        logger.info(f"Language changed to: {language_code}")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_beam_size_changed(self, beam_size: int):
        """Handle beam size change event.
        
        Args:
            beam_size: The new beam size
        """
        logger.info(f"Beam size changed to: {beam_size}")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_vad_filter_changed(self, enabled: bool):
        """Handle VAD filter change event.
        
        Args:
            enabled: Whether VAD filter is enabled
        """
        logger.info(f"VAD filter {'enabled' if enabled else 'disabled'}")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_temperature_changed(self, temperature: float):
        """Handle temperature change event.
        
        Args:
            temperature: The new temperature
        """
        logger.info(f"Temperature changed to: {temperature}")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
    
    def _on_condition_on_prev_text_changed(self, enabled: bool):
        """Handle condition on previous text change event.
        
        Args:
            enabled: Whether condition on previous text is enabled
        """
        logger.info(f"Condition on previous text {'enabled' if enabled else 'disabled'}")
        
        # Update audio recorder if available
        if hasattr(self, 'audio_recorder') and self.audio_recorder:
            self.audio_recorder._load_transcription_parameters()
