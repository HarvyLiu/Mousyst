# Mousyst — desktop radial typing

A Windows mouse-operated keyboard with a Python gesture engine and Qt Quick UI.
Rounded vector sectors, alpha transparency, soft shadows, and animated highlights.

## Run the portable app

Extract the entire ZIP and open `Mousyst/Mousyst.exe`. Keep `_internal` beside it.
Python and Qt do not need to be installed. Mousyst starts in the Windows system
tray, near the clock. Its temporary logo is a pale green `m`. If Windows hides
it, click the taskbar's upward arrow to find it. Run only one copy at a time.

- Middle-click in a text field to open the keyboard immediately.
- Click the tray icon, or right-click it and choose **Show Mousyst**, to open the panel.
- Closing or minimizing the panel hides it to the tray; typing remains available.
- Right-click the tray icon and choose **Quit Mousyst** to exit completely and
  restore ordinary middle-click behavior.

If Windows has no system tray available, Mousyst shows its panel and closing it exits.

1. Click a text field in another app to put its caret where you want to type.
2. Middle-click to summon the keyboard around your cursor (adjusted to fit the screen).
3. Visit the center, move through a letter group, then cross a letter's outer edge.
   The two side edges of the fan also enter its first/last letter (such as A/E).
4. Return to the center before the next entry. Returning early cancels selection.
5. Space and Backspace enter at the first ring's outer edge; they have no outer fan.
6. Middle-click again, press Esc, or use the overlay's × to hide it.

The overlay does not take keyboard focus. Switching foreground apps automatically
hides it; middle-click again in the desired app. Middle clicks are reserved for
Mousyst while it runs; scrolling is unaffected. The center displays MOUSYST until
you enter something, then keeps the last entered character visible. Space is shown
as ␣ and Backspace as ⌫. Clearing the local display resets the center label.

Movement follows Windows mouse-hook events, with path checks between positions
so quick returns can pass through the center between events. Outward overshoots
beyond the overlay are processed before returning to the center. The remaining
16 ms timer only checks focus and Esc; it does not sample typing gestures.

Output uses Windows SendInput, not the clipboard. The panel's local session text
is only an echo of Mousyst's entries; it is not synchronized with the destination
app, and Clear local display does not delete text in that app. No text is saved.

Ordinary Windows text fields are supported. Windows can block injection into
higher-privilege apps, and some games/custom input systems may reject synthetic
input. Mousyst reports blocked input in its panel. Release held modifiers before
typing. No Enter action is sent automatically.

This build supports lowercase English, Space and Backspace. Symbols, prediction,
settings/config customization, and the general launcher remain later milestones.
Mixed-DPI and multiple-monitor behavior needs broader physical-hardware testing.

## Develop

Use native Windows and Python 3.11+:

```powershell
python -m pip install -r requirements-dev.txt
python src/main.py
python -m pytest -q
python -m ruff check src tests
python -m mypy --strict src
python src/main.py --smoke-test
python tests/desktop_smoke.py --app src/main.py
```

The smoke test isolates external output and verifies the actual QML UI. The
opt-in desktop integration test creates its own disposable text window and checks
real input, focus retention, middle-click activation, pointer gestures, controls,
and dismissal. It never uses an existing document as its test target.

For this workspace's local dependency folders, set:
`$env:PYTHONPATH = "$PWD/.runtime;$PWD/.dev-tools"`.

## Build

```powershell
./build-preview.ps1
```

Output: `dist/Mousyst/Mousyst.exe` and
`dist/Mousyst-preview-windows-x64.zip`. This is a portable folder bundle, not an
installer. The build isolates DLL search paths to avoid picking up incompatible
libraries from unrelated developer tools. The Python interpreter and Qt runtime
are bundled; this is not a tiny native-code-only executable.

The prior Qt practice build was approximately 55 MiB zipped / 142 MiB extracted.
Its short local idle sample used 210 MiB working set and 0.62% of one CPU core;
these are historical measurements, not benchmarks of the desktop-input build.
No clean Windows VM test has been performed.

The QML presentation is original. Rovyl was a visual reference; none of its code
or artwork was copied. The older planning/handoff documents remain historical.
