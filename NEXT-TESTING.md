# Mousyst NEXT — isolated testing branch

Branch: `codex/mousyst-next`. Original baseline: `bcbe928` on `main`.

This is the first input-safety checkpoint, not the completed improvement roadmap. Do not merge, tag, publish a release, or promote a website deployment until the owner has finished testing.

## Run

Use this checkout's `dist/MousystNext/MousystNext.exe`, retaining its `_internal` folder. Its executable name enables isolated development mode automatically. It has a separate instance lock, local IPC name, settings folder, and NEXT tray tooltip.

For source execution, pass `python src/desktop_app.py --development`.

Quit the original Mousyst tray instance temporarily before testing NEXT, so two global middle-button hooks do not compete. You can restart the original EXE afterward. The original binary and published release are not replaced.

Development settings are written under this version's `build/development-settings`, not the homework's `%APPDATA%/Mousyst` settings. Exact clicks remain available when a field cannot be verified; swipe results are rejected rather than committed to an unverifiable destination.

### Compatibility and color-picker update · November 15

The first checkpoint required caret information even for inserting a swipe word. Some editable controls expose their identity but no caret API, so swipes were rejected although clicks worked. The updated build accepts insertion when the same non-password editable control is still focused. It does not enable alternatives, word Undo, or automatic-space deletion without verified caret/text ownership. Completely unknown or changed destinations still reject delayed results. Password state is rechecked per stroke instead of blocking input based on the field used when the keyboard opened.

The system color dialog is replaced with a matching dark panel: presets, a preview, hex input, hue/saturation/brightness sliders, and explicit Apply/Cancel. There is no draggable color square. Draft changes are discarded on Cancel or Escape.

Test the affected apps again, especially fields where clicks previously worked but swipes did not. Also test switching fields during recognition, clicking punctuation after an insertion, changing colors repeatedly, cancelling, and reopening the picker. If a field remains unsupported, report the app and type of text box; this is not a claim of universal compatibility.

## Implemented in this checkpoint

- Check field/caret/expected prefix before deleting a word's automatic space.
- Reject delayed recognition with missing, password or changed origin information.
- Clear transient typing context on cancellation and avoid retaining known-password/unknown-field click text in the local echo.
- Invalidate local ownership after failed Undo or partial dispatch rather than reporting a successful edit.
- Correct US-English Shift symbols and displayed punctuation.
- Map shortcut characters using the target Windows keyboard layout; reject unsupported mappings.
- Add Backspace, Enter and on-screen Esc to both number formats without expanding the panel.
- Keep NEXT configuration and instance names separate from the homework app.

## Test using disposable text only

1. Swipe a word, move the caret, then click a period. Check that no unrelated character is deleted.
2. Swipe in one browser field, switch to another field before a delayed result. The result must not follow to the new field.
3. Test Shift+1, Shift+semicolon, Shift+slash; expect `!`, `:`, `?`.
4. Test Ctrl+slash/brackets/comma in an application where their intended actions are known. They must not become Help/Windows/PrintScreen keys.
5. In symbols and numpad modes, enter a number, correct a digit using Backspace, then submit with Enter without returning to ABC.
6. Change NEXT settings, then restart the original homework EXE: its own settings should be unchanged.

## Verification recorded

- 58 unit tests passed, including fake-output regressions for editable controls without caret APIs, changed destinations, and stale password state (no live application injection).
- Python lint passed.
- Source offscreen UI smoke passed.
- Packaged offscreen UI smoke passed (no live hooks or external typing).
- Color-picker UI checks cover preview without saving, Cancel, Apply, and hue-slider changes. Its rendered layout was visually checked.

## Still pending

Ordered input transactions for rapid swipes/punctuation; fully asynchronous bounded UI Automation; physical Escape handling; full monitor/DPI qualification; recognition confidence/evaluation; editing shelf, shortcut favorites and saved phrases; website accessibility/localization/motion improvements; release hardening.

In particular, this checkpoint does not yet fix the known pending-recognition input-order issue. Use it to test the listed fixes, not as a new stable release. See `specs/review-and-roadmap-2026-11-15.md` for the full sequence and acceptance criteria.
