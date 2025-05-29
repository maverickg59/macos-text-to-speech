"""Permissions menu component for Ottotone."""

import logging
import rumps
from typing import Dict, List, Any, Callable, Optional

from .menu_manager import BaseMenuComponent, MenuManager
from ..config import AppConfig

logger = logging.getLogger(__name__)

# Menu constants
MENU_CHECK_PERMISSIONS = "Check Permissions"

class PermissionsMenu(BaseMenuComponent):
    """Menu component for permission checking.
    
    This component manages the permissions-related menu items.
    
    Attributes:
        permissions_callback: Callback to invoke when permissions check is requested
    """
    
    def __init__(self, menu_manager: MenuManager, config: AppConfig, permissions_callback: Optional[Callable] = None):
        """Initialize the PermissionsMenu component.
        
        Args:
            menu_manager: The parent MenuManager instance
            config: The application configuration
            permissions_callback: Optional callback function to invoke when permissions check is requested
        """
        super().__init__(menu_manager, config)
        self.permissions_callback = permissions_callback
        self.check_permissions_item = None
    
    def get_menu_items(self) -> List[Any]:
        """Create and return permissions menu items.
        
        Returns:
            A list containing the permissions menu items
        """
        self.check_permissions_item = self._create_menu_item(
            MENU_CHECK_PERMISSIONS, 
            callback=self._on_check_permissions
        )
        
        return [self.check_permissions_item]
    
    def update_menu_state(self):
        """Update permissions menu state based on current configuration."""
        # No state to update for this menu
        pass
    
    def _on_check_permissions(self, sender: rumps.MenuItem):
        """Handle check permissions action.
        
        Args:
            sender: The menu item that was clicked
        """
        logger.info("Check permissions requested")
        
        # Notify listeners if callback is provided
        if self.permissions_callback:
            self.permissions_callback()
