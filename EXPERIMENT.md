# Mousyst typing comparison

This prototype is for short replies, searches, and labels. It does not send text
to other applications. The previous radial release remains on main.

## Run

Extract MousystPractice-preview-windows-x64.zip, keep the folder intact, and run
MousystPractice.exe. Source: `python src/practice.py` or `python src/main.py --practice`.
Install requirements.txt for source use. Build: `./build-preview.ps1 -Practice`.
The vocabulary is already bundled; wordfreq is only needed to regenerate it.

Click Open keyboard. Click to spell exact text, or hold the left button and trace
the letters of a word, then release. No loops are needed for double letters.
The candidate strip replaces the most recent swipe; Undo removes that word.
Click punctuation after a swipe to replace its trailing space. Use Shift for
the next letter or initial capital, and 123 for symbols. Escape cancels a stroke.
Unknown words, names, and contractions can be spelled with clicks.

## Comparison procedure

### Shortcut practice

Enable Shortcut practice to load sample text. Click Ctrl, then A to select all;
Ctrl then C copies the selection to an in-memory practice clipboard. Click End,
then Ctrl and V to paste. Ctrl+X cuts; Ctrl+Z undoes shortcut edits. You can also
drag across text to select it. Modifiers are highlighted and apply to one key,
then clear automatically. Escape, focus loss, and reset clear them too.

Click Win, Shift, then S to open a local snipping exercise; drag a rectangle to
complete it. This does not invoke Windows Snipping Tool or capture the desktop.
Other combinations are shown in the status message without triggering OS actions.
Shortcut events and elapsed times are included in requested exports. Finish shortcut
trial saves comfort and preference with a separate shortcut record, without a WPM
score. Switch this exercise off before the typing comparison.

Use approximately five testers, with five minutes of familiarization per condition.
For tester IDs 0/3, use click, hybrid, physical; IDs 1/4 use hybrid, physical,
click; ID 2 uses physical, click, hybrid. Each condition gets six short tasks;
the participant ID and condition rotate between three phrase sets. These small
sets are a pilot and are not statistically equivalent difficulty.

Restart after familiarization. Timing begins when each task appears and ends
when Finish is pressed, including opening the keyboard and corrections. Physical
users click the text box to focus it. Finish is allowed with errors so failures
are retained. Record comfort and preference before advancing. Do not switch the
condition partway through a measured task.

Results stay in memory and are lost on exit unless explicitly exported. Export
includes elapsed time, entry WPM, Levenshtein remaining errors, correction actions,
pointer travel over the practice window, per-swipe latency, comfort, and preference.
Pointer travel excludes movement outside the practice window;
do not treat it as total desktop movement. Correction counts represent actions,
not a reconstructed history of every mistaken character.

Compare each tester's median completion times, then the group median, with final
error counts alongside speed. Advance to planning desktop integration only when
hybrid is at least 20% faster than click-only, final accuracy is no worse, and
a majority prefer hybrid for short entries. Physical typing is a reference.
No performance benefit or 50 WPM target has been established.

## Recorded-stroke evaluation

Enable Record strokes only with the tester's agreement; raw paths are exported
only on request. The task phrase is saved as context. Add an `expected_word`
label to each exported stroke independently of its recognized result, then run
`python tools/evaluate_swipes.py results.json`. Keep these strokes held out from
tuning. It reports top-1/top-3 accuracy and p95 latency. Ideal generated paths
and automated UI strokes are regression checks, not evidence of user accuracy.

## Known experimental limitations

The first recognizer uses geometry and frequency, without sentence context.
The candidate strip provides three guesses even on ambiguous paths. This may
produce wrong words; exact clicking and correction are always available.
Input is appended at the end in mouse conditions; the physical condition supports
normal text-box editing. Resizing the keyboard cancels active recognition.
Human trials, independently recorded strokes, and a clean Windows VM test remain
outstanding. Desktop focus handling and replacement safety require a later plan.
