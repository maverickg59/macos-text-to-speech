"""Handles pasting text at the current cursor location on macOS."""

import platform
import time
import logging

logger = logging.getLogger(__name__)

if platform.system() == "Darwin":
    import Quartz
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGHIDEventTap,
        CGEventSourceCreate,
        kCGEventSourceStateHIDSystemState,
        kCGEventFlagMaskCommand  # Command key modifier flag
    )
    try:
        # Try importing from HIToolbox first
        from Quartz.HIToolbox import kVK_ANSI_V, kVK_Command
    except ImportError:
        # Fallback to raw keycodes if specific constants are not found
        logger.debug("kVK_ANSI_V or kVK_Command not found in Quartz.HIToolbox. Using raw keycodes.")
        kVK_ANSI_V = 0x09  # Virtual keycode for 'V'
        kVK_Command = 0x37 # Virtual keycode for Command
        
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
    time.sleep(0.01) 

def paste_text_at_cursor(text_to_paste):
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
        _press_key(source, kVK_Command, kCGEventFlagMaskCommand, True)
        
        # Simulate V down
        _press_key(source, kVK_ANSI_V, kCGEventFlagMaskCommand, True)
        
        # Simulate V up
        _press_key(source, kVK_ANSI_V, kCGEventFlagMaskCommand, False)
        
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
