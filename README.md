# Mousyst

A dark Windows keyboard operated with your mouse: click letters, swipe words,
enter shortcuts, and scrub the caret without moving your hand to a keyboard.

## Download and run

Download the Windows x64 ZIP from [Releases](https://github.com/HarvyLiu/Mousyst/releases).
Extract the whole folder and open **MousystDesktop.exe**. Keep `_internal` beside it.
No Python installation is needed. Mousyst starts in the tray with a white script
M on black; right-click that icon to open Settings or Quit.

1. Click the destination text field, then **middle-click** to show the keyboard.
2. Click individual keys or hold left-click and trace a word, then release.
3. Middle-click again or use the close icon to hide it.

## Controls

- **Suggestions:** click an alternative or scroll over the reserved suggestion bar
  to replace the last word. Empty suggestions never move the keys.
- **Symbols:** right-click a letter to enter its small printed symbol.
- **ABC/123:** replace the main keys with symbol rows or a numpad in the same space.
- **Shortcuts:** select Ctrl, Alt, Win, or Shift, then a key. Modifiers apply once.
- **Repeat:** hold a letter or Backspace.
- **Caret:** tap Space for a space; hold and drag it horizontally for caret movement.
- **Settings:** choose Compact/Standard/Full, size, colors, repeat timing, symbols,
  and optional predictive aiming. Config import/export is available separately.

Automatic opening is removed. Activation is manual through the middle button.
See [the desktop guide](DESKTOP.md) for details and compatibility limits.

The app uses offline English word recognition. No production text or clipboard
history is saved. Some custom/elevated apps can reject input or lack accessible
caret information; alternatives are disabled when replacement cannot be verified.
This is a desktop preview, with broader application and mixed-DPI testing still needed.

## Develop

Use native Windows x64 and Python 3.12:

```powershell
python -m pip install -r requirements-dev.txt
python src/desktop_app.py
python -m pytest -q --basetemp build/pytest-local
python -m ruff check src tests tools
```

Build the portable folder and ZIP:

```powershell
./build-preview.ps1 -Desktop -BundleName MousystDesktop
```

The build generates Windows UI Automation bindings before packaging. The bundled
vocabulary is already included; `wordfreq` is only needed to regenerate it.
Its attribution and license notices are in [src/data](src/data/ATTRIBUTION.md).

The local practice harness remains available with `python src/practice.py`.
See [EXPERIMENT.md](EXPERIMENT.md). The older radial prototype remains in Git history.
There is no claim that mouse typing outperforms a physical keyboard.

## Automatic releases

GitHub Actions tests and builds Windows ZIPs on main-branch changes. To publish a
new version, push a version tag:

```powershell
git tag v0.2.1
git push origin v0.2.1
```

The workflow publishes the ZIP and SHA-256 checksum only after tests, UI checks,
and packaging pass. Tags such as `v0.2.1-preview.1` are supported too. Use the
Actions page for build logs and diagnostic screenshots. Manual workflow runs
produce downloadable build artifacts without creating a release.
