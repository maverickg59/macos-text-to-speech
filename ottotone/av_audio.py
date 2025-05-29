"""PyAudio-based audio capture for Ottotone.

This module provides macOS audio recording capabilities using PyAudio.
It provides a reliable way to access the microphone with a simple interface.
"""

import time
import logging
import numpy as np
import pyaudio
from typing import Callable, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class AVAudioCapture:
    """Audio capture implementation using PyAudio.
    
    This class provides an interface for capturing audio from the device microphone
    that is compatible with the sounddevice interface used by AudioRecorder.
    """
    
    def __init__(
        self,
        samplerate: float = 16000.0,
        channels: int = 1,
        device: Union[int, str, None] = None,
        callback: Optional[Callable] = None,
    ):
        """Initialize audio capture with the given parameters.
        
        Args:
            samplerate: Sample rate for audio capture in Hz
            channels: Number of audio channels (1 for mono, 2 for stereo)
            device: Device name or ID (device index for PyAudio)
            callback: Function to call with audio data
        """
        self.sample_rate = float(samplerate)
        self.channels = int(channels)
        self.device = device
        self.callback = callback
        self.is_recording = False
        
        # PyAudio objects
        self._py_audio = None
        self._stream = None
        
        # Format parameters
        self._format = pyaudio.paFloat32  # Use 32-bit float format
        self._frames_per_buffer = 1024    # Buffer size
        
        logger.info(f"Initialized PyAudio capture: rate={self.sample_rate}, channels={self.channels}")
    
    def _get_device_index(self) -> int:
        """Get the device index for the specified device.
        
        Returns:
            int: Device index to use with PyAudio
        """
        # If device is specified as an integer, use it directly
        if isinstance(self.device, int):
            return self.device
            
        # If device is specified as a string, try to find matching device
        if isinstance(self.device, str) and self._py_audio:
            info = self._py_audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            # Iterate through devices to find a name match
            for i in range(num_devices):
                device_info = self._py_audio.get_device_info_by_index(i)
                if (device_info.get('maxInputChannels') > 0 and 
                    self.device.lower() in device_info.get('name').lower()):
                    return i
        
        # Default to default input device
        return pyaudio.paNoDevice  # Will use system default
    
    def _get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the selected audio device.
        
        Returns:
            Optional[Dict[str, Any]]: Device information or None if not available
        """
        try:
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
                
            device_index = self._get_device_index()
            if device_index == pyaudio.paNoDevice:
                # Get default input device
                device_index = self._py_audio.get_default_input_device_info().get('index')
                
            # Get device info
            device_info = self._py_audio.get_device_info_by_index(device_index)
            
            # Format into a consistent dictionary
            info = {
                'name': device_info.get('name'),
                'sample_rate': device_info.get('defaultSampleRate'),
                'channels': device_info.get('maxInputChannels'),
                'index': device_index
            }
            
            return info
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return None
    
    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for PyAudio stream.
        
        This is called by PyAudio when audio data is available.
        We convert the raw bytes to numpy array and call the user's callback.
        
        Args:
            in_data: Raw audio data as bytes
            frame_count: Number of frames in the buffer
            time_info: Timing information
            status: Status flags from PyAudio
            
        Returns:
            tuple: (None, paContinue) to continue recording
        """
        try:
            if self.callback and self.is_recording:
                # Convert bytes to numpy array (assuming float32 format)
                audio_data = np.frombuffer(in_data, dtype=np.float32)
                
                # Call the user's callback with the data
                # The AudioRecorder expects (indata, frame_count, time_info, status)
                callback_time_info = {'current_time': time.time()}
                self.callback(audio_data, frame_count, callback_time_info, status)
                
            # Return None to indicate we didn't modify the data, and paContinue to continue
            return (None, pyaudio.paContinue)
        except Exception as e:
            logger.error(f"Error in PyAudio callback: {e}")
            return (None, pyaudio.paContinue)
    
    def start(self) -> bool:
        """Start audio recording.
        
        Returns:
            bool: True if started successfully
        """
        try:
            if self.is_recording:
                logger.warning("Recording already in progress")
                return True
            
            # Initialize PyAudio if needed
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
            
            # Get device info to log
            device_info = self._get_device_info()
            device_index = device_info.get('index') if device_info else None
            device_name = device_info.get('name') if device_info else "Default microphone"
            
            logger.info(f"Starting audio recording from device: {device_name} (index: {device_index})")
            
            # Open a stream for recording
            self._stream = self._py_audio.open(
                format=self._format,
                channels=self.channels,
                rate=int(self.sample_rate),
                input=True,
                output=False,
                input_device_index=device_index,
                frames_per_buffer=self._frames_per_buffer,
                stream_callback=self._pyaudio_callback
            )
            
            # Start the stream
            self._stream.start_stream()
            
            # Mark as recording
            self.is_recording = True
            
            logger.info("PyAudio recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting audio capture: {e}", exc_info=True)
            return False
    
    def stop(self) -> bool:
        """Stop audio recording.
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            if not self.is_recording:
                logger.debug("Recording already stopped.")
                return True
                
            logger.debug("Stopping PyAudio recording")
            
            # Stop and close the stream
            if self._stream:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
                self._stream = None
                logger.debug("Audio stream stopped and closed")
            
            # Reset recording flag
            self.is_recording = False
                
            logger.info("Audio capture stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")
            return False
    
    def close(self) -> None:
        """Close the audio stream and release resources.
        
        This method is provided for compatibility with the sounddevice interface.
        It ensures proper cleanup of resources when the audio recorder is stopped.
        """
        try:
            # Ensure recording is stopped
            if self.is_recording:
                self.stop()
                
            # Clean up PyAudio
            if self._py_audio:
                self._py_audio.terminate()
                self._py_audio = None
                logger.debug("PyAudio terminated and resources released")
                    
        except Exception as e:
            logger.error(f"Error closing audio resources: {e}")
            # Don't raise exception to maintain compatibility with sounddevice interface
        
        # Format parameters
        self._format = pyaudio.paFloat32  # Use 32-bit float format
        self._frames_per_buffer = 1024    # Buffer size
        
        logger.info(f"Initialized PyAudio capture: rate={self.sample_rate}, channels={self.channels}")
    
    def _get_device_index(self) -> int:
        """Get the device index for the specified device.
        
        Returns:
            int: Device index to use with PyAudio
        """
        # If device is specified as an integer, use it directly
        if isinstance(self.device, int):
            return self.device
            
        # If device is specified as a string, try to find matching device
        if isinstance(self.device, str) and self._py_audio:
            info = self._py_audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            # Iterate through devices to find a name match
            for i in range(num_devices):
                device_info = self._py_audio.get_device_info_by_index(i)
                if (device_info.get('maxInputChannels') > 0 and 
                    self.device.lower() in device_info.get('name').lower()):
                    return i
        
        # Default to default input device
        return pyaudio.paNoDevice  # Will use system default
    
    def _get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the selected audio device.
        
        Returns:
            Optional[Dict[str, Any]]: Device information or None if not available
        """
        try:
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
                
            device_index = self._get_device_index()
            if device_index == pyaudio.paNoDevice:
                # Get default input device
                device_index = self._py_audio.get_default_input_device_info().get('index')
                
            # Get device info
            device_info = self._py_audio.get_device_info_by_index(device_index)
            
            # Format into a consistent dictionary
            info = {
                'name': device_info.get('name'),
                'sample_rate': device_info.get('defaultSampleRate'),
                'channels': device_info.get('maxInputChannels'),
                'index': device_index
            }
            
            return info
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return None
    
    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for PyAudio stream.
        
        This is called by PyAudio when audio data is available.
        We convert the raw bytes to numpy array and call the user's callback.
        
        Args:
            in_data: Raw audio data as bytes
            frame_count: Number of frames in the buffer
            time_info: Timing information
            status: Status flags from PyAudio
            
        Returns:
            tuple: (None, paContinue) to continue recording
        """
        try:
            if self.callback and self.is_recording:
                # Convert bytes to numpy array (assuming float32 format)
                audio_data = np.frombuffer(in_data, dtype=np.float32)
                
                # Call the user's callback with the data
                # The AudioRecorder expects (indata, frame_count, time_info, status)
                callback_time_info = {'current_time': time.time()}
                self.callback(audio_data, frame_count, callback_time_info, status)
                
            # Return None to indicate we didn't modify the data, and paContinue to continue
            return (None, pyaudio.paContinue)
        except Exception as e:
            logger.error(f"Error in PyAudio callback: {e}")
            return (None, pyaudio.paContinue)
    
    def start(self) -> bool:
        """Start audio recording.
        
        Returns:
            bool: True if started successfully
        """
        try:
            if self.is_recording:
                logger.warning("Recording already in progress")
                return True
            
            # Initialize PyAudio if needed
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
            
            # Get device info to log
            device_info = self._get_device_info()
            device_index = device_info.get('index') if device_info else None
            device_name = device_info.get('name') if device_info else "Default microphone"
            
            logger.info(f"Starting audio recording from device: {device_name} (index: {device_index})")
            
            # Open a stream for recording
            self._stream = self._py_audio.open(
                format=self._format,
                channels=self.channels,
                rate=int(self.sample_rate),
                input=True,
                output=False,
                input_device_index=device_index,
                frames_per_buffer=self._frames_per_buffer,
                stream_callback=self._pyaudio_callback
            )
            
            # Start the stream
            self._stream.start_stream()
            
            # Mark as recording
            self.is_recording = True
            
            logger.info("PyAudio recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting audio capture: {e}", exc_info=True)
            return False
    
    def stop(self) -> bool:
        """Stop audio recording.
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            if not self.is_recording:
                logger.debug("Recording already stopped.")
                return True
                
            logger.debug("Stopping PyAudio recording")
            
            # Stop and close the stream
            if self._stream:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
                self._stream = None
                logger.debug("Audio stream stopped and closed")
            
            # Reset recording flag
            self.is_recording = False
                
            logger.info("Audio capture stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")
            return False
    
    def close(self) -> None:
        """Close the audio stream and release resources.
        
        This method is provided for compatibility with the sounddevice interface.
        It ensures proper cleanup of resources when the audio recorder is stopped.
        """
        try:
            # Ensure recording is stopped
            if self.is_recording:
                self.stop()
                
            # Clean up PyAudio
            if self._py_audio:
                self._py_audio.terminate()
                self._py_audio = None
                logger.debug("PyAudio terminated and resources released")
                    
        except Exception as e:
            logger.error(f"Error closing audio resources: {e}")
            # Don't raise exception to maintain compatibility with sounddevice interface
    
    def get_default_device_info(self) -> Dict[str, Any]:
        """Get information about the default audio device.
        
        Returns:
            Dict with device information
        """
        try:
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
            
            # Get the default input device info
            device_info = self._py_audio.get_default_input_device_info()
            
            return {
                'name': device_info.get('name', 'Default System Device'),
                'manufacturer': 'Unknown',  # PyAudio doesn't provide this info
                'unique_id': str(device_info.get('index', 0)),
                'is_connected': True,  # Assume connected
                'default_samplerate': device_info.get('defaultSampleRate', self.sample_rate)
            }
        except Exception as e:
            logger.error(f"Error getting default device info: {e}")
            return {
                'name': "Default System Device",
                'error': str(e),
                'default_samplerate': self.sample_rate
            }
    
    def query_devices(self, kind='input'):
        """Query available audio devices.
        
        Args:
            kind: 'input' or 'output'
            
        Returns:
            List of available device info dictionaries
        """
        try:
            # Initialize PyAudio if needed
            if not self._py_audio:
                self._py_audio = pyaudio.PyAudio()
                
            # For compatibility with sounddevice API
            if kind != 'input' and kind != 'all':
                return []  # Only handle input devices if specified
                
            devices = []
            
            # Get the PyAudio host API info
            host_api_info = self._py_audio.get_host_api_info_by_index(0)
            device_count = host_api_info.get('deviceCount', 0)
            default_input_device = host_api_info.get('defaultInputDevice', -1)
            
            # Iterate through all devices
            for i in range(device_count):
                device_info = self._py_audio.get_device_info_by_index(i)
                
                # Check if it's an input device (or if we want all devices)
                is_input = device_info.get('maxInputChannels', 0) > 0
                if kind == 'input' and not is_input:
                    continue  # Skip non-input devices when only input requested
                
                # Format the device info
                formatted_info = {
                    'name': device_info.get('name', f'Device {i}'),
                    'unique_id': str(i),
                    'default_samplerate': device_info.get('defaultSampleRate', self.sample_rate),
                    'is_default': (i == default_input_device),
                    'max_input_channels': device_info.get('maxInputChannels', 0),
                    'max_output_channels': device_info.get('maxOutputChannels', 0),
                }
                
                devices.append(formatted_info)
            
            return devices
        except Exception as e:
            logger.error(f"Error querying devices: {e}")
            return [{
                'name': "Default System Device",
                'error': str(e),
                'default_samplerate': self.sample_rate,
                'is_default': True
            }]


def create_input_stream(samplerate=44100, channels=1, callback=None, **kwargs):
    """Create an input stream compatible with sounddevice API.
    
    This function provides a compatibility layer for the AudioRecorder class.
    
    Args:
        samplerate: Sample rate in Hz
        channels: Number of channels
        callback: Function to call with audio data
        **kwargs: Additional arguments (ignored for compatibility)
        
    Returns:
        AVAudioCapture instance with start/stop methods
    """
    return AVAudioCapture(callback=callback, channels=channels, samplerate=samplerate)


def query_devices(device=None, kind=None):
    """Query audio devices for compatibility with sounddevice.
    
    Args:
        device: Device ID or name (optional)
        kind: 'input' or 'output' (optional)
        
    Returns:
        Device info dictionary or list
    """
    capture = AVAudioCapture()
    if device is None:
        return capture.query_devices(kind=kind if kind else 'input')
    else:
        return capture.get_default_device_info()
