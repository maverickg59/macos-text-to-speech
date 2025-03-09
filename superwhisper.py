#!/usr/bin/env python3
# Superwhisper - Voice-to-text transcription tool using OpenAI's Whisper
# This application uses a global Cmd+Control+R hotkey to record audio,
# automatically stops on silence, and puts transcribed text on the clipboard.

import os
import sys
import time
import tempfile
import wave
import threading
import logging

import numpy as np
import pyaudio
import pyperclip
import whisper
from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('superwhisper.log')  # File output
    ]
)
logger = logging.getLogger('superwhisper')
# logger.setLevel(logging.DEBUG)  # Enable debug logging

# Audio recording settings
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1         # Mono
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHUNK_SIZE = 1024    # Audio buffer size
SILENCE_THRESHOLD = 300  # Lower threshold for better voice detection
SILENCE_DURATION = 0.5  # Seconds of silence to trigger stop
MIN_AUDIO_DURATION = 0.25  # Reduced minimum audio duration for better responsiveness

# Initialize Whisper model (do this once at startup)
logger.info("Loading Whisper model...")
model = whisper.load_model("tiny")
logger.info("Whisper model loaded successfully")

# Global state - consolidated
class AppState:
    recording = False
    audio_frames = []
    stop_event = threading.Event()
    audio_instance = None

state = AppState()

def is_silence(audio_data, threshold):
    """Determine if the audio chunk is silent based on amplitude threshold"""
    # Convert audio data to numpy array and get average volume
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    volume = np.abs(audio_array).mean()
    logger.debug(f"Current volume: {volume}")  # Add volume logging
    return volume < threshold

def start_recording():
    """Start recording audio from the default microphone"""
    if state.recording:
        logger.info("Already recording. Stopping current recording.")
        stop_recording()
        return
    
    state.recording = True
    state.audio_frames = []
    state.stop_event.clear()
    
    logger.info("Recording started... (Press Cmd+Control+R again to stop manually)")
    
    # Create a new thread for recording to avoid blocking the main thread
    record_thread = threading.Thread(target=record_audio)
    record_thread.daemon = True
    record_thread.start()

def record_audio():
    """Record audio and detect silence"""
    # Initialize PyAudio
    state.audio_instance = pyaudio.PyAudio()
    
    # List available input devices
    info = state.audio_instance.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (state.audio_instance.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            logger.info(f"Input Device {i}: {state.audio_instance.get_device_info_by_host_api_device_index(0, i).get('name')}")
    
    # Open audio stream
    stream = state.audio_instance.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
        input_device_index=None  # Use default input device
    )
    
    silent_chunks = 0
    silence_limit = int(SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE)
    min_audio_chunks = int(MIN_AUDIO_DURATION * SAMPLE_RATE / CHUNK_SIZE)
    has_audio = False
    audio_chunks = 0
    
    try:
        # Continue recording until stopped or silence detected
        while state.recording and not state.stop_event.is_set():
            try:
                # Read audio chunk
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                state.audio_frames.append(data)
                
                # Check for silence
                if is_silence(data, SILENCE_THRESHOLD):
                    # Only count silence after we've detected some audio
                    if has_audio:
                        silent_chunks += 1
                        if silent_chunks >= silence_limit:
                            logger.info("Silence threshold reached after audio detected, stopping recording")
                            break
                else:
                    silent_chunks = 0
                    if not has_audio:
                        audio_chunks += 1
                        if audio_chunks >= min_audio_chunks:
                            has_audio = True
                            logger.info("Audio detected, recording...")
            except IOError as e:
                logger.error(f"IOError during recording: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error during recording: {e}")
    
    finally:
        # Clean up resources
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        
        state.recording = False
        
        # Only process if we captured some audio
        if has_audio:
            process_recording()
        else:
            logger.info("No audio detected, discarding recording")
        
        # Clean up PyAudio instance
        state.audio_instance.terminate()
        state.audio_instance = None

def stop_recording():
    """Stop the current recording"""
    if not state.recording:
        return
    
    logger.info("Stopping recording...")
    state.stop_event.set()
    state.recording = False

def save_audio_to_file():
    """Save recorded audio frames to a temporary WAV file"""
    if not state.audio_frames:
        logger.warning("No audio recorded")
        return None
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_filename = temp_file.name
    temp_file.close()
    
    # Write audio frames to WAV file
    with wave.open(temp_filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(state.audio_instance.get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(state.audio_frames))
    
    logger.info(f"Audio saved to temporary file: {temp_filename}")
    return temp_filename

def transcribe_audio(audio_file):
    """Transcribe audio file using Whisper"""
    try:
        logger.info("Transcribing audio...")
        result = model.transcribe(
            audio_file,
            language="en",
            task="transcribe",
            fp16=False  # Use fp32 for better compatibility
        )
        
        transcription = result["text"].strip()
        logger.info(f"Transcription completed: {transcription}")
        return transcription
    
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None

def process_recording():
    """Process the recorded audio and get transcription"""
    # Save audio to file
    audio_file = save_audio_to_file()
    if not audio_file:
        return
    
    # Transcribe audio
    transcription = transcribe_audio(audio_file)
    
    # Copy to clipboard
    if transcription:
        pyperclip.copy(transcription)
        logger.info("Transcription copied to clipboard")
    
    # Clean up temporary file
    try:
        os.remove(audio_file)
        logger.info(f"Temporary audio file removed: {audio_file}")
    except Exception as e:
        logger.warning(f"Failed to remove temporary file: {e}")

def setup_hotkey_listener():
    """Set up the global hotkey listener"""
    # Create keyboard listener for global hotkey
    listener = keyboard.GlobalHotKeys({
        '<cmd>+<ctrl>+r': lambda: start_recording() if not state.recording else stop_recording()
    })
    
    # Start listening for hotkey
    listener.start()
    return listener

def main():
    """Main application entry point"""
    logger.info("Superwhisper started")
    logger.info("Press Cmd+Control+R to start recording")
    
    # Set up hotkey listener
    listener = setup_hotkey_listener()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    finally:
        # Clean up resources
        listener.stop()
        if state.recording:
            stop_recording()
        logger.info("Superwhisper stopped")

if __name__ == "__main__":
    main() 