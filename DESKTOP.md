# Mousyst desktop keyboard

Extract the full bundle and run its executable. Keep _internal beside the EXE.
Mousyst starts in the Windows tray. Middle-click a text field to open or hide the
keyboard. Close hides it; right-click its tray icon to open Settings or Quit.
Launching another copy opens Settings in the existing instance.

Click letters or hold left-click and swipe a word. Right-click a letter for its
small printed secondary symbol. Hold a letter or Backspace to repeat. Click
Ctrl/Alt/Win/Shift, then a key to execute a real shortcut. Modifiers clear after
the next key. Shortcuts operate in the focused target application, including
Ctrl+C/V and Win+Shift+S. There is no local practice clipboard in this mode.

Tap Space for a space; hold or drag it to move the caret horizontally. Arrow keys
move vertically. Scroll over the candidate bar to replace the last word, or click
an alternative. Undo removes the last owned swipe. Alternatives are disabled when
the destination does not expose a verifiable caret range through UI Automation.
Moving the caret or changing the field invalidates replacement.

ABC/123 replaces the main key area with symbol rows or a calculator-style numpad;
it does not expand the keyboard. The in-place format button switches between
symbols and numpad, and ABC restores letters. The gear opens
Settings: choose Compact/Standard/Full, size, and optional
predictive click assistance. Colors, repeat delay/interval, scrub sensitivity,
and per-letter symbols have normal graphical controls. Color buttons open a
color picker; timing uses stepper controls. Import config and Export config
handle optional JSON files without exposing a code editor in Settings.
Settings are saved to %APPDATA%/Mousyst/settings.json. Invalid settings preserve
the last valid configuration.

Automatic opening has been removed. Use middle-click to summon the keyboard.
Legacy auto-open preferences in imported configurations are discarded.
In password fields, word prediction and adaptive aiming are disabled.
Settings may take focus: after closing them, click the destination
field and middle-click again to resume.

Keyboard controls use matching drawn line icons. Swipe feedback is a smoothed,
bounded recent trail with a 240 ms fade; it does not retain the full visual path.
The recognizer still receives the original input coordinates.
The suggestion strip reserves three fixed slots even when empty, so clearing
suggestions with Backspace does not move the keyboard or Enter key. Settings
uses the same rounded dark controls and line icons as the keyboard.

The keyboard is a Windows x64 preview. Custom editors, games, and elevated targets
may expose limited accessibility or reject input. The application reports blocked
input instead of deliberately redirecting it. UI Automation can occasionally time
out; manual activation remains available. Do not rely on candidate replacement in
controls where it is disabled. Full-layout sizing and mixed-DPI behavior need
broader hardware checks. No user typing-speed advantage has been established.

No production text or clipboard history is saved. Inference and configuration
are local. The bundled vocabulary includes its attribution and licenses.

Build: ./build-preview.ps1 -Desktop -BundleName MousystDesktop
Source: python src/desktop_app.py
Isolated UI smoke: python src/desktop_app.py --smoke-test
Disposable native input test: python tests/desktop_adapter_smoke.py
