# Ottotone

A simple voice-to-text transcription tool that uses OpenAI's Whisper model. Just press Cmd+Control+R, speak, and your transcribed text will be automatically copied to your clipboard.

## Features

- 🔊 Automatic silence detection
- 📋 Instant clipboard copy

## Requirements

- macOS (tested on Sonoma 14.0+)
- Homebrew (will be installed if not present)
- Internet connection for initial setup

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/maverickg59/ottotone.git
cd ottotone
```

2. Run the setup script:

```bash
bash setup.sh
```

3. Choose your preferred way to run:
   - **As a macOS app**: The setup script will offer to install Ottotone to your Applications folder
   - **From terminal**: Run `./run.sh`

That's it! Press Cmd+Control+R to start recording, speak your text, and wait for silence or press Cmd+Control+R again to stop. The transcribed text will be automatically copied to your clipboard.

## How It Works

1. Press Cmd+Control+R to start recording
2. Speak your text
3. The recording will automatically stop
4. Transcribed text will be copied to your clipboard
5. Paste anywhere with Cmd+V
6. Runs on your machine only

## Installation Options

### 1. As a macOS App

- During setup, choose 'y' when asked to install to Applications
- Find Ottotone in your Applications folder
- Launch like any other macOS app
- Grant microphone permissions when prompted

### 2. From Terminal

- After setup, run: `./run.sh`
- Or use the built app directly: `open dist/Ottotone.app`

## Troubleshooting

If you encounter any issues:

1. Make sure your microphone is working and properly selected in System Settings
2. Check that you have granted microphone permissions to Ottotone
3. Look at the `ottotone.log` file for detailed error messages
4. Try running the setup script again: `bash setup.sh`

## Development

- Python 3.11 (managed in virtual environment)
- Uses OpenAI's Whisper model for transcription
- Includes test suite: `source venv/bin/activate && python3 -m unittest test_ottotone.py -v`
- Built with PyInstaller for native macOS app

## License

MIT License - Feel free to use and modify as needed.
