"""Output action menu component for Ottotone."""

import logging
import rumps
from typing import Dict, List, Any, Callable, Optional

from .menu_manager import BaseMenuComponent, MenuManager
from ..config import AppConfig

logger = logging.getLogger(__name__)

# Output action constants
MENU_OUTPUT_ACTION = "Output Action"
MENU_COPY_TO_CLIPBOARD = "Copy to Clipboard"
MENU_PASTE_AT_CURSOR = "Paste at Cursor"

OUTPUT_ACTION_CLIPBOARD = "clipboard"
OUTPUT_ACTION_PASTE_AT_CURSOR = "paste_at_cursor"

class OutputMenu(BaseMenuComponent):
    """Menu component for output action selection.
    
    This component manages the output action menu items and
    handles switching between output modes (clipboard/paste at cursor).
    
    Attributes:
        output_action_callback: Callback to invoke when output action is changed
    """
    
    def __init__(self, menu_manager: MenuManager, config: AppConfig, output_action_callback: Optional[Callable] = None):
        """Initialize the OutputMenu component.
        
        Args:
            menu_manager: The parent MenuManager instance
            config: The application configuration
            output_action_callback: Optional callback function to invoke when output action is changed
        """
        super().__init__(menu_manager, config)
        self.output_action_callback = output_action_callback
        self.output_menu_item = None
        self.copy_menu_item = None
        self.paste_menu_item = None
    
    def get_menu_items(self) -> List[Any]:
        """Create and return output action menu items.
        
        Returns:
            A list containing the output action menu
        """
        # Create main menu item for output action
        output_menu_item = rumps.MenuItem(MENU_OUTPUT_ACTION)
        
        # Create submenu items for radio button behavior
        self.copy_menu_item = rumps.MenuItem(
            MENU_COPY_TO_CLIPBOARD, 
            callback=lambda sender: self._on_output_action_selected(sender, OUTPUT_ACTION_CLIPBOARD)
        )
        
        self.paste_menu_item = rumps.MenuItem(
            MENU_PASTE_AT_CURSOR, 
            callback=lambda sender: self._on_output_action_selected(sender, OUTPUT_ACTION_PASTE_AT_CURSOR)
        )
        
        # Add submenu items directly to the output menu
        output_menu_item.add(self.copy_menu_item)
        output_menu_item.add(self.paste_menu_item)
        
        # Update menu state initially - ensure one option is always selected
        current_action = self.config.ui.get_output_action()
        # Set default if no valid selection
        if current_action not in [OUTPUT_ACTION_CLIPBOARD, OUTPUT_ACTION_PASTE_AT_CURSOR]:
            current_action = OUTPUT_ACTION_CLIPBOARD
            self.config.ui.set_output_action(current_action)
            
        # Initialize checkmarks
        self.copy_menu_item.state = 1 if current_action == OUTPUT_ACTION_CLIPBOARD else 0
        self.paste_menu_item.state = 1 if current_action == OUTPUT_ACTION_PASTE_AT_CURSOR else 0
        logger.debug(f"Initial output menu state - Copy: {self.copy_menu_item.state}, Paste: {self.paste_menu_item.state}")
        
        return [output_menu_item]
    
    def update_menu_state(self):
        """Update checkmarks based on current output action."""
        current_action = self.config.ui.get_output_action()
        logger.debug(f"Updating output menu state. Current action: {current_action}")
        
        # Set checkmarks on appropriate action
        if self.copy_menu_item and self.paste_menu_item:
            # In rumps, True = 1 (on) and False = 0 (off) for menu item state
            self.copy_menu_item.state = 1 if current_action == OUTPUT_ACTION_CLIPBOARD else 0
            self.paste_menu_item.state = 1 if current_action == OUTPUT_ACTION_PASTE_AT_CURSOR else 0
            
            # Force a refresh of the menu
            logger.debug(f"Copy menu state: {self.copy_menu_item.state}, Paste menu state: {self.paste_menu_item.state}")
    
    def _on_output_action_selected(self, sender: rumps.MenuItem, action: str):
        """Handle output action selection event for radio button behavior.
        
        Args:
            sender: The menu item that was clicked
            action: The output action identifier
        """
        # Update configuration first
        self.config.ui.set_output_action(action)
        logger.debug(f"Setting output action to: {action}")
        
        # Update menu items - use a direct, simple approach
        try:
            # Update both menu items directly
            if hasattr(self, 'copy_menu_item') and self.copy_menu_item is not None:
                self.copy_menu_item.state = 1 if action == OUTPUT_ACTION_CLIPBOARD else 0
                logger.debug(f"Copy menu item state: {self.copy_menu_item.state}")
            else:
                logger.warning("Copy menu item is not initialized")
                
            if hasattr(self, 'paste_menu_item') and self.paste_menu_item is not None:
                self.paste_menu_item.state = 1 if action == OUTPUT_ACTION_PASTE_AT_CURSOR else 0
                logger.debug(f"Paste menu item state: {self.paste_menu_item.state}")
            else:
                logger.warning("Paste menu item is not initialized")
                
        except Exception as e:
            logger.error(f"Error updating menu items: {e}")
            
        # Also update the sender's state directly
        sender.state = 1
            
        # Get current action for logging only
        current_action = self.config.ui.get_output_action()
        logger.info(f"Set output action to: {action} (was: {current_action})")
        
        # Notify listeners if callback is provided
        if self.output_action_callback:
            self.output_action_callback(action)
        
        # Log final state for debugging
        try:
            logger.debug(f"Final menu state - Copy: {self.copy_menu_item.state}, Paste: {self.paste_menu_item.state}")
        except:
            logger.debug("Could not log menu states")
