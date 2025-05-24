"""Main menu manager implementation for Ottotone."""

import logging
import rumps
from typing import Dict, List, Optional, Any, Callable

from ..config import AppConfig

logger = logging.getLogger(__name__)

class MenuManager:
    """Manages the application menu structure and interactions.
    
    This class acts as a coordinator for various menu components,
    managing their lifecycle and facilitating communication between
    them and the application.
    
    Attributes:
        config: The application configuration
        app: The rumps App instance this menu is attached to
        menu_components: Dictionary of menu component instances
    """
    
    def __init__(self, app: rumps.App, config: AppConfig):
        """Initialize the MenuManager.
        
        Args:
            app: The rumps App instance this menu is attached to
            config: The application configuration
        """
        self.app = app
        self.config = config
        self.menu_components = {}
        self._main_menu_items = {}
    
    def register_component(self, name: str, component: 'BaseMenuComponent'):
        """Register a menu component with the manager.
        
        Args:
            name: Unique identifier for the component
            component: The menu component instance
        """
        self.menu_components[name] = component
        logger.debug(f"Registered menu component: {name}")
    
    def build_menu(self) -> List[Any]:
        """Build and return the complete menu structure.
        
        Returns:
            A list of menu items that can be assigned to a rumps App's menu
        """
        menu_items = []
        
        # Let each component contribute its items
        for name, component in self.menu_components.items():
            items = component.get_menu_items()
            if items:
                menu_items.extend(items)
                # Store reference to main menu items for later updates
                for item in items:
                    if isinstance(item, tuple) and len(item) == 2:
                        self._main_menu_items[item[0]] = item[1]
                    elif isinstance(item, rumps.MenuItem):
                        self._main_menu_items[item.title] = item
        
        logger.debug(f"Built menu with {len(menu_items)} top-level items")
        return menu_items
    
    def update_all_menus(self):
        """Update the state of all menu components."""
        for name, component in self.menu_components.items():
            component.update_menu_state()
        logger.debug("Updated all menu states")
    
    def get_menu_item(self, title: str) -> Optional[rumps.MenuItem]:
        """Get a menu item by its title.
        
        Args:
            title: The title of the menu item to retrieve
            
        Returns:
            The menu item if found, None otherwise
        """
        return self._main_menu_items.get(title)
    
    def handle_config_change(self):
        """Handle configuration changes by updating menus."""
        self.update_all_menus()
        
    def bind_callback(self, menu_title: str, callback: Callable):
        """Bind a callback function to a menu item.
        
        Args:
            menu_title: The title of the menu item
            callback: The callback function to bind
        """
        menu_item = self.get_menu_item(menu_title)
        if menu_item and isinstance(menu_item, rumps.MenuItem):
            menu_item.set_callback(callback)
            logger.debug(f"Bound callback to menu item: {menu_title}")
        else:
            logger.warning(f"Cannot bind callback: menu item not found - {menu_title}")


class BaseMenuComponent:
    """Base class for all menu components.
    
    Menu components are responsible for creating and updating
    a specific section of the application menu.
    
    Attributes:
        menu_manager: Reference to the parent MenuManager
        config: Reference to the application configuration
    """
    
    def __init__(self, menu_manager: MenuManager, config: AppConfig):
        """Initialize a BaseMenuComponent.
        
        Args:
            menu_manager: The parent MenuManager instance
            config: The application configuration
        """
        self.menu_manager = menu_manager
        self.config = config
        self.menu_items = {}
    
    def get_menu_items(self) -> List[Any]:
        """Get the menu items for this component.
        
        Returns:
            A list of menu items to be added to the application menu
        """
        raise NotImplementedError("Menu components must implement get_menu_items")
    
    def update_menu_state(self):
        """Update the state of menu items based on current configuration."""
        raise NotImplementedError("Menu components must implement update_menu_state")
    
    def _create_menu_item(self, title: str, callback: Optional[Callable] = None) -> rumps.MenuItem:
        """Create a menu item and store it for later reference.
        
        Args:
            title: The title of the menu item
            callback: Optional callback function for the menu item
            
        Returns:
            The created menu item
        """
        item = rumps.MenuItem(title, callback=callback)
        self.menu_items[title] = item
        return item
