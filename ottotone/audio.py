from faster_whisper import WhisperModel
import sounddevice as sd
import threading
import time
import queue
import math
import numpy as np
import logging
import os
import sys
import gc
import psutil

from .config import AppConfig

logger = logging.getLogger(__name__)

class AudioRecorder:
    """Handles audio recording and transcription using faster-whisper.
    
    Records audio from microphone, detects silence, and transcribes using Whisper.
    Automatically stops recording after detecting silence following speech.
    """
    STATE_IDLE = "IDLE"
    STATE_WAITING_FOR_SPEECH = "WAITING_FOR_SPEECH"
    STATE_SPEECH_DETECTED = "SPEECH_DETECTED"

    def __init__(self, config, transcription_callback=None):
        if isinstance(config, AppConfig):
            self.config = config
            self.audio_config = config.audio
        else:
            logger.warning("AudioRecorder received legacy ConfigManager. Creating AppConfig wrapper.")
            self.config = AppConfig()
            self.config.migrate_from_legacy_config(config)
            self.audio_config = self.config.audio
            
        self.transcription_callback = transcription_callback
        self._load_transcription_parameters()

        self.model_size = self.audio_config.get_selected_model()
        self.model_path = self.audio_config.get_models_path()
        self.device = "cpu"  # Explicitly use CPU as faster-whisper doesn't support MPS
        self.compute_type = "int8"

        self.model = None
        if not self._load_model():
            raise RuntimeError("Failed to load the initial Whisper model.")

        logger.info(f"AudioRecorder initialized. Model: {self.model_size}, Device: {self.device}, Compute: {self.compute_type}.")
        
        # Initialize recording state
        self.frames = []
        self.is_recording = False
        self.command_queue = queue.Queue()
        self._abort_transcription = False
        self._stop_triggered_by_silence = False
        self._silence_start_time = None
        self._recording_start_time = None
        self.min_recording_time = 0.5
        self.current_recording_state = self.STATE_IDLE
        self._initial_speech_detected_this_session = False

        # Start audio processing thread
        self.audio_manager_thread = threading.Thread(target=self._audio_manager_worker, daemon=True)
        self.audio_manager_thread.start()

    def _load_transcription_parameters(self):
        """Load transcription parameters from configuration."""
        # Load transcription parameters
        self.transcribe_language = self.audio_config.get_language()
        self.transcribe_beam_size = self.audio_config.get_beam_size()
        self.transcribe_vad_filter = self.audio_config.get_vad_filter()
        self.transcribe_vad_parameters = self.audio_config.get_vad_parameters()
        self.transcribe_temperature = self.audio_config.get_temperature()
        self.transcribe_patience = self.audio_config.get_patience()
        self.transcribe_condition_on_previous_text = self.audio_config.get_condition_on_previous_text()
        
        # Load silence detection parameters
        self.silence_threshold_db = self.audio_config.get_silence_threshold_db()
        self.silence_duration = self.audio_config.get_silence_duration_seconds()

        logger.info(f"Parameters loaded: silence={self.silence_threshold_db}dB/{self.silence_duration}s, VAD={self.transcribe_vad_filter}")
        logger.info(f"VAD params: {self.transcribe_vad_parameters}")

    def reload_model(self):
        """Reload model with updated configuration."""
        new_model_size = self.audio_config.get_selected_model()
        old_model_size = self.model_size
        
        if new_model_size != old_model_size:
            logger.info(f"Model change: {old_model_size} -> {new_model_size}")
            
            # Track memory before model change
            self._log_memory_usage("Before model change")
            
            # Unload old model first
            if not self._unload_current_model():
                logger.warning("Failed to properly unload previous model, continuing with load anyway")
            
            # Update model size and load new model
            self.model_size = new_model_size
            if self._load_model():
                logger.info(f"Model {new_model_size} loaded successfully")
                self._load_transcription_parameters()
                
                # Final memory usage after model change complete
                self._log_memory_usage("After model change complete")
                return True
            else:
                logger.error(f"Failed to load {new_model_size}, reverting to {old_model_size}")
                self.model_size = old_model_size
                self._load_model()
                return False
        else:
            logger.info(f"Model unchanged ({old_model_size}), updating parameters only")
            self._load_transcription_parameters()
            return True

    def _calculate_dbfs(self, data):
        rms = np.sqrt(np.mean(data**2))
        if rms == 0: return -np.inf
        dbfs = 20 * math.log10(rms)
        return dbfs

    def _recording_callback(self, indata, frame_count, time_info, status):
        """Callback function for the InputStream."""
        if status:
            logger.warning(f"WARNING: Recording callback status: {status}")
        
        if not self.is_recording or self.current_recording_state == self.STATE_IDLE:
            return
        
        self.frames.append(indata.copy().astype(np.float32))

        current_time = time.monotonic()
        if self._recording_start_time is None: # Should be set by _audio_manager_worker
            self._recording_start_time = current_time 

        # Always respect min_recording_time to avoid processing tiny audio snippets
        if (current_time - self._recording_start_time) < self.min_recording_time:
            return

        mono_data = indata.mean(axis=1) if indata.ndim > 1 else indata
        dbfs = self._calculate_dbfs(mono_data)
        
        # Log audio levels periodically to debug silence detection
        if int(current_time * 10) % 20 == 0:  # Log approximately every 2 seconds
            logger.debug(f"Audio level: {dbfs:.2f} dB, Threshold: {self.silence_threshold_db:.2f} dB, State: {self.current_recording_state}")

        if self.current_recording_state == self.STATE_WAITING_FOR_SPEECH:
            if dbfs >= self.silence_threshold_db:
                logger.info(f"Initial sound detected (dBFS: {dbfs:.2f}). Transitioning to SPEECH_DETECTED state.")
                self.current_recording_state = self.STATE_SPEECH_DETECTED
                self._initial_speech_detected_this_session = True
                self._silence_start_time = None # Reset silence timer, as speech just occurred
            # else: Still waiting for speech, silence timer is not active yet.

        elif self.current_recording_state == self.STATE_SPEECH_DETECTED:
            if dbfs < self.silence_threshold_db:
                if self._silence_start_time is None:
                    self._silence_start_time = current_time
                    logger.debug(f"Sound dropped below threshold (dBFS: {dbfs:.2f}). Starting silence timer (duration: {self.silence_duration}s).")
                elif (current_time - self._silence_start_time) >= self.silence_duration:
                    if not self.is_recording or self._stop_triggered_by_silence: # Check if already stopping
                        return 

                    logger.info(f"Max silence duration ({self.silence_duration}s) met after speech. Queuing stop command.")
                    logger.info(f"Silence details - Start: {self._silence_start_time:.2f}, Current: {current_time:.2f}, Duration: {current_time - self._silence_start_time:.2f}s")
                    self._stop_triggered_by_silence = True # Mark that silence is the trigger
                    self.command_queue.put({"command": "stop", "reason": "silence_detected"})
            else: # Sound is present (dbfs >= self.silence_threshold_db)
                if self._silence_start_time is not None:
                    logger.debug(f"Sound re-detected (dBFS: {dbfs:.2f}), resetting silence timer.")
                self._silence_start_time = None # Reset silence timer as sound is present

    def _log_memory_usage(self, tag=""):
        """Log current memory usage.
        
        Args:
            tag: Optional tag to include in the log message
        """
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            prefix = f"[{tag}] " if tag else ""
            logger.info(f"{prefix}Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB RSS, {memory_info.vms / 1024 / 1024:.2f} MB VMS")
        except Exception as e:
            logger.warning(f"Failed to log memory usage: {e}")
    
    def _unload_current_model(self):
        """Unload the current model and release resources."""
        if self.model is not None:
            logger.info("Unloading existing model and releasing resources...")
            try:
                # Log memory before unloading
                self._log_memory_usage("Before model unload")
                
                # Delete model and run garbage collection
                del self.model
                self.model = None
                
                # Force a full garbage collection
                logger.debug("Running garbage collection cycle...")
                collected = gc.collect()
                logger.debug(f"Garbage collection finished - collected {collected} objects")
                
                # Log memory after unloading and GC
                self._log_memory_usage("After model unload and GC")
                
                # Give system a moment to clean up resources
                time.sleep(0.2)
                
                return True
            except Exception as e:
                logger.error(f"Error unloading model: {e}", exc_info=True)
                return False
        return True  # No model to unload
    
    def _load_model(self):
        try:            
            # Release existing model if present
            self._unload_current_model()
            
            # Ensure model parameters are set
            if not hasattr(self, 'model_size') or not self.model_size:
                self.model_size = self.audio_config.get_selected_model()
            self.compute_type = self.audio_config.get_compute_type()
            self.device = "cpu"  # Always use CPU as faster-whisper doesn't support MPS

            # Get path for models
            effective_model_path = self.audio_config.get_models_path()
            force_local_files_only = False

            # Handle bundled app case (PyInstaller)
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                bundle_model_dir = os.path.join(sys._MEIPASS, 'bundled_models')
                if os.path.isdir(bundle_model_dir):
                    potential_model_bundle_path = os.path.join(bundle_model_dir, self.model_size)
                    if os.path.isdir(potential_model_bundle_path):
                        logger.info(f"Found bundled model '{self.model_size}'")
                        effective_model_path = bundle_model_dir
                    else:
                        logger.info(f"Using bundled models dir as download_root")
                        effective_model_path = bundle_model_dir
                    force_local_files_only = True
                else:
                    logger.warning(f"Bundled models directory not found, using fallback path")
                    force_local_files_only = True
            
            # Log memory before loading new model
            self._log_memory_usage("Before model load")
            
            logger.info(f"Loading Whisper model '{self.model_size}' (device: {self.device})")
            self.model = WhisperModel(
                model_size_or_path=self.model_size,
                device=self.device, 
                compute_type=self.compute_type,
                download_root=effective_model_path,
                local_files_only=force_local_files_only
            )
            
            # Log memory after loading new model
            self._log_memory_usage("After model load")
            
            logger.info(f"Whisper model '{self.model_size}' loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{self.model_size}': {e}", exc_info=True)
            error_message = f"Failed to load model {self.model_size}. Error: {str(e)[:100]}..."
            self._safe_callback({"status": "model_load_error", "error": error_message, "details": str(e)})
            return False

    def _audio_manager_worker(self):
        current_stream = None # Local stream variable for this thread

        while True:
            try:
                command_data = self.command_queue.get() # Blocks until a command is available
                command = command_data.get("command")
                logger.debug(f"DEBUG AUDMAN: Received command: {command}")

                if command == "start":
                    if self.is_recording:
                        logger.debug("DEBUG AUDMAN: Already recording, ignoring start command.")
                        continue
                    
                    if sd is None:
                        logger.error("ERROR AUDMAN: sounddevice not available, cannot start recording.")
                        self._safe_callback({"status": "error", "message": "Audio device error"})
                        continue

                    if self.model is None:
                        logger.error("ERROR AUDMAN: Model not loaded, aborting recording start.")
                        self._safe_callback({"status": "error", "message": "Model not loaded"})
                        continue # Added continue

                    self.frames = []
                    self._silence_start_time = None
                    self._recording_start_time = time.monotonic() # Set actual stream start time here
                    self._stop_triggered_by_silence = False
                    self._initial_speech_detected_this_session = False # Reset for new session
                    self.current_recording_state = self.STATE_WAITING_FOR_SPEECH # Set initial state

                    try:
                        # Query sample rate each time in case default device changes
                        # TODO: Make device selectable and store its sample rate
                        device_info = sd.query_devices(None, 'input')
                        samplerate = int(device_info['default_samplerate'])
                        logger.info(f"INFO: Audio device initialized. Device: {device_info['name']}, Sample rate: {samplerate}Hz")
                        
                        current_stream = sd.InputStream(
                            samplerate=samplerate, 
                            channels=1,
                            callback=self._recording_callback,
                            dtype='float32'
                        )
                        current_stream.start()
                        self.is_recording = True # Critical: Set true *after* stream starts
                        logger.info("INFO: Recording started by audio manager. State: WAITING_FOR_SPEECH")
                        self._safe_callback({"status": "recording_started"})
                    except Exception as e:
                        logger.error(f"ERROR AUDMAN: Failed to start audio stream: {e}", exc_info=True)
                        self.is_recording = False
                        self.current_recording_state = self.STATE_IDLE # Reset state on error
                        if current_stream:
                            try: 
                                current_stream.stop() # Ensure stream is stopped
                                current_stream.close()
                            except Exception as e_close:
                                logger.error(f"ERROR AUDMAN: Exception closing stream after start failure: {e_close}")
                        current_stream = None
                        self._safe_callback({"status": "error", "message": f"Audio stream error: {e}"})
                
                elif command == "stop":
                    if not self.is_recording and not self._stop_triggered_by_silence:
                        logger.debug("DEBUG AUDMAN: Not recording or stop already processed (e.g. by silence), ignoring redundant stop command.")
                        # If already stopped by silence, _stop_triggered_by_silence will be true.
                        # If is_recording is false and _stop_triggered_by_silence is false, it was likely a manual stop already handled.
                        if self.current_recording_state == self.STATE_IDLE:
                             continue
                    
                    reason = command_data.get("reason", "manual_stop")
                    logger.debug(f"DEBUG AUDMAN: Processing stop command. Reason: {reason}. Current state: {self.current_recording_state}")
                    
                    self.is_recording = False # Signal callback to stop appending frames *first*
                    self.current_recording_state = self.STATE_IDLE # Transition to IDLE

                    if reason == "silence_detected":
                        self._stop_triggered_by_silence = True # This flag is checked by callback
                    else: # manual_stop or other reasons
                        self._stop_triggered_by_silence = False

                    actual_stop_reason = "silence_detected" if self._stop_triggered_by_silence else "manual_stop"

                    if current_stream:
                        logger.debug("DEBUG AUDMAN: Stream exists. Attempting to stop and close.")
                        try:
                            current_stream.stop()
                            logger.debug("DEBUG AUDMAN: current_stream.stop() called successfully.")
                            current_stream.close()
                            logger.debug("DEBUG AUDMAN: current_stream.close() called successfully.")
                        except Exception as e:
                            logger.error(f"ERROR AUDMAN: Exception while stopping/closing audio stream: {e}", exc_info=True)
                        current_stream = None
                        logger.debug("DEBUG AUDMAN: Stream stopped, closed, and set to None.")
                    else:
                        logger.debug("DEBUG AUDMAN: Stream is None. No stream operations needed for stop.")

                    logger.info(f"INFO: Recording stopped by audio manager. Reason: {actual_stop_reason}")
                    self._safe_callback({"status": "recording_stopped", "reason": actual_stop_reason})

                    # Check if any audio was actually captured before attempting transcription
                    # This also handles the case where recording was stopped before min_recording_time
                    # or if no initial speech was detected and then a manual stop occurred.
                    if not self.frames or not self._initial_speech_detected_this_session and actual_stop_reason == "manual_stop":
                        if not self.frames:
                            logger.warning("WARNING AUDMAN: No frames recorded.")
                        if not self._initial_speech_detected_this_session and actual_stop_reason == "manual_stop":
                            logger.info("INFO AUDMAN: Recording stopped manually before initial speech was detected. No transcription.")
                        
                        self._safe_callback({
                            "status": "no_audio_for_transcription", 
                            "reason": actual_stop_reason, 
                            "message": "No speech detected or recording too short."
                        })
                        self.frames = [] # Ensure frames are cleared
                        self._stop_triggered_by_silence = False # Reset for next session
                        continue

                    # Make a copy of frames for transcription thread to prevent modification issues
                    frames_to_transcribe = list(self.frames) 
                    self.frames = [] # Clear frames immediately
                    
                    audio_data_np = np.concatenate(frames_to_transcribe, axis=0).astype(np.float32)
                    
                    if audio_data_np.ndim > 1:
                        audio_data_np = audio_data_np.mean(axis=1)
                    
                    logger.info(f"INFO AUDMAN: Audio data prepared for transcription. Samples: {len(audio_data_np)}")
                    self._safe_callback({"status": "processing_transcription"})
                    
                    # Start transcription in a new thread
                    transcription_thread = threading.Thread(
                        target=self._transcribe_audio_data, 
                        args=(audio_data_np, actual_stop_reason)
                    )
                    transcription_thread.daemon = True # Ensure thread doesn't block app exit
                    transcription_thread.start()

                elif command == "exit":
                    logger.info("INFO AUDMAN: Exit command received. Shutting down audio manager.")
                    if current_stream:
                        try:
                            if self.is_recording:
                                current_stream.stop()
                                self.is_recording = False
                            current_stream.close()
                        except Exception as e:
                            logger.error(f"ERROR AUDMAN: Exception during stream cleanup on exit: {e}")
                        current_stream = None
                    break # Exit the while loop, ending the thread
                else:
                    logger.warning(f"WARNING AUDMAN: Unknown command received: {command_data}")
            
            except queue.Empty:
                # This should not happen with queue.get() blocking, but as a safeguard.
                continue
            except Exception as e:
                logger.error(f"CRITICAL AUDMAN: Unhandled exception in audio manager worker loop: {e}", exc_info=True)
                # Attempt to gracefully stop recording if active, to prevent runaway threads/resources
                if current_stream and self.is_recording:
                    try:
                        current_stream.stop()
                        current_stream.close()
                    except Exception as e_stop:
                        logger.error(f"CRITICAL AUDMAN: Further error stopping stream during exception handling: {e_stop}")
                self.is_recording = False
                self.current_recording_state = self.STATE_IDLE
                current_stream = None
                # Consider if the thread should exit or try to recover. For now, it continues.
                # If errors persist, the app might become unresponsive or behave erratically.

        logger.info("INFO AUDMAN: Audio manager worker thread finished.")

    def _safe_callback(self, data):
        """Safely invoke callbacks on the main thread."""
        if self.transcription_callback:
            def invoke_callback():
                self.transcription_callback(data)
            threading.Timer(0.01, invoke_callback).start()

    def start_recording(self):
        """Start recording audio."""
        logger.debug("Starting audio recording")
        self.command_queue.put({"command": "start"})
        return True

    def stop_recording(self, reason="manual_stop"):
        """Stop recording audio."""
        logger.debug(f"Stopping recording, reason: {reason}")
        self.command_queue.put({"command": "stop", "reason": reason})

    def _transcribe_audio_data(self, audio_data_np, reason):
        """Transcribe recorded audio data."""
        try:
            if self._abort_transcription:
                logger.debug("Transcription aborted due to shutdown request")
                return
            
            # Basic audio stats for debugging
            avg_amplitude = np.abs(audio_data_np).mean()
            max_amplitude = np.abs(audio_data_np).max()
            logger.debug(f"Audio samples: {len(audio_data_np)}, Mean: {avg_amplitude:.4f}, Max: {max_amplitude:.4f}")
            
            # Get transcription parameters and run the model
            transcription_params = self.audio_config.get_all_transcription_parameters()
            segments, info = self.model.transcribe(
                audio_data_np,
                language=transcription_params["language"],
                beam_size=transcription_params["beam_size"],
                vad_filter=transcription_params["vad_filter"],
                vad_parameters=transcription_params["vad_parameters"],
                temperature=transcription_params["temperature"],
                patience=transcription_params["patience"],
                condition_on_previous_text=transcription_params["condition_on_previous_text"]
            )
            
            if self._abort_transcription:
                logger.debug("Transcription results discarded due to shutdown")
                return
                
            # Convert segments to text
            transcribed_text = "".join(segment.text for segment in segments).strip()
            logger.info(f"Transcription complete. Detected: {info.language} (prob: {info.language_probability:.2f})")
            
            self._safe_callback({
                "status": "transcription_complete", 
                "text": transcribed_text, 
                "language": info.language, 
                "reason": reason
            })
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            self._safe_callback({"status": "error", "reason": reason, "message": f"Error during transcription: {e}"})

    def shutdown(self):
        """Shut down the audio recorder."""
        logger.info("Shutting down audio recorder")
        
        # Log memory before shutdown
        self._log_memory_usage("Before shutdown")
        
        # Signal any ongoing transcription to abort
        self._abort_transcription = True
        
        # Signal audio manager thread to exit and wait for it
        self.command_queue.put({"command": "exit"})
        if self.audio_manager_thread and self.audio_manager_thread.is_alive():
            logger.debug("Waiting for audio manager thread to exit (timeout: 3s)")
            self.audio_manager_thread.join(timeout=3.0)
            if self.audio_manager_thread.is_alive():
                logger.warning("Audio manager thread did not exit within timeout")
        
        # Unload and cleanup model resources
        if self._unload_current_model():
            logger.debug("Model resources released successfully")
        else:
            logger.warning("Failed to properly release model resources")
        
        # Final cleanup
        logger.debug("Running final garbage collection")
        collected = gc.collect()
        logger.debug(f"Final GC collected {collected} objects")
        
        # Log memory after shutdown
        self._log_memory_usage("After shutdown")
        
        logger.info("Audio recorder shutdown complete")
