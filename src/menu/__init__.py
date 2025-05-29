"""Menu management module for Ottotone.

This module provides a clean, modular approach to managing menu items
and their interactions with the application state. The menu system follows
a component-based architecture where each functional area of the application
has its own menu component that manages its specific menu items.

Key components:
- MenuManager: Central coordinator for all menu components
- BaseMenuComponent: Abstract base class for all menu components
- ModelMenu: Manages Whisper model selection
- OutputMenu: Handles output action selection (clipboard/paste)
- SettingsMenu: Provides access to application settings
- PermissionsMenu: Shows permission status and guidance

Each component is responsible for building its menu items, handling user
interactions, and updating its state based on application events.
"""

from .menu_manager import MenuManager, BaseMenuComponent
from .model_menu import ModelMenu
from .output_menu import OutputMenu
from .settings_menu import SettingsMenu
from .permissions_menu import PermissionsMenu

# Export the main classes for direct import
__all__ = ['MenuManager', 'BaseMenuComponent', 'ModelMenu', 'OutputMenu', 'SettingsMenu', 'PermissionsMenu']
