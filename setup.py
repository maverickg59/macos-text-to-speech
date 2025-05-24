from setuptools import setup

APP_NAME = "Ottotone"
APP_SCRIPT = "ottotone/app.py"
VERSION = "0.0.1"  # Should match pyproject.toml

# --- Py2App options ---
# Ensure you have an icon file (e.g., ottotone.icns) in the same directory as setup.py
# or update the path here.
ICONFILE = "ottotone/resources/ottotone.icns"

# TODO: Replace with your unique bundle identifier
BUNDLE_IDENTIFIER = "com.yourcompany.ottotone"

# Packages to include. py2app might not find all of them, especially
# those imported dynamically or via plugins.
# Based on pyproject.toml and common needs for such an app.
PACKAGES = [
    "rumps",
    "sounddevice",
    "faster_whisper",
    "numpy",
    "appdirs",
    "torch",
    "torchaudio",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "onnxruntime",
    "pyobjc", # Include the top-level pyobjc package
    "queue",
    "logging",
    "json",
    "os",
    "sys",
    "platform",
    "threading",
    "math",
    "subprocess",
    "yaml"  # Added to ensure PyYAML is included
]

# Explicitly include necessary PyObjC frameworks
# These are often needed for GUI and system interaction on macOS
INCLUDES = [
    "AppKit",
    "Foundation",
    "Quartz",
    "ApplicationServices",
    "AVFoundation"  # Added for microphone permissions and audio/video
]

OPTIONS = {
    "argv_emulation": False, # True if your app needs to process command-line arguments dropped onto it
    "iconfile": ICONFILE,
    "packages": PACKAGES,
    "includes": INCLUDES,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleGetInfoString": "Ottotone Speech-to-Text",
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": "(c) 2024 Your Name or Company. All rights reserved.", # TODO: Update copyright
        "LSUIElement": True,  # Makes it an agent app (no Dock icon)
        "NSPrincipalClass": "NSApplication",
        "NSAppleEventsUsageDescription": "Ottotone needs to control other applications to paste transcribed text.",
        "NSMicrophoneUsageDescription": "Ottotone needs access to the microphone to record audio for transcription.",
        "NSSpeechRecognitionUsageDescription": "Ottotone uses speech recognition to transcribe audio.", # Though we use our own engine
        # For Sparkle updates (optional, if you implement it later)
        # "SUFeedURL": "YOUR_APPCAST_URL_HERE",
        # "SUPublicDSAKeyFile": "YOUR_DSA_PUBLIC_KEY_FILENAME_HERE",
    },
    # Add any data files your app needs (e.g., models, config templates)
    # 'resources': ['path/to/your/resource_folder_or_file'],
    # Ensure that the CTranslate2 models are bundled if they are not downloaded at runtime
    # This might involve finding where faster-whisper stores them or pre-downloading
    # and including them in 'resources'.
    # For faster-whisper, models are typically downloaded to a cache directory.
    # If you want to bundle them, you'd need to specify their path.
    # Example: 'resources': ['path/to/faster_whisper_models']
}

setup(
    app=[APP_SCRIPT],
    name=APP_NAME,
    version=VERSION,
    author="Chris White", # TODO: Update author
    author_email="chris@chriswhite.rocks", # TODO: Update author email
    description="STT",
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    # install_requires will be handled by pyproject.toml and uv/pip
)