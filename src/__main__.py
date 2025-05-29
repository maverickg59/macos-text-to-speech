#!/usr/bin/env python3
"""Main entry point for the Ottotone speech-to-text application.

This module serves as the command-line entry point for the Ottotone application,
which provides speech-to-text capabilities via a macOS menubar app with global hotkeys.
"""

import logging

def main():
    """Run the Ottotone application.
    
    Initializes and launches the menubar application with all its components:
    - Audio recording and transcription
    - Global hotkey management
    - Configuration management
    - Permissions handling
    """
    # Configure basic logging
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Import here to avoid importing everything when just showing help
    from src.app import OttotoneApp
    
    # Create and run the app
    app = OttotoneApp()
    app.run()

if __name__ == "__main__":
    main()
