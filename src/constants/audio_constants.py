"""Audio-related constants for Ottotone.

This module contains constants related to audio recording, transcription,
and Whisper model configuration.
"""

# Available Whisper models
AVAILABLE_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2"]
DEFAULT_WHISPER_MODEL = "base"

# Audio recording constants
DEFAULT_SILENCE_THRESHOLD_DB = -30.0  # Default silence threshold in dB
DEFAULT_SILENCE_DURATION = 2.0  # Default silence duration in seconds (renamed from SECONDS for consistency)
DEFAULT_MIN_RECORDING_TIME = 0.5  # Minimum recording time in seconds

# Audio state constants
AUDIO_STATE_IDLE = "IDLE"
AUDIO_STATE_WAITING_FOR_SPEECH = "WAITING_FOR_SPEECH"
AUDIO_STATE_SPEECH_DETECTED = "SPEECH_DETECTED"

# Whisper model device and compute constants
WHISPER_DEVICE_CPU = "cpu"  # Force CPU mode (MPS not supported by faster-whisper)
WHISPER_COMPUTE_INT8 = "int8"  # Compute type for model

# Transcription parameters
DEFAULT_LANGUAGE = "en"  # Default language code
DEFAULT_BEAM_SIZE = 5  # Default beam size
DEFAULT_VAD_FILTER = True  # Default VAD filter setting
DEFAULT_TEMPERATURE = 0.0  # Default temperature
DEFAULT_CONDITION_ON_PREVIOUS_TEXT = True  # Default condition on previous text setting

# Transcription languages map
TRANSCRIPTION_LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Russian": "ru",
    "Auto-detect": "auto"
}
