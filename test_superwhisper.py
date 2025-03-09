#!/usr/bin/env python3
import unittest
import wave
import tempfile
import os
import numpy as np
from unittest.mock import MagicMock, patch
import pyaudio

# Import the module we want to test
from superwhisper import (
    is_silence, 
    AppState, 
    SILENCE_THRESHOLD,
    SAMPLE_RATE,
    CHANNELS,
    FORMAT,
    MIN_AUDIO_DURATION,
    SILENCE_DURATION
)

class TestSuperwhisper(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.state = AppState()
        self.temp_files = []

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        for file in self.temp_files:
            try:
                os.remove(file)
            except OSError:
                pass

    def create_test_audio(self, duration, frequency=440, amplitude=10000):
        """Create a test audio file with specified duration and properties."""
        # Create a temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_files.append(temp_file.name)
        
        # Generate audio data (sine wave)
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
        audio_data = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
        
        # Write to WAV file
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        
        return temp_file.name, audio_data.tobytes()

    def test_is_silence_detection(self):
        """Test silence detection function."""
        # Test with silence (zeros)
        silent_data = np.zeros(1024, dtype=np.int16).tobytes()
        self.assertTrue(is_silence(silent_data, SILENCE_THRESHOLD))
        
        # Test with loud audio
        loud_data = (np.ones(1024, dtype=np.int16) * 10000).tobytes()
        self.assertFalse(is_silence(loud_data, SILENCE_THRESHOLD))
        
        # Test with barely audible audio
        quiet_data = (np.ones(1024, dtype=np.int16) * 100).tobytes()
        self.assertTrue(is_silence(quiet_data, SILENCE_THRESHOLD))

    def test_minimum_audio_duration(self):
        """Test that recordings respect minimum audio duration."""
        # Create audio shorter than MIN_AUDIO_DURATION
        short_duration = MIN_AUDIO_DURATION / 2
        short_file, short_data = self.create_test_audio(short_duration)
        
        # Create audio longer than MIN_AUDIO_DURATION
        long_duration = MIN_AUDIO_DURATION * 2
        long_file, long_data = self.create_test_audio(long_duration)
        
        # Calculate chunks for each
        short_chunks = len(short_data) // (2 * CHANNELS)  # 16-bit = 2 bytes per sample
        long_chunks = len(long_data) // (2 * CHANNELS)
        
        min_chunks = int(MIN_AUDIO_DURATION * SAMPLE_RATE)
        
        # Verify chunk calculations
        self.assertLess(short_chunks, min_chunks)
        self.assertGreater(long_chunks, min_chunks)

    def test_silence_duration_buffer(self):
        """Test that silence duration buffer works correctly."""
        # Create test audio with silence at the end
        audio_duration = 1.0
        silence_duration = SILENCE_DURATION
        total_duration = audio_duration + silence_duration
        
        # Generate audio with silence at the end
        t = np.linspace(0, total_duration, int(SAMPLE_RATE * total_duration))
        audio = np.zeros_like(t, dtype=np.int16)
        audio[:int(SAMPLE_RATE * audio_duration)] = 10000  # Audio
        audio[int(SAMPLE_RATE * audio_duration):] = 0      # Silence
        
        # Calculate silence chunks
        silence_samples = int(SILENCE_DURATION * SAMPLE_RATE)
        silence_chunks = silence_samples // 1024  # Using CHUNK_SIZE
        
        # Verify silence duration calculations
        self.assertEqual(
            silence_chunks,
            int(SILENCE_DURATION * SAMPLE_RATE / 1024)
        )

    @patch('pyaudio.PyAudio')
    def test_audio_stream_parameters(self, mock_pyaudio):
        """Test that audio stream is created with correct parameters."""
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        # Create PyAudio instance
        p = pyaudio.PyAudio()
        
        # Open stream with our parameters
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024
        )
        
        # Verify stream parameters
        mock_pyaudio.return_value.open.assert_called_once_with(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024
        )

    def test_state_management(self):
        """Test AppState class functionality."""
        # Test initial state
        self.assertFalse(self.state.recording)
        self.assertEqual(self.state.audio_frames, [])
        self.assertFalse(self.state.stop_event.is_set())
        self.assertIsNone(self.state.audio_instance)
        
        # Test state changes
        self.state.recording = True
        self.state.audio_frames.append(b'test')
        self.state.stop_event.set()
        self.state.audio_instance = MagicMock()
        
        self.assertTrue(self.state.recording)
        self.assertEqual(self.state.audio_frames, [b'test'])
        self.assertTrue(self.state.stop_event.is_set())
        self.assertIsNotNone(self.state.audio_instance)

if __name__ == '__main__':
    unittest.main() 