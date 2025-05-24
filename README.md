# Ottotone - Speech-to-Text Menubar App

Ottotone is a macOS menubar application that provides quick speech-to-text transcription using Faster Whisper. It allows users to record audio via a global hotkey or menu click and then copies the transcribed text to the clipboard or pastes it directly at the cursor location.

## Running the Application

1.  **Create and Activate a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies:**
    Make sure you have `portaudio` installed for `sounddevice`:
    ```bash
    brew install portaudio
    ```
    Then, install the Python packages from your `requirements.txt` file (ensure this file is up-to-date):
    ```bash
    pip install -r requirements.txt 
    ```
    *If `requirements.txt` is not present or up-to-date, you might need to manually install: `rumps faster-whisper sounddevice pyobjc pyperclip`.*

3.  **Run the Application:**
    ```bash
    python -m ottotone
    ```
    Or, if your `__main__.py` is set up to call `OttotoneApp().run()`:
    ```bash
    python ottotone
    ```

## Building for macOS (.app)

To create a standalone `.app` bundle for macOS, you can use `pyinstaller`.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Bundle the Application:**
    Navigate to the root directory of your project (where `setup.py` or your main script `__main__.py` is located).

    You will need a `.spec` file to correctly bundle a `rumps` application and include necessary data like models. If you don't have one, `pyinstaller` can generate a basic one first.

    Run the following command. You may need to adjust paths and included data based on your project structure, especially for the Whisper models.

    ```bash
    pyinstaller --windowed --name Ottotone --icon=your_icon.icns \
                --add-data="path/to/your/whisper/models/*:whisper_models" \
                --hidden-import="_cffi_backend" \
                --hidden-import="sounddevice._sounddevice_data" \
                --hidden-import="pyobjc" \
                --collect-all "rumps" \
                ottotone/__main__.py
    ```

    **Explanation of options:**
    *   `--windowed`: Essential for macOS GUI applications; prevents a terminal window from showing.
    *   `--name Ottotone`: Sets the name of your application.
    *   `--icon=your_icon.icns`: (Optional) Specify a `.icns` file for your app icon.
    *   `--add-data="path/to/your/whisper/models/*:whisper_models"`: This is crucial. You need to tell PyInstaller to bundle your Whisper model files. Adjust `path/to/your/whisper/models/*` to where your models are stored locally (e.g., `~/.cache/faster_whisper/`) and `whisper_models` to the target directory name within the app bundle. Your application code will need to look for models in this bundled path.
    *   `--hidden-import="_cffi_backend"`: Often needed by `sounddevice`.
    *   `--hidden-import="sounddevice._sounddevice_data"`: May be needed.
    *   `--hidden-import="pyobjc"`: Ensures PyObjC components are included.
    *   `--collect-all "rumps"`: Ensures all `rumps` necessary files are included.
    *   `ottotone/__main__.py`: Your main application script.

    This will create a `dist` folder containing `Ottotone.app`.

3.  **Important Considerations for Models:**
    *   The `--add-data` path for models is critical. Faster Whisper typically downloads models to a cache directory (e.g., `~/.cache/faster_whisper`). You'll need to point to this location or copy the models into your project and bundle them from there.
    *   Your application code (specifically where `AudioRecorder` or `faster-whisper` loads the model) might need to be adjusted to look for models in a relative path within the app bundle when it's running as a packaged app. PyInstaller sets `sys._MEIPASS` to the path of the bundled resources.

## Main Functionalities and Configurable Features

*   **Speech-to-Text:** Click the menubar icon or use the global hotkey (default: `Command+Shift+Space`) to start/stop recording. The app uses Faster Whisper for transcription.
*   **Output Actions:**
    *   **Copy to Clipboard:** Transcribed text is automatically copied to the clipboard.
    *   **Paste at Cursor:** Transcribed text is typed out at the current cursor position (requires Accessibility permission).
    *   *This can be configured via the app's menubar menu.*
*   **Whisper Model Selection:** Choose different Faster Whisper model sizes (e.g., tiny, base, small) from the menu. Larger models are more accurate but slower and require more resources. The selected model is saved in the configuration.
*   **Permissions Guidance:** The app checks for necessary permissions (Microphone, Accessibility, Input Monitoring for hotkeys) and guides the user to grant them via System Settings if they are missing.
*   **Global Hotkey:** Toggle recording from anywhere using a configurable global hotkey.

---