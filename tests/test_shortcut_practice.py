"""Shortcut exercises must stay local and clear their one-shot modifiers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shortcut_practice import ShortcutPractice


def test_local_copy_paste_cut_and_undo():
    s = ShortcutPractice()
    text, selected, _ = s.apply("Ctrl+A", "hello", 0, 0, 0)
    assert selected == (0, 5)
    assert s.apply("Ctrl+C", text, *selected, 5)[0] == "hello"
    text, selected, _ = s.apply("Ctrl+V", text, 5, 5, 5)
    assert (text, selected) == ("hellohello", (10, 10))
    text, _, _ = s.apply("Ctrl+X", text, 5, 10, 10)
    assert text == "hello"
    assert s.apply("Ctrl+Z", text, 5, 5, 5)[0] == "hellohello"


def test_empty_selection_and_unsupported_chord_are_safe():
    s = ShortcutPractice()
    assert s.apply("Ctrl+C", "hello", 2, 2, 2)[0] == "hello"
    assert not s.clipboard
    assert s.apply("Ctrl+V", "hello", 0, 5, 5)[0] == "hello"
    assert s.apply("Alt+F", "hello", 0, 5, 5)[0] == "hello"
    assert s.apply("Win+Shift+S", "hello", 0, 5, 5)[0] == "hello"
