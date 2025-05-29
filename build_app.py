#!/usr/bin/env python3
"""Ottotone macOS App Builder

This script:
1. Creates a temporary py2app config
2. Builds the app bundle
3. Packages it as a DMG (optional)

"""

import os
import sys
import subprocess
import shutil

def run_command(cmd, cwd=None, env=None):
    """Run a command and return the output."""
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def create_build_setup():
    """Create a setup.py file for py2app."""
    setup_content = """
from setuptools import setup

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'ottotone/resources/icon.icns',
    'plist': {
        'CFBundleName': 'Ottotone',
        'CFBundleDisplayName': 'Ottotone',
        'CFBundleIdentifier': 'com.ottotone.speech-to-text',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSBackgroundOnly': True,
        'LSUIElement': True,
        'NSHumanReadableCopyright': '© 2025 Chris White',
        'NSMicrophoneUsageDescription': 'Ottotone needs microphone access to record and transcribe your speech.',
    },
    'packages': [
        'rumps',
        'faster_whisper',
        'av',
        'numpy',
        'torch',
        'torchaudio',
        'ctranslate2',
        'tokenizers',
        'huggingface_hub',
        'pyobjc',
        'AppKit',
        'Quartz',
        'Foundation',
        'ApplicationServices',
        'AVFoundation',
        'libdispatch'
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'sounddevice'
    ],
    'site_packages': True,
    'dylib_excludes': [
        'libgcc_s.1.dylib',
        'libstdc++.6.dylib',
        'libSystem.dylib',
        'libportaudio.2.dylib'
    ],
}

setup(
    app=['ottotone/__main__.py'],
    data_files=['README.md', 'LICENSE'],
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    name="Ottotone"
)
"""
    
    # Write the setup file
    with open('setup_build.py', 'w') as f:
        f.write(setup_content)
    
    print("Created build setup file: setup_build.py")


def build_app():
    """Build the macOS app bundle."""
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Run py2app with our custom setup
    print("Building application bundle...")
    run_command("python setup_build.py py2app")
    
    # Clean up
    os.remove('setup_build.py')
    
    print("Application bundle created at: dist/Ottotone.app")


def create_dmg():
    """Create a DMG installer."""
    print("Creating DMG installer...")
    run_command('hdiutil create -volname "Ottotone" -srcfolder dist/Ottotone.app -ov -format UDZO Ottotone.dmg')
    print("DMG installer created: Ottotone.dmg")


def main():
    print("==== Ottotone macOS App Builder ====")
    
    # Create build setup
    create_build_setup()
    
    # Build the app
    build_app()
    
    # Ask if user wants to create DMG
    while True:
        response = input("Do you want to create a DMG installer? (y/n): ").lower()
        if response in ['y', 'yes']:
            create_dmg()
            break
        elif response in ['n', 'no']:
            break
        else:
            print("Please enter 'y' or 'n'")
    
    print("Build process complete!")


if __name__ == "__main__":
    main()
