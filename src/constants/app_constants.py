"""Application-wide constants for Ottotone.

This module contains application-wide constants like app metadata,
default values, and general configuration settings.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Find the project root directory (where .env should be located)
project_root = Path(__file__).resolve().parent.parent.parent

# Try to find and load the .env file
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    logger.info(f"Found .env file at: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    # If find_dotenv fails, try explicit path from project root
    potential_env = os.path.join(project_root, ".env")
    if os.path.exists(potential_env):
        logger.info(f"Loading .env from explicit path: {potential_env}")
        load_dotenv(potential_env)
    else:
        logger.warning(f"No .env file found at {potential_env}")

# Application metadata
APP_NAME = "Ottotone"
APP_AUTHOR = "Ottobots"
APP_VERSION = "0.0.1"
APP_LICENSE = "MIT"

# UI constants
DEFAULT_TITLE = "🎙️"  # Default menu bar title when no icon is used
MENU_ICON_FILE = "ottotone.png"  # Icon for menu bar
APP_ICON_FILE = "ottotone.icns"  # Icon for dock
RESOURCES_DIR = "resources"  # Directory containing app resources

# Platform identifiers
PLATFORM_DARWIN = "Darwin"  # Platform identifier for macOS

# Development mode flag - check environment variable first, fallback to False
dev_env_value = os.getenv("OTTOTONE_DEV_MODE", "")
DEV_MODE = dev_env_value.lower() == "true"

# Log whether dev mode is enabled
logger.info(f"Development mode: {DEV_MODE} (Environment value: '{dev_env_value}')")

# Also handle command-line --dev flag
if "--dev" in sys.argv:
    logger.info("Development mode enabled via command-line flag")
    DEV_MODE = True
