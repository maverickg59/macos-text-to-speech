"""Model selection menu component for Ottotone."""

import logging
import rumps
from typing import Dict, List, Any, Callable, Optional

from .menu_manager import BaseMenuComponent, MenuManager
from ..config import AppConfig

logger = logging.getLogger(__name__)

# Available Whisper models (from tiny to large)
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
MENU_SELECT_MODEL = "Select Model"

class ModelMenu(BaseMenuComponent):
    """Menu component for Whisper model selection.
    
    This component manages the model selection menu items and
    handles model switching.
    
    Attributes:
        model_callback: Callback to invoke when model is changed
    """
    
    def __init__(self, menu_manager: MenuManager, config: AppConfig, model_callback: Optional[Callable] = None):
        """Initialize the ModelMenu component.
        
        Args:
            menu_manager: The parent MenuManager instance
            config: The application configuration
            model_callback: Optional callback function to invoke when model is changed
        """
        super().__init__(menu_manager, config)
        self.model_callback = model_callback
        self.model_menu_item = None
        self.model_submenu_items = {}
    
    def get_menu_items(self) -> List[Any]:
        """Create and return model selection menu items.
        
        Returns:
            A list containing the model selection menu
        """
        # Create main model selector menu
        self.model_menu_item = rumps.MenuItem(MENU_SELECT_MODEL)
        
        # Create model submenu items and add them directly to avoid tuple format issues
        for model_name in AVAILABLE_MODELS:
            item = rumps.MenuItem(model_name, callback=self._on_model_selected)
            self.model_submenu_items[model_name] = item
            self.model_menu_item.add(item)
        
        # Update menu state initially
        self.update_menu_state()
        
        return [self.model_menu_item]
    
    def update_menu_state(self):
        """Update checkmarks based on current model selection."""
        current_model = self.config.audio.get_selected_model()
        logger.debug(f"Updating model menu state. Current model: {current_model}")
        
        # Set checkmarks on appropriate model - explicitly use 1 and 0 for state
        for model_name, item in self.model_submenu_items.items():
            item.state = 1 if model_name == current_model else 0
            
        # Log states for debugging
        checked_items = [name for name, item in self.model_submenu_items.items() if item.state == 1]
        logger.debug(f"Models with checkmarks: {checked_items}")
    
    def _on_model_selected(self, sender: rumps.MenuItem):
        """Handle model selection event.
        
        Args:
            sender: The menu item that was clicked
        """
        model_name = sender.title
        current_model = self.config.audio.get_selected_model()
        
        # Update the model even if it's already selected (to make sure menu state is consistent)
        logger.info(f"Setting model to {model_name} (was {current_model})")
        
        # Update configuration
        self.config.audio.set_selected_model(model_name)
        
        # First clear all checkmarks
        for name, item in self.model_submenu_items.items():
            item.state = 0
        
        # Set the checkmark for the selected model
        # First update the sender directly - this is crucial for visual feedback
        sender.state = 1
        
        # Also update our stored reference if we have one
        if model_name in self.model_submenu_items:
            self.model_submenu_items[model_name].state = 1
            
        # Log the state for debugging
        checked_items = [name for name, item in self.model_submenu_items.items() if item.state == 1]
        logger.debug(f"After model selection - Models with checkmarks: {checked_items}")
        
        # Notify listeners if callback is provided and the model actually changed
        if model_name != current_model and self.model_callback:
            self.model_callback(model_name)
            logger.info(f"Model changed to: {model_name}")
        else:
            logger.debug(f"Model selection confirmed: {model_name}")

    def get_available_models(self) -> List[str]:
        """Get the list of available models.
        
        Returns:
            List of available model names
        """
        return AVAILABLE_MODELS.copy()
