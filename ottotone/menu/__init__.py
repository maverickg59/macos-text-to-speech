"""Menu management module for Ottotone.

This module provides a clean, modular approach to managing menu items
and their interactions with the application state.
"""

from .menu_manager import MenuManager, BaseMenuComponent
from .model_menu import ModelMenu
from .output_menu import OutputMenu
from .settings_menu import SettingsMenu
from .permissions_menu import PermissionsMenu

# Export the main classes for direct import
__all__ = ['MenuManager', 'BaseMenuComponent', 'ModelMenu', 'OutputMenu', 'SettingsMenu', 'PermissionsMenu']
