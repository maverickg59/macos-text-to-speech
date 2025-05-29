# Ottotone - STT

Ottotone is a macOS app that provides quick speech-to-text transcription using Faster Whisper. Record audio via global hotkey with auto-stop on silence detection. Transcribe to clipboard or paste at cursor.

## Prerequisites

- Python 3.12 or higher
- UV package manager

## Running the Application

1.  **Create and Activate a Virtual Environment:**

    ```bash
    uv venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies:**

    ```bash
    uv pip install -e .
    ```

3.  **Run the Application:**

    ```bash
    python3 -m ottotone
    ```

## Building for macOS (.app)

Ottotone includes a smart build script that automatically detects dependencies and creates a standalone macOS application bundle (.app).

1.  **Install Development Dependencies:**

    ```bash
    # Install Python development dependencies
    uv pip install -e ".[dev]"
    ```

    Note: The app now uses native macOS AVFoundation APIs for audio recording, eliminating the need for external dependencies like PortAudio.

2.  **Run the Build Script:**

    ```bash
    # Build the app
    python3 build_app.py
    ```

3.  **What the Build Script Does:**

- Creates a customized py2app configuration
- Bundles the application with all dependencies
- Optionally creates a DMG installer when finished

4.  **App Bundle Location:**
    After building, the standalone app will be available at `dist/Ottotone.app`
5.  **Testing the App Bundle:**
    ```bash
    # Open the application
    open dist/Ottotone.app
    ```

### App Bundle Details

The build script creates an application bundle that includes:

- Bundle identifier and version information
- Menubar app configuration (LSUIElement)
- Required permissions (Microphone usage description)
- All necessary Python dependencies, including Whisper models
- Icon and branding
- **Native Integration**: Uses macOS AVFoundation APIs for audio recording with no external dependencies

## Main Functionalities and Configurable Features

- **Speech-to-Text:** Press `Command+Shift+Space`) to start recording.
- **Configuration Options:**

  - **Copy to Clipboard:** Transcribed text is automatically copied to the clipboard.
  - **Paste at Cursor:** Transcribed text is typed out at the current cursor position.
  - **Model Selection:** Select from different Whisper model sizes (tiny, base, small, medium, large) balancing speed vs accuracy
  - **Silence Threshold:** Configure how quiet (-10 to -50dB) silence needs to be before recording stops automatically
  - **Max Silence Duration:** Configure how long (1-10s) silence needs to be before recording stops automatically
  - **Temperature:** Adjust the randomness of the transcription (0.0-1.0), with lower values being more deterministic
  - **VAD Filter:** Enable/disable Voice Activity Detection to filter out non-speech audio segments

- **Permissions:** The app checks for necessary permissions (Microphone, Accessibility, Input Monitoring for hotkeys) and guides the user to grant them via System Settings if they are missing.

---
