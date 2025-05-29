# Ottotone - Speech-to-Text Menubar App for macOS

Ottotone is a powerful macOS menubar application that provides quick and efficient speech-to-text transcription using the faster-whisper library. It enables users to seamlessly record audio via a global hotkey, automatically stop recording when silence is detected, and output the transcribed text either to the clipboard or directly to the cursor position.

## Key Features

- **Global Hotkey Support**: Trigger recording with a customizable global hotkey (default: Command+Shift+Space)
- **Intelligent Silence Detection**: Automatically stops recording after detecting silence following speech
- **Multiple Whisper Models**: Choose from different model sizes (tiny, base, small, medium, large) to balance speed vs. accuracy
- **Flexible Output Options**: Select between "Copy to Clipboard" or "Paste at Cursor" modes
- **Comprehensive Permission Management**: Built-in handling of microphone, accessibility, and input monitoring permissions
- **Configurable Transcription Settings**: Adjust silence threshold, max silence duration, temperature, and VAD filtering
- **Native macOS Integration**: Uses native macOS APIs through pyobjc for menubar integration and keyboard events

## System Requirements

- macOS 10.15 (Catalina) or later
- Python 3.12 or higher for development
- UV package manager (recommended) or pip

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
    python3 -m src
    ```

## Building for macOS (.app)

Ottotone includes a smart build script that automatically detects dependencies and creates a standalone macOS application bundle (.app).

1.  **Install Development Dependencies:**

    ```bash
    # Install Python development dependencies
    uv pip install -e ".[dev]"
    ```

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

## Architecture

Ottotone follows a modular architecture with clean separation of concerns between different components:

### Core Components

- **OttotoneApp**: Main application class that orchestrates all components
- **AudioRecorder**: Handles audio recording and transcription using faster-whisper
- **PermissionsManager**: Manages and checks for required system permissions
- **HotkeyManager**: Handles global hotkey detection via Quartz event taps
- **AppConfig**: Manages application configuration and persistence

### Menu System

The menubar interface uses a component-based architecture where each functional area has its own menu component:

- **MenuManager**: Central coordinator for all menu components
- **ModelMenu**: Manages Whisper model selection
- **OutputMenu**: Handles output action selection (clipboard/paste)
- **SettingsMenu**: Provides access to application settings

### Technical Notes

- **MPS Limitation**: faster-whisper does not support MPS (Apple Silicon) acceleration, so the application forces CPU mode for transcription on all Macs
- **Component Independence**: Components communicate through well-defined interfaces and callbacks, minimizing tight coupling
- **Permission Handling**: The application guides users through obtaining permissions with detailed instructions and direct links to System Settings

## Development Guidelines

1. **Coding Standards**
   - Follow PEP 8 for Python code style
   - Use absolute imports to avoid circular dependencies
   - Document classes and methods with detailed docstrings

2. **Testing**
   - Strive for a sensible level of code coverage as close to 100% as possible using unit tests
   - Use vitest for unit testing
   - Tests should be placed in the `__tests__` directory only
   - Never modify source code to make tests pass

3. **Error Handling**
   - Use proper logging at appropriate levels (debug, info, warning, error)
   - Gracefully handle failures in user permissions or hardware access
   - Provide user-friendly error messages and guidance

---
