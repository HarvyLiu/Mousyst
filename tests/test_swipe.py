"""Editing and recognition regression cases for the practice experiment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtCore import QCoreApplication

from keyboard_layout import CENTERS
from practice import Controller, edit_distance
from text_model import Editor
from word_recognizer import Recognizer


def test_spacing_replacement_and_undo():
    e = Editor()
    e.word("hello")
    e.insert(" ")
    assert e.text == "hello "
    e.replace("help")
    assert e.text == "help "
    e.insert(",")
    assert e.text == "help,"
    e.word("world")
    e.replace("word")
    assert e.text == "help, word "
    e.undo()
    assert e.text == "help,"


def test_edit_invalidates_replacement():
    e = Editor()
    e.word("hello")
    e.backspace()
    e.replace("wrong")
    assert e.text == "hello"
    e.external("name xyz")
    e.insert("!")
    assert e.text == "name xyz!"


def test_repeated_letters_and_noisy_sparse_stroke():
    r = Recognizer(["hello", "help", "held", "world", "word", "test"])
    assert r.recognize([CENTERS[c] for c in "helo"])[0] == "hello"
    points = [(CENTERS[c][0] + 0.08, CENTERS[c][1] - 0.06) for c in "world"]
    assert r.recognize(points)[0] == "world"
    assert edit_distance("hello", "helo") == 1


def test_stale_results_do_not_insert():
    QCoreApplication.instance() or QCoreApplication([])
    c = Controller()
    c.executor.shutdown(wait=True)
    generation, revision = c.generation, c.editor.revision
    c.key("x")
    c.receive(generation, revision, ["hello"], 10)
    assert c.text == "x"
    c.modifier("Ctrl")
    c.activateKey("a", 0, 0, 0)
    assert not c.activeModifiers
    c.modifier("Win")
    c.key("Shift")
    c.activateKey("s", 0, 0, 0)
    assert c.shortcut_events[-1]["chord"] == "Win+Shift+S"
    assert not c.shifted and not c.activeModifiers
    c.modifier("Ctrl")
    c.cancel()
    assert not c.activeModifiers
    c.cancel()
    c.receive(generation, revision, ["world"], 10)
    assert c.text == "x"
