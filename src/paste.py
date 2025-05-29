"""Handles pasting text at the current cursor location on macOS.

This module provides functionality to paste text at the current cursor position
in any application by simulating keyboard events (Command+V) using Quartz.

This approach requires Accessibility permission to be granted to the application
as it simulates keyboard events at the system level.

Typical usage:
    paste_text_at_cursor("Text to be pasted")
"""

import platform
import time
import logging

# Import centralized constants
from src.constants import (
    PLATFORM_DARWIN,
    KEY_CODE_V, KEY_CODE_COMMAND,
    EVENT_FLAG_COMMAND,
    PASTE_DELAY_SEC
)

logger = logging.getLogger(__name__)

if platform.system() == PLATFORM_DARWIN:
    import Quartz
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGHIDEventTap,
        CGEventSourceCreate,
        kCGEventSourceStateHIDSystemState
    )
    try:
        # Try importing from HIToolbox first
        from Quartz.HIToolbox import kVK_ANSI_V, kVK_Command
    except ImportError:
        # Fallback to raw keycodes from our centralized constants
        logger.debug("kVK_ANSI_V or kVK_Command not found in Quartz.HIToolbox. Using constants from src.constants.")
        kVK_ANSI_V = KEY_CODE_V  # Virtual keycode for 'V'
        kVK_Command = KEY_CODE_COMMAND  # Virtual keycode for Command
        
    from AppKit import NSPasteboard, NSStringPboardType
else:
    Quartz = None
    NSPasteboard = None
    NSStringPboardType = None

def _press_key(source, keycode, flags, is_down):
    """Helper to create and post a keyboard event."""
    event = CGEventCreateKeyboardEvent(source, keycode, is_down)
    CGEventSetFlags(event, flags)
    CGEventPost(kCGHIDEventTap, event)
    # Small delay between key events, especially for modifiers
    time.sleep(PASTE_DELAY_SEC)

def paste_text_at_cursor(text_to_paste):
    """Pastes text at the current cursor position using Command+V simulation.
    
    This function works by temporarily storing the text in the clipboard,
    simulating a Command+V keyboard shortcut to paste the text at the current
    cursor position, and then restoring the original clipboard content.
    
    Args:
        text_to_paste (str): The text to paste at the current cursor position
        
    Returns:
        bool: True if the paste operation was successful, False otherwise
        
    Note:
        Requires Accessibility permission to be granted to the application
        to simulate keyboard events. If this permission is not granted,
        the function will fail.
    """
    if platform.system() != "Darwin" or not Quartz or not NSPasteboard:
        logger.warning("Paste at cursor (via clipboard) is only supported on macOS.")
        return False

    # Store original clipboard content to restore it later
    original_clipboard_content = None
    pasteboard = NSPasteboard.generalPasteboard()
    if pasteboard:
        original_clipboard_content = pasteboard.stringForType_(NSStringPboardType)

    try:
        # 1. Copy text to clipboard
        pasteboard.clearContents() # Clear previous content
        success = pasteboard.setString_forType_(text_to_paste, NSStringPboardType)
        if not success:
            logger.error("Failed to set string on pasteboard.")
            return False
        logger.info(f"Text copied to clipboard: '{text_to_paste[:50] + '...' if len(text_to_paste) > 50 else text_to_paste}'")
        time.sleep(0.05) # Ensure clipboard has the text before simulating paste

        # 2. Simulate Command+V to paste
        # CGEventSourceRef is a CFType. PyObjC typically handles CF object memory management (retain/release)
        # automatically when the Python wrapper object goes out of scope. Explicit CFRelease is generally not needed
        # for short-lived objects created and used within a single function scope unless issues are observed.
        source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        if not source:
            logger.error("Failed to create event source for pasting. Accessibility permission might be missing.")
            # Attempt to restore clipboard before returning
            if original_clipboard_content is not None:
                pasteboard.clearContents()
                pasteboard.setString_forType_(original_clipboard_content, NSStringPboardType)
            return False

        # Simulate Command down
        _press_key(source, kVK_Command, EVENT_FLAG_COMMAND, True)
        
        # Simulate V down
        _press_key(source, kVK_ANSI_V, EVENT_FLAG_COMMAND, True)
        
        # Simulate V up
        _press_key(source, kVK_ANSI_V, EVENT_FLAG_COMMAND, False)
        
        # Simulate Command up
        _press_key(source, kVK_Command, 0, False) 

        logger.info("Command+V simulated successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to paste text using clipboard and Command+V: {e}", exc_info=True)
        # Attempt to restore original clipboard content in case of error during paste simulation
        try:
            if original_clipboard_content is not None:
                pasteboard = NSPasteboard.generalPasteboard() 
                pasteboard.clearContents()
                pasteboard.setString_forType_(original_clipboard_content, NSStringPboardType)
                logger.info("Original clipboard content restored after error.")
            else:
                # If we couldn't get original, at least clear the one we put
                pasteboard = NSPasteboard.generalPasteboard()
                pasteboard.clearContents()
                logger.info("Clipboard cleared after error (original content was not available).")
        except Exception as e_clear:
            logger.error(f"Could not restore/clear pasteboard after paste error: {e_clear}", exc_info=True)
        return False

if __name__ == '__main__':
    # Setup basic logging for the test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if platform.system() == "Darwin":
        logger.info("Testing paste function (clipboard method) in 3 seconds...")
        logger.info("Focus a text input field NOW!")
        time.sleep(3)
        
        test_string = "Hello, Clipboard! 123\nThis is a new line with TABS:\tTest.\nAnd some sYmBoLs: !@#$%^&*()_+"
        logger.info(f"Pasting: '{test_string}'")
        
        if paste_text_at_cursor(test_string):
            logger.info("Paste test successful.")
        else:
            logger.error("Paste test failed.")

        logger.info("\nTesting with a simpler string:")
        time.sleep(1)
        test_string_simple = "abc 123 ?/."
        logger.info(f"Pasting: '{test_string_simple}'")
        paste_text_at_cursor(test_string_simple)

    else:
        logger.info("Paste test is for macOS only.")
