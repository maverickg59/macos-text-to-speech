#!/usr/bin/env python3
"""Main entry point for the Ottotone application.

This module provides the command-line interface for the Ottotone application.
"""

def main():
    """Run the Ottotone application."""
    
    # Import here to avoid importing everything when just showing help
    from .app import OttotoneApp
    
    app = OttotoneApp()
    app.run()

if __name__ == "__main__":
    main()
