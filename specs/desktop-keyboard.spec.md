# Mousyst desktop keyboard: agreed direction and implementation plan

Historical planning document. Auto-pop was subsequently removed, and ABC/123 now
replaces the main keys rather than expanding a panel. See README.md and DESKTOP.md
for the implemented behavior.

## Overview

Mousyst will provide a mouse-operated Windows keyboard for short text entries,
symbols, shortcuts, and caret movement. The default is Compact QWERTY, with
clicking and whole-word swiping. This specification extends the practice prototype
before integrating the new interaction with desktop input. No typing-speed benefit
has yet been established by a user comparison.

Keep Python, PySide6/Qt Quick, the offline recognizer, and portable packaging.
Keep the previous radial implementation in Git history. Continue development on
codex/swipe-prototype. Do not publish or replace the GitHub release as part of
implementing this specification.

## Functional requirements

### Layouts and symbols

- When started without saved preferences, Mousyst shall use Compact: letter rows,
  Shift/Ctrl/Alt/Win, Space, Backspace, Enter, Tab, Escape, and four arrow controls.
- When Standard is selected, Mousyst shall add a number row and the editing keys
  Home, End, Delete, Page Up, and Page Down.
- When Full is selected, Mousyst shall additionally show F1–F12 and a dedicated
  calculator-style numpad, including Num Lock, decimal, arithmetic, and Enter.
- When the optional Numbers/Symbols panel is opened, Mousyst shall offer row and
  numpad arrangements and remember the chosen arrangement. This panel supplements
  right-click symbols; switching layers is not required to enter common symbols.
- When a letter key is right-clicked and released on the same key, Mousyst shall
  enter its displayed secondary symbol and suppress that key's context menu.
  Use the existing numeric-layer letter-to-symbol mapping as the initial mapping;
  expose it in Settings and configuration. Right-click shall not start a swipe.
- While shortcuts are assembled, Mousyst shall show selected modifiers and dispatch
  them once with the next key. Afterwards it shall clear them. Shortcut labels
  shall identify the base key even when secondary symbols are displayed.

### Suggestions and exact replacement

- When a swipe completes, Mousyst shall insert the best word and automatic trailing
  space, with that word and up to two alternatives in a stable suggestion bar.
- While the pointer is over an enabled suggestion bar, when the wheel moves one
  detent, Mousyst shall immediately replace the latest word with the adjacent
  candidate. Down advances; up returns. Clamp at either end; do not wrap. Accumulate
  high-resolution wheel deltas into deliberate steps. Clicking remains supported.
- While outside the bar, Mousyst shall leave wheel input available to its normal
  recipient. Middle-click shall remain the open/hide action, not candidate confirmation.
- When a candidate changes, Mousyst shall preserve the word's capitalization and
  automatic space, keep Undo available, and avoid adding another space.
- When the caret, selection, text, focused field, or foreground target changes
  independently of Mousyst, it shall invalidate candidate replacement.
- Where the desktop adapter cannot verify the original word and caret range,
  Mousyst shall disable replacement rather than delete text by guessing. The bar
  shall explain why alternatives are unavailable. Raw text entry remains available.
- The first version shall use current-word alternatives, not next-word prediction
  or vocabulary learning.

### Gesture priorities, repeat, and caret control

- When left-click is released on a letter without a swipe or repeat, Mousyst shall
  insert one character, retaining the existing one-third-key-width swipe threshold.
- When a letter is held stationary for 450 ms, Mousyst shall insert the first
  character and repeat every 50 ms until release. A repeat shall lock its glyph,
  including case, for the duration of that press. Release shall add no extra character.
- When movement starts a swipe before the repeat threshold, Mousyst shall cancel
  repeat without inserting the initial letter. After repeat begins, that press
  shall remain a repeating-key action until release; it shall not become a swipe.
- When Backspace is pressed, Mousyst shall delete once immediately, then repeat
  using the same delay and interval. Modifiers, suggestions, Enter, Tab, Escape,
  and shortcut chords shall not auto-repeat. Arrow controls may repeat.
- When Space is clicked and released before 250 ms without dragging, Mousyst shall
  insert one space. When held for 250 ms or dragged at least 6 logical pixels,
  it shall enter horizontal caret-scrubbing mode and display feedback.
- While scrubbing, horizontal displacement shall move by one character per 8
  logical pixels, with accumulated residual movement and reversible direction.
  Vertical movement shall be ignored. Release shall insert no space. Up/Down
  arrow controls shall handle line navigation.
- When a press ends, the target changes, the keyboard hides, Escape is invoked,
  or the app loses its valid target, Mousyst shall cancel active gestures/timers
  and clear pending modifiers. A held key shall never continue after cancellation.
- Timing and scrub sensitivity shall be adjustable in Settings. Layout or scale
  changes shall cancel active gestures before applying new geometry.

### Settings and optional hitbox assistance

- When Settings is opened, Mousyst shall offer layout presets, optional panel
  arrangement, continuous scale, theme colors, secondary symbols, repeat timing,
  scrub sensitivity, auto-pop, and hitbox assistance. Include Reset to defaults.
- When settings are saved, Mousyst shall atomically write versioned JSON to
  %APPDATA%/Mousyst/settings.json. The UI and file shall describe the same settings.
  Provide Open config folder and Reload config actions. Reload shall be explicit.
- When configuration is invalid or has an unsupported version, Mousyst shall retain
  the last working settings and report the offending field. It shall not overwrite
  the user's file. Configuration shall contain declarative values, not scripts.
- Where predictive hitbox assistance is enabled, Mousyst shall keep visible geometry
  fixed and only bias ambiguous normal letter clicks near shared key boundaries.
  Limit the ambiguous band to 10% of key pitch on each side of a shared boundary;
  central key areas shall remain exact. Freeze the chosen target on press and
  highlight it. Right-click symbols, modifiers, shortcuts, and swipe paths shall
  continue using canonical geometry. Assistance shall be off by default.

### Desktop lifecycle and automatic opening

- When launched normally, Mousyst shall start in the tray. When middle-clicked,
  it shall open/hide near the pointer, clamped to the active monitor without
  covering the target field where its bounds can be determined.
- When closed or minimized, Mousyst shall hide to the tray. The tray shall offer
  Show/Hide, Settings, and Quit. Quit shall release hooks and stop all workers.
  A second launch shall activate the existing instance rather than install another hook.
- Where auto-pop is enabled, when a supported editable field receives focus,
  Mousyst shall open without taking text focus. Auto-pop shall be initially enabled;
  its first appearance shall include a nonmodal Turn off automatic opening action.
- When manually dismissed, Mousyst shall suppress auto-pop for that field until
  focus leaves it and enters another editable field. Middle-click may reopen it.
  Opening Mousyst Settings shall not be treated as a new target field.
- Where field detection is unavailable, Mousyst shall retain manual activation.
  Use Windows UI Automation focus events rather than continuous full-tree scanning.
  Password fields shall require manual activation with suggestions/hitbox prediction
  disabled and without reading or retaining their contents.
- When desktop output is requested, Mousyst shall validate the captured target
  immediately before dispatch. Text shall use Unicode input; keys and chords shall
  use explicit key-down/up sequences with modifier release in cleanup paths.
- Where Windows changes focus as a normal shortcut result, Mousyst shall stop the
  current interaction and release modifiers without trying to restore focus.
  The real Win+Shift+S shall invoke Windows snipping only in desktop mode.

## Architecture and interfaces

Use one interaction controller and shared keyboard geometry across two adapters:
practice editing and Windows desktop input. Introduce explicit actions for text,
named keys, chords, relative caret movement, and verified word replacement.
Represent candidate ownership using a target/field identity, text revision, and
word range. Cancel asynchronous recognition on any ownership change.

Keep the Windows focus observer, input dispatcher, settings service, recognizer,
and QML presentation separate. UI Automation may supply focus/range information;
it is not a universal text-editing API. Do not replace an application's entire
text value to implement insertion or candidate replacement.

Keep the practice clipboard and snipping exercise local. Desktop mode uses real
shortcuts and the destination application's normal clipboard behavior. Practice
mode must never install desktop hooks or inject input outside its own window.

## Non-functional requirements

- Keep inference offline. Do not save typed text, password content, or clipboard
  content in production logs. Retain opt-in practice recording and explicit export.
- Target p95 below 100 ms for recognition and below 50 ms for ordinary click and
  wheel feedback on the development machine. Measure end-to-end GUI latency.
- Support Windows x64 portable execution without a Python installation or admin
  installation. Preserve bundled vocabulary attribution. Measure actual ZIP size,
  startup, idle CPU, and working set rather than claiming an unmeasured improvement.
- Use event-driven focus/input handling; no high-frequency idle polling or tree scans.
- Test scale and positioning on mixed-DPI monitors. Never capture the system-wide
  wheel or right button merely to handle events inside the keyboard.

## Acceptance criteria and failures

| Given / when | Then |
|---|---|
| A valid latest word; scroll down and up over its suggestions | Exactly one owned word changes per detent and returns without duplicate spaces |
| The caret or target changed before scrolling | No text is deleted or replaced |
| A letter is right-clicked | Its printed symbol is entered once; no letter or context menu appears |
| A short click, a pre-threshold swipe, and a long hold are tried | One letter, one word, and repeated letters respectively; no mixed actions |
| A repeating key is held while the keyboard hides or focus changes | Repetition stops and no destination receives further input |
| Space is tapped, held, or dragged in either horizontal direction | Space or reversible character movement occurs according to the gesture rules |
| Row/numpad and Compact/Standard/Full are switched | Visible labels, hitboxes, actions, and saved preferences agree |
| A supported text field gains focus, is dismissed, and is revisited | Auto-pop follows the suppression rule; the first-use opt-out persists |
| Config is malformed or contains an invalid mapping | Last working settings remain usable, with a specific error |
| Windows blocks input or a control lacks range support | Show a concise status; cancel dispatch or disable replacement, without guessing |
| A real chord such as Ctrl+C/V or Win+Shift+S is executed | Correct down/up order; no modifiers remain held; target focus stays correct until the shortcut changes it |

Test unit-level action arbitration/settings/range ownership, QML mouse and wheel
interaction, then native tests against disposable target windows. Exercise Notepad,
browser input/textarea/contenteditable, and available document/code editors; record
capabilities per control instead of claiming universal compatibility. Include
unsupported and elevated targets, cancellation, mixed DPI, and clean-machine ZIP use.
Do not send test shortcuts into arbitrary user documents.

## Implementation checklist and release gates

1. [ ] Build the shared action model and editable practice adapter with caret/selection tracking.
2. [ ] Add candidate-wheel replacement, right-click symbols, numpad/row arrangements,
   key repeat, horizontal Space scrubbing, and complete shortcut controls in practice.
3. [ ] Add Settings/configuration and three layout presets; evaluate optional hitbox
   assistance separately with it off/on using held-out human input.
4. [ ] Re-run the short-task user comparison, adding symbol, shortcut, and caret
   exercises. Keep text WPM separate from command-task completion and comfort.
5. [ ] Connect the Windows adapter, verified replacement, middle-click, tray, single
   instance behavior, and real shortcuts. Validate manual activation first.
6. [ ] Add event-driven auto-pop and per-control capability checks; test first-use
   opt-out and dismissal suppression before enabling the default.
7. [ ] Package and verify the executable; document measured compatibility and
   performance. Keep practice mode available for regression and user testing.

Human trials and compatibility tests are required evidence; automated ideal
strokes do not establish usability. Retain the existing hybrid-versus-click
comparison target: at least 20% better median completion time, no worse final
accuracy, and majority preference before promoting a performance claim. Desktop
engineering can proceed without claiming that this benefit has already been proven.
