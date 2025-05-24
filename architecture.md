# Ottotone

Ottotone is a lightweight STT App designed for productive dictation without interrupting workflow.

## Features

- record on global hotkey
- transcribe on silence detection
- paste to cursor focus or clipboard (configurable)
- configurable
- - hotkey (default to command+shift+space)
- - silence threshold
- - silence interval
- - model (using all faster-whisper models)
- - output action (paste to cursor focus or copy to clipboard)

## UI

- menu bar icon:
- - /ottotone/resources/ottotone.icns

- menu bar items
- - start recording toggle (when not recording) | stop recording (when recording)
- - select output action toggle (paste to cursor focus) | (copy to clipboard)
- - select model dropdown (allows user to select a different model)
- - check permissions (opens system settings)
- - settings (opens settings window)
- - quit (closes the app)

- settings window
- - record hotkey (allows user to record a new hotkey)
- - set silence threshold (allows user to set a new silence threshold)
- - set silence interval (allows user to set a new silence interval)
- - select model dropdown (allows user to select a different model)
- - select output action toggle (paste to cursor focus) | (copy to clipboard)
- - displays permissions status (granted or not)

## Permissions

Every time the app loads it should check for permissions and show a modal and system settings if any are missing. This modal should guide the user through the process of enabling the necessary permissions. No buttons. No inputs. Just a very simple panel walking the use through the process of enabling the necessary permissions.

- accessibility
- input monitoring
- microphone

## Modules

- app (main entry point)
- audio (audio recording and transcription)
- config (configuration management)
- hotkeys (hotkey management)
- menubar (menu bar icon and menu)
- permissions (permissions management)
- settings (settings window)
