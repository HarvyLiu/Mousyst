"""Regression tests use fake output only; never install hooks or inject keys."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop_app import DesktopController
from input_session import matches_owner
from keymap import shifted_text


def field(identity=1, prefix="hello ", caret=6, password=False):
    return {
        "identity": (identity,),
        "prefix": prefix,
        "caret": caret,
        "password": password,
        "hwnd": 42,
    }


class Output:
    def __init__(self):
        self.events = []
        self.fail = False

    def send(self, text):
        if self.fail:
            raise RuntimeError("blocked")
        self.events.append(("text", text))

    def chord(self, key, modifiers):
        if self.fail:
            raise RuntimeError("blocked")
        self.events.append(("key", key, modifiers))


@pytest.fixture
def controller(monkeypatch, tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setenv("MOUSYST_SETTINGS_DIR", str(tmp_path))
    c = DesktopController(smoke=True)
    c.executor.shutdown(wait=True)
    c.output = Output()
    c.snapshot = lambda: field()
    yield c
    c.repeat_timer.stop()
    assert app is not None


@pytest.mark.parametrize(
    "current", [None, field(2), field(prefix="hello X", caret=7), field(password=True)]
)
def test_stale_space_never_deletes_external_character(controller, current):
    c = controller
    c.editor.word("hello")
    c.owner = field()
    c.snapshot = lambda: current
    c.key(".")
    assert c.output.events == [("text", ".")]
    assert c.owner is None


def test_owned_punctuation_removes_only_owned_space(controller):
    c = controller
    c.editor.word("hello")
    c.owner = field()
    c.key(".")
    assert c.output.events == [("key", "Back", []), ("text", ".")]


@pytest.mark.parametrize(
    "pending,current",
    [
        (None, field()),
        (field(), None),
        (field(), field(2)),
        (field(prefix=None, caret=None), field(prefix=None, caret=None)),
    ],
)
def test_unverified_result_is_not_inserted(controller, pending, current):
    c = controller
    c.pending_field = pending
    c.snapshot = lambda: current
    c.receive(c.generation, c.editor.revision, ["world"], 20)
    assert c.output.events == []
    assert c.editor.text == ""


def test_failed_undo_invalidates_ownership(controller):
    c = controller
    c.editor.word("hello")
    c.owner = field()
    c.output.fail = True
    c.undoWord()
    assert c.owner is None and c.editor.span is None
    assert "blocked" in c.status


def test_password_clicks_have_no_local_echo(controller):
    c = controller
    c.snapshot = lambda: field(password=True)
    c.key("s")
    assert c.output.events == [("text", "s")]
    assert c.editor.text == ""


def test_cancel_clears_transient_context(controller):
    c = controller
    c.editor.word("hello")
    c.owner = field()
    c.cancel()
    assert c.editor.text == "" and not c.editor.auto_space and c.editor.span is None


@pytest.mark.parametrize(
    "base,expected", [("1", "!"), (";", ":"), ("/", "?"), ("[", "{"), ("a", "A")]
)
def test_shift_display_and_output_agree(controller, base, expected):
    controller.shift = True
    controller.key(base)
    assert controller.output.events == [("text", expected)]
    assert controller.shiftLabel(base) == shifted_text(base) == expected


def test_empty_caret_is_not_ownership():
    assert not matches_owner(field(caret=None), field(caret=None))
