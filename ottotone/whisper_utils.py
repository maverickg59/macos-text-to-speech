"""Whisper utilities for Ottotone.

This module provides utilities for working with faster-whisper without depending on PyAV.
It provides the audio processing functionality needed by faster-whisper using numpy directly.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def process_audio_data(audio_data, sample_rate=16000):
    """Process audio data for faster-whisper.
    
    Args:
        audio_data: numpy array containing audio samples
        sample_rate: target sample rate for faster-whisper
        
    Returns:
        Processed audio data as numpy float32 array at 16kHz
    """
    # Convert to mono if stereo
    if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
        audio_data = audio_data.mean(axis=1)
    
    # Ensure float32 format with values in [-1, 1]
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    
    # Normalize if needed
    max_value = np.max(np.abs(audio_data))
    if max_value > 0:
        audio_data = audio_data / max_value
    
    # Return processed audio data
    return audio_data

def prepare_audio_for_whisper(audio_data, original_sample_rate):
    """Prepare audio data for Whisper transcription.
    
    Whisper expects 16kHz mono audio in float32 format.
    
    Args:
        audio_data: numpy array containing audio samples
        original_sample_rate: sample rate of the audio data
        
    Returns:
        Prepared audio data as numpy float32 array at 16kHz
    """
    try:
        # Convert to mono and normalize
        processed_audio = process_audio_data(audio_data)
        
        # Resample to 16kHz if needed using numpy
        if original_sample_rate != 16000:
            # Simple resampling using numpy
            # For production use, consider a better resampling method
            duration = len(processed_audio) / original_sample_rate
            new_length = int(duration * 16000)
            indices = np.linspace(0, len(processed_audio) - 1, new_length)
            processed_audio = np.interp(indices, np.arange(len(processed_audio)), processed_audio)
            
        return processed_audio
    except Exception as e:
        logger.error(f"Error preparing audio for Whisper: {e}")
        return None
