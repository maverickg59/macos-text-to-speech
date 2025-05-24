"""Audio configuration management for Ottotone."""

import os
import appdirs
import logging

from .base import ConfigStorageManager, APP_NAME, APP_AUTHOR

logger = logging.getLogger(__name__)

class AudioConfig:
    """Manages audio recording and transcription settings.
    
    Responsibilities:
    - Manage silence detection parameters
    - Configure transcription model settings
    - Handle VAD (Voice Activity Detection) parameters
    """
    
    NAMESPACE = "audio"
    
    # Default values
    DEFAULT_SILENCE_THRESHOLD_DB = -30.0
    DEFAULT_SILENCE_DURATION_SECONDS = 2.0
    DEFAULT_SELECTED_MODEL = "tiny"
    DEFAULT_COMPUTE_TYPE = "int8"  # Always use int8 for CPU compatibility
    DEFAULT_LANGUAGE = "en"
    DEFAULT_BEAM_SIZE = 1
    DEFAULT_VAD_FILTER = True
    DEFAULT_TEMPERATURE = 0.0
    DEFAULT_PATIENCE = 1.0
    DEFAULT_CONDITION_ON_PREVIOUS_TEXT = False
    
    def __init__(self, storage_manager):
        """Initialize with a ConfigStorageManager instance.
        
        Args:
            storage_manager: ConfigStorageManager instance for persistence
        """
        self.storage_manager = storage_manager
        
        # Initialize with defaults if needed
        if not self.storage_manager.get_setting(f"{self.NAMESPACE}"):
            self._init_default_settings()
    
    def _init_default_settings(self):
        """Initialize default audio settings."""
        default_settings = {
            "silence_threshold_db": self.DEFAULT_SILENCE_THRESHOLD_DB,
            "silence_duration_seconds": self.DEFAULT_SILENCE_DURATION_SECONDS,
            "selected_model": self.DEFAULT_SELECTED_MODEL,
            "models_path": os.path.join(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR), "models"),
            "compute_type": self.DEFAULT_COMPUTE_TYPE,
            "transcription": {
                "language": self.DEFAULT_LANGUAGE,
                "beam_size": self.DEFAULT_BEAM_SIZE,
                "vad_filter": self.DEFAULT_VAD_FILTER,
                "vad_parameters": {
                    "min_silence_duration_ms": 250,
                    "threshold": 0.35
                },
                "temperature": self.DEFAULT_TEMPERATURE,
                "patience": self.DEFAULT_PATIENCE,
                "condition_on_previous_text": self.DEFAULT_CONDITION_ON_PREVIOUS_TEXT
            }
        }
        
        self.storage_manager.set_setting(self.NAMESPACE, default_settings)
    
    def _get_audio_setting(self, key, default=None):
        """Get a setting from the audio namespace.
        
        Args:
            key: Setting key within the audio namespace
            default: Default value if not found
            
        Returns:
            The setting value or default
        """
        audio_settings = self.storage_manager.get_setting(self.NAMESPACE, {})
        return audio_settings.get(key, default)
    
    def _set_audio_setting(self, key, value):
        """Set a setting in the audio namespace.
        
        Args:
            key: Setting key within the audio namespace
            value: Value to set
        """
        audio_settings = self.storage_manager.get_setting(self.NAMESPACE, {})
        audio_settings[key] = value
        self.storage_manager.set_setting(self.NAMESPACE, audio_settings)
    
    def _get_transcription_setting(self, key, default=None):
        """Get a setting from the transcription namespace.
        
        Args:
            key: Setting key within the transcription namespace
            default: Default value if not found
            
        Returns:
            The setting value or default
        """
        transcription = self._get_audio_setting("transcription", {})
        return transcription.get(key, default)
    
    def _set_transcription_setting(self, key, value):
        """Set a setting in the transcription namespace.
        
        Args:
            key: Setting key within the transcription namespace
            value: Value to set
        """
        transcription = self._get_audio_setting("transcription", {})
        transcription[key] = value
        self._set_audio_setting("transcription", transcription)
    
    # Silence threshold methods
    def get_silence_threshold_db(self):
        """Get the silence threshold in decibels."""
        return self._get_audio_setting("silence_threshold_db", self.DEFAULT_SILENCE_THRESHOLD_DB)
    
    def set_silence_threshold_db(self, value):
        """Set the silence threshold in decibels."""
        self._set_audio_setting("silence_threshold_db", float(value))
    
    # Silence duration methods
    def get_silence_duration_seconds(self):
        """Get the silence duration in seconds."""
        return self._get_audio_setting("silence_duration_seconds", self.DEFAULT_SILENCE_DURATION_SECONDS)
    
    def set_silence_duration_seconds(self, value):
        """Set the silence duration in seconds."""
        duration = float(value)
        self._set_audio_setting("silence_duration_seconds", duration)
        
        # Update the VAD parameters to be consistent with silence duration
        # Only if VAD filter is enabled
        if self.get_vad_filter():
            vad_params = self.get_vad_parameters()
            # Convert seconds to milliseconds and use a smaller value for VAD than manual detection
            vad_params["min_silence_duration_ms"] = min(250, int(duration * 1000 / 4))
            self.set_vad_parameters(vad_params)
    
    # Model selection methods
    def get_selected_model(self):
        """Get the selected whisper model name."""
        return self._get_audio_setting("selected_model", self.DEFAULT_SELECTED_MODEL)
    
    def set_selected_model(self, model_name):
        """Set the selected whisper model name."""
        self._set_audio_setting("selected_model", model_name)
    
    # Models path methods
    def get_models_path(self):
        """Get the path where models are stored."""
        default_path = os.path.join(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR), "models")
        return self._get_audio_setting("models_path", default_path)
    
    def set_models_path(self, path):
        """Set the path where models are stored."""
        self._set_audio_setting("models_path", path)
    
    # Compute type methods
    def get_compute_type(self):
        """Get the compute type for the model."""
        return self._get_audio_setting("compute_type", self.DEFAULT_COMPUTE_TYPE)
    
    def set_compute_type(self, compute_type):
        """Set the compute type for the model."""
        self._set_audio_setting("compute_type", compute_type)
    
    # Transcription language methods
    def get_language(self):
        """Get the transcription language."""
        return self._get_transcription_setting("language", self.DEFAULT_LANGUAGE)
    
    def set_language(self, language):
        """Set the transcription language."""
        self._set_transcription_setting("language", language)
    
    # Beam size methods
    def get_beam_size(self):
        """Get the beam size for transcription."""
        return self._get_transcription_setting("beam_size", self.DEFAULT_BEAM_SIZE)
    
    def set_beam_size(self, beam_size):
        """Set the beam size for transcription."""
        self._set_transcription_setting("beam_size", int(beam_size))
    
    # VAD filter methods
    def get_vad_filter(self):
        """Get whether VAD filter is enabled."""
        return self._get_transcription_setting("vad_filter", self.DEFAULT_VAD_FILTER)
    
    def set_vad_filter(self, enabled):
        """Set whether VAD filter is enabled."""
        self._set_transcription_setting("vad_filter", bool(enabled))
    
    # VAD parameters methods
    def get_vad_parameters(self):
        """Get VAD parameters."""
        default_params = {
            "min_silence_duration_ms": 250,
            "threshold": 0.35
        }
        return self._get_transcription_setting("vad_parameters", default_params)
    
    def set_vad_parameters(self, params):
        """Set VAD parameters."""
        self._set_transcription_setting("vad_parameters", params)
    
    # Temperature methods
    def get_temperature(self):
        """Get the temperature for transcription."""
        return self._get_transcription_setting("temperature", self.DEFAULT_TEMPERATURE)
    
    def set_temperature(self, temperature):
        """Set the temperature for transcription."""
        self._set_transcription_setting("temperature", float(temperature))
    
    # Patience methods
    def get_patience(self):
        """Get the patience value for transcription."""
        return self._get_transcription_setting("patience", self.DEFAULT_PATIENCE)
    
    def set_patience(self, patience):
        """Set the patience value for transcription."""
        self._set_transcription_setting("patience", float(patience))
    
    # Condition on previous text methods
    def get_condition_on_previous_text(self):
        """Get whether to condition on previous text."""
        return self._get_transcription_setting("condition_on_previous_text", 
                                             self.DEFAULT_CONDITION_ON_PREVIOUS_TEXT)
    
    def set_condition_on_previous_text(self, enabled):
        """Set whether to condition on previous text."""
        self._set_transcription_setting("condition_on_previous_text", bool(enabled))
    
    def get_all_transcription_parameters(self):
        """Get all transcription parameters as a dictionary.
        
        Returns:
            Dictionary with all transcription parameters
        """
        return {
            "language": self.get_language(),
            "beam_size": self.get_beam_size(),
            "vad_filter": self.get_vad_filter(),
            "vad_parameters": self.get_vad_parameters(),
            "temperature": self.get_temperature(),
            "patience": self.get_patience(),
            "condition_on_previous_text": self.get_condition_on_previous_text()
        }
