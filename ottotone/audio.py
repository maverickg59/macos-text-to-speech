from faster_whisper import WhisperModel
import sounddevice as sd
import threading
import time
import queue
import platform
import math
import numpy as np
import logging
import os
import sys

# Set up logging
logger = logging.getLogger(__name__)

class AudioRecorder:
    """Handles audio recording and transcription using faster-whisper.

    Responsibilities:
    - Record audio from microphone.
    - Transcribe recorded audio using Whisper.
    - Manage Whisper model loading.
    - Automatically stop recording after a period of silence.
    """
    def __init__(self, config_manager, transcription_callback=None):
        self.config_manager = config_manager
        self.transcription_callback = transcription_callback

        self._load_transcription_parameters()

        self.model_size = self.config_manager.get_selected_model()
        self.model_path = self.config_manager.get_models_path()
        self.device = "cpu"
        self.compute_type = "int8"

        self.model = None
        if not self._load_model():
            raise RuntimeError("Failed to load the initial Whisper model.")

        logger.info(f"AudioRecorder initialized. Model: {self.model_size}, Device: {self.device}, Compute: {self.compute_type}.")
        
        self.frames = []
        self.is_recording = False
        self.command_queue = queue.Queue()
        self._abort_transcription = False
        self._stop_triggered_by_silence = False
        self.silence_threshold_db = self.config_manager.get_silence_threshold_db(default=-30.0)
        self.silence_duration = self.config_manager.get_silence_duration_seconds(default=2.0)
        self._silence_start_time = None
        self._recording_start_time = None
        self.min_recording_time = 0.5

        self.audio_manager_thread = threading.Thread(target=self._audio_manager_worker, daemon=True)
        self.audio_manager_thread.start()

    def _load_transcription_parameters(self):
        """Loads or re-loads transcription parameters from ConfigManager."""
        self.transcribe_language = self.config_manager.get_transcription_param("language", default="en")
        self.transcribe_beam_size = self.config_manager.get_transcription_param("beam_size", default=5)
        self.transcribe_vad_filter = self.config_manager.get_transcription_param("vad_filter", default=True)
        default_vad_params = {"min_silence_duration_ms": 250, "threshold": 0.35}
        self.transcribe_vad_parameters = self.config_manager.get_transcription_param("vad_parameters", default=default_vad_params)
        self.transcribe_temperature = self.config_manager.get_transcription_param("temperature", default=0.0)
        self.transcribe_patience = self.config_manager.get_transcription_param("patience", default=1.0)
        self.transcribe_condition_on_previous_text = self.config_manager.get_transcription_param("condition_on_previous_text", default=False)
        logger.info("Transcription parameters loaded/reloaded.")

    def reload_model(self):
        """Reloads the Whisper model and its transcription parameters, typically after a configuration change."""
        logger.info("Reloading Whisper model and transcription parameters...")
        if self.model is not None:
            logger.info("Releasing existing model...")
            del self.model
            self.model = None
            logger.info("Existing model released.")

        self.model_size = self.config_manager.get_selected_model()
        self._load_transcription_parameters()

        logger.info(f"New model selected: {self.model_size}")
        if not self._load_model():
            self._safe_callback({"status": "error", "message": f"Failed to reload model {self.model_size}."})
            logger.error(f"Failed to reload model {self.model_size}. Keeping old model if one existed, or no model.")
            return False
        
        logger.info(f"Whisper model reloaded. Current model: {self.model_size}")
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
        
        if not self.is_recording:
            return
        
        # Append audio data as float32, which is standard for processing
        self.frames.append(indata.copy().astype(np.float32))

        current_time = time.monotonic()
        if self._recording_start_time is None:
            self._recording_start_time = current_time 

        if (current_time - self._recording_start_time) < self.min_recording_time:
            return

        mono_data = indata.mean(axis=1) if indata.ndim > 1 else indata
        dbfs = self._calculate_dbfs(mono_data)

        if dbfs < self.silence_threshold_db:
            if self._silence_start_time is None:
                self._silence_start_time = current_time
            elif (current_time - self._silence_start_time) >= self.silence_duration:
                # Check if a stop command due to silence has already been issued for this recording session.
                # This prevents queuing multiple stop commands if the callback somehow fires again
                # before the audio manager processes the first stop command.
                if not self.is_recording or self._stop_triggered_by_silence:
                    return # Already stopping or stopped

                logger.info(f"INFO: Silence duration ({self.silence_duration}s) met. Queuing stop command.")
                self._stop_triggered_by_silence = True # Mark that silence is the trigger
                self.command_queue.put({"command": "stop", "reason": "silence_detected"})
                # Do not reset _silence_start_time here. The recording will be stopped by the manager.
                # The _safe_callback for 'silence_limit_reached' is no longer needed here as the stop command implies this.
                # If app.py needs a pre-stop notification, that's a different status like 'silence_detected_stopping'.
                # For now, the 'recording_stopped' with reason 'silence_detected' should be sufficient.
        else:
            if self._silence_start_time is not None:
                logger.debug(f"DEBUG: Sound detected, resetting silence timer. (dBFS: {dbfs:.2f})")
                self._silence_start_time = None

    def _load_model(self):
        self.model = None # Clear existing model first
        self.model_size = self.config_manager.get_selected_model()
        self.compute_type = self.config_manager.get_compute_type(default="int8") # Get from config
        self.device = "cpu" # Ensure it's always CPU for Macs

        # Determine the correct path for models (for bundled app or normal run)
        effective_model_path = self.config_manager.get_models_path() # User-defined path from config
        force_local_files_only = False

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Application is running in a bundled environment (PyInstaller)
            # Models are expected to be in 'bundled_models' directory relative to sys._MEIPASS
            bundle_model_dir = os.path.join(sys._MEIPASS, 'bundled_models')
            if os.path.isdir(bundle_model_dir):
                # Check if the specific model exists within the bundled directory
                potential_model_bundle_path = os.path.join(bundle_model_dir, self.model_size)
                if os.path.isdir(potential_model_bundle_path):
                    logger.info(f"Running bundled. Found model '{self.model_size}' in bundled models path: {potential_model_bundle_path}")
                    # If model_size is a name like 'base', and it's found directly under bundled_models, 
                    # effective_model_path should point to 'bundled_models' for download_root behavior.
                    # If self.model_size was intended as a sub-path already, this logic might need adjustment.
                    # For now, assume model_size is a direct subdir name under bundled_models or a full path.
                    effective_model_path = bundle_model_dir # WhisperModel will look for 'model_size' inside this
                else:
                    # If the specific model isn't a subdir, but model_size itself might be a full path to a bundled model
                    # This case is less likely if we bundle all models under 'bundled_models/<model_name>/'
                    logger.info(f"Running bundled. Model '{self.model_size}' not found as direct subdir in {bundle_model_dir}. Using '{self.model_size}' as model_size_or_path and {bundle_model_dir} as download_root.")
                    effective_model_path = bundle_model_dir # Still use bundled_models as the root to search in
                force_local_files_only = True # Crucial for bundled apps
            else:
                logger.warning(f"Running bundled, but 'bundled_models' directory not found at {bundle_model_dir}. Will fall back to config/default download path. This might fail if internet is unavailable.")
                # If bundled_models isn't found, it will fall back to user's config path or default download behavior of faster-whisper
                # Forcing local_files_only might be risky here if we expect a fallback download.
                # However, for a truly standalone app, we should aim for bundled_models to exist.
                force_local_files_only = True # Still prefer local if we claim to be bundled.
    
        logger.info(f"INFO: Loading Whisper model '{self.model_size}' (device: {self.device}, compute: {self.compute_type}). Effective model download_root: {effective_model_path}, local_files_only: {force_local_files_only}")
        try:
            self.model = WhisperModel(
                model_size_or_path=self.model_size, # Pass the model size/name directly
                device=self.device, 
                compute_type=self.compute_type,
                download_root=effective_model_path, # Use the determined path for download/caching if not an absolute path
                local_files_only=force_local_files_only # For bundled app, force local files only
            )
            logger.info(f"INFO: Whisper model '{self.model_size}' loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"ERROR: Failed to load Whisper model '{self.model_size}': {e}", exc_info=True)
            # Attempt to provide a more user-friendly error to the main app if possible
            error_message = f"Failed to load model {self.model_size}. Error: {str(e)[:100]}..."
            self._safe_callback({"status": "model_load_error", "error": error_message, "details": str(e)})
            self.model = None
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
                        continue

                    self.frames = []
                    self._silence_start_time = None
                    self._recording_start_time = time.monotonic()
                    self._stop_triggered_by_silence = False

                    try:
                        samplerate = int(sd.query_devices(None, 'input')['default_samplerate'])
                        logger.info(f"INFO: Audio device initialized. Sample rate: {samplerate}Hz")
                        current_stream = sd.InputStream(
                            samplerate=samplerate, 
                            channels=1,
                            callback=self._recording_callback,
                            dtype='float32'
                        )
                        current_stream.start()
                        self.is_recording = True
                        logger.info("INFO: Recording started by audio manager.")
                        self._safe_callback({"status": "recording_started"})
                    except Exception as e:
                        logger.error(f"ERROR AUDMAN: Failed to start audio stream: {e}")
                        self.is_recording = False
                        if current_stream:
                            try: current_stream.close()
                            except: pass
                        current_stream = None
                        self._safe_callback({"status": "error", "message": f"Audio stream error: {e}"})
                
                elif command == "stop":
                    if not self.is_recording and not self._stop_triggered_by_silence:
                        logger.debug("DEBUG AUDMAN: Not recording or stop already processed, ignoring stop command.")
                        if not self.is_recording:
                             continue
                    
                    reason = command_data.get("reason", "manual_stop")
                    logger.debug(f"DEBUG AUDMAN: Processing stop command. Reason: {reason}")
                    
                    # Critical: Set is_recording false *before* touching the stream.
                    # This signals the callback to stop appending frames.
                    self.is_recording = False 
                    if reason == "silence_detected":
                        self._stop_triggered_by_silence = True
                    else:
                        self._stop_triggered_by_silence = False # Clear if manual stop

                    actual_stop_reason = "silence_detected" if self._stop_triggered_by_silence else "manual_stop"

                    if current_stream:
                        logger.debug("DEBUG AUDMAN: Stream exists. Attempting to stop and close.")
                        try:
                            current_stream.stop()
                            logger.debug("DEBUG AUDMAN: current_stream.stop() called successfully.")
                            current_stream.close()
                            logger.debug("DEBUG AUDMAN: current_stream.close() called successfully.")
                        except Exception as e:
                            logger.error(f"ERROR AUDMAN: Exception while stopping/closing audio stream: {e}")
                        current_stream = None # Clear stream reference
                        logger.debug("DEBUG AUDMAN: Stream stopped, closed, and set to None.")
                    else:
                        logger.debug("DEBUG AUDMAN: Stream is None. No stream operations needed for stop.")

                    logger.info(f"INFO: Recording stopped by audio manager. Reason: {actual_stop_reason}")

                    if not self.frames:
                        logger.warning("WARNING AUDMAN: No frames recorded before stop command.")
                        self._safe_callback({"status": "no_audio_recorded", "reason": actual_stop_reason})
                        self._stop_triggered_by_silence = False 
                        continue

                    audio_data_np = np.concatenate(self.frames, axis=0).astype(np.float32)
                    self.frames = [] # Clear frames immediately after concatenation
                    
                    # Convert to mono if needed
                    if audio_data_np.ndim > 1:
                        audio_data_np = audio_data_np.mean(axis=1)
                    
                    # Normalize the audio (scale to [-1.0, 1.0] range)
                    # This is crucial for Whisper performance
                    max_abs_val = np.abs(audio_data_np).max()
                    if max_abs_val > 0:
                        audio_data_np = audio_data_np / max_abs_val
                    else:
                        logger.warning("WARNING AUDMAN: Audio data is all zeros after concatenation.")
                        self._safe_callback({"status": "no_audio_recorded", "reason": "empty_signal"})
                        self._stop_triggered_by_silence = False
                        continue
                                        
                    logger.debug("DEBUG AUDMAN: Frames concatenated, converted to mono, normalized, and cleared.")
                    
                    # Run transcription in a separate thread so we can respond to exit commands immediately
                    self._transcription_thread = threading.Thread(
                        target=self._transcribe_audio_data,
                        args=(audio_data_np, actual_stop_reason),
                        daemon=True
                    )
                    self._transcription_thread.start()
                    self._stop_triggered_by_silence = False # Reset for next recording

                elif command == "exit":
                    logger.info("INFO AUDMAN: Exit command received. Shutting down audio manager.")
                    # Mark that we're aborting any in-progress work
                    self._abort_transcription = True
                    
                    # Safely stop and close any active stream
                    if current_stream:
                        try: 
                            current_stream.stop()
                            current_stream.close()
                        except Exception as e: 
                            logger.warning(f"WARNING AUDMAN: Error during stream cleanup on exit: {e}")
                    
                    # Clean up the model reference if it exists
                    if hasattr(self, 'model') and self.model is not None:
                        logger.info("INFO AUDMAN: Clearing Whisper model reference in audio manager thread.")
                        self.model = None
                    
                    logger.info("INFO AUDMAN: Audio manager thread exiting")
                    break # Exit the while loop
                else:
                    logger.warning(f"WARNING AUDMAN: Unknown command: {command}")
            except Exception as e:
                logger.error(f"ERROR AUDMAN: Unhandled exception in worker: {e}")
                # Potentially try to reset state or log critical error
                if current_stream: # Attempt to clean up stream on unexpected error
                    try: current_stream.close() 
                    except: pass
                    current_stream = None
                self.is_recording = False # Reset recording state

    def _safe_callback(self, data):
        """Helper method to safely invoke callbacks on the main thread."""
        if self.transcription_callback:
            # Use a timer with a small delay to schedule on main thread
            def invoke_callback():
                self.transcription_callback(data)
            threading.Timer(0.01, invoke_callback).start()

    def start_recording(self):
        logger.debug("DEBUG AUDREC: start_recording called. Queuing 'start' command.")
        self.command_queue.put({"command": "start"})
        return True

    def stop_recording(self, reason="manual_stop"):
        logger.debug(f"DEBUG AUDREC: stop_recording called. Reason: {reason}. Queuing 'stop' command.")
        self.command_queue.put({"command": "stop", "reason": reason})

    def _transcribe_audio_data(self, audio_data_np, reason):
        """Helper method to run transcription, called in a separate thread."""
        logger.debug("Starting transcription process...")
        try:
            # Check abort flag before starting transcription
            if self._abort_transcription:
                logger.debug("Transcription aborted due to shutdown request")
                return
            
            avg_amplitude = np.abs(audio_data_np).mean()
            max_amplitude = np.abs(audio_data_np).max()
            logger.debug(f"Pre-transcription Audio stats - Samples: {len(audio_data_np)}, Mean amp: {avg_amplitude:.6f}, Max amp: {max_amplitude:.6f}")
            
            logger.debug("Running transcription with configured parameters...")
            
            segments, info = self.model.transcribe(
                audio_data_np,
                language=self.transcribe_language,
                beam_size=self.transcribe_beam_size,
                vad_filter=self.transcribe_vad_filter,
                vad_parameters=self.transcribe_vad_parameters,
                temperature=self.transcribe_temperature,
                patience=self.transcribe_patience,
                condition_on_previous_text=self.transcribe_condition_on_previous_text
            )
            
            # Check abort flag again after transcription
            if self._abort_transcription:
                logger.debug("Transcription completed but results discarded due to shutdown")
                return
                
            # Convert segments to text
            transcribed_text = "".join(segment.text for segment in segments).strip()
            
            logger.info(f"INFO: Transcription complete. Detected lang: {info.language} (prob: {info.language_probability:.2f}), Forced lang: {self.transcribe_language}")
            
            self._safe_callback({
                "status": "transcription_complete", 
                "text": transcribed_text, 
                "language": info.language, 
                "reason": reason
            })
        except Exception as e:
            logger.error(f"ERROR: Transcription failed: {e}", exc_info=True)
            self._safe_callback({"status": "error", "reason": reason, "message": f"Error during transcription: {e}"})

    def shutdown(self):
        logger.info("INFO AUDREC: Shutdown called. Setting abort flag and queuing 'exit' command.")
        self._abort_transcription = True
        self.command_queue.put({"command": "exit"})
        
        # Wait for the audio manager thread to finish
        self.audio_manager_thread.join(timeout=3.0) 
        if self.audio_manager_thread.is_alive():
            logger.warning("WARNING AUDREC: Audio manager thread did not exit cleanly after 3 seconds.")
        else:
            logger.info("INFO AUDREC: Audio manager thread exited cleanly.")

        # Clean up the model if it exists to release its resources
        if hasattr(self, 'model') and self.model is not None:
            logger.info("INFO AUDREC: Releasing Whisper model resources.")
            del self.model 
            self.model = None
            logger.info("INFO AUDREC: Whisper model resources released.")