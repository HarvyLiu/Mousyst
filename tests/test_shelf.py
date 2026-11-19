"""Local libraries and target-bound shelf actions use disposable data and fake input."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QObject, Signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shelf_tools import ShelfTools
from user_content import LIMITS, UserLibrary, read_library, validate, write_library


class Adapter:
    target = 42
    current = True

    def __init__(self):
        self.events = []

    def is_current(self):
        return self.current

    def chord(self, key, modifiers):
        self.events.append((key, tuple(modifiers)))


class Desktop(QObject):
    changed = Signal()
    pendingCount = 0

    def __init__(self, directory):
        super().__init__()
        self.settings = SimpleNamespace(path=directory / "settings.json")
        self.output = Adapter()
        self.current_field = (1,)
        self.field = {"identity": (1,), "hwnd": 42, "password": False, "editable": True}
        self.error = None
        self.cancel_count = 0

    def snapshot(self):
        return self.field

    def send_text(self, value):
        self.output.events.append(value)

    def cancel(self):
        self.cancel_count += 1

    def dispatch(self, callback):
        try:
            callback()
        except RuntimeError as exc:
            self.error = str(exc)


@pytest.fixture
def desktop_tools(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    desktop = Desktop(tmp_path)
    yield desktop, ShelfTools(desktop)
    assert app


def test_favorite_and_phrase_round_trip(tmp_path, desktop_tools):
    desktop, tools = desktop_tools
    shortcut = tools.saveFavorite("", "Find", "F", ["Ctrl"])
    phrase = tools.savePhrase("", "Signature", "王同學🌷\r\nMousyst", "School", True)
    assert tools.saveFavorite(shortcut, "Find again", "G", ["Ctrl"]) == shortcut
    assert tools.change("favorites", shortcut, "up")
    restored = UserLibrary(tmp_path)
    assert restored.items["favorites"][-2]["label"] == "Find again"
    assert restored.items["phrases"][0]["text"] == "王同學🌷\nMousyst"
    exported = tmp_path / "backup.json"
    write_library("phrases", exported, restored.items["phrases"])
    assert read_library("phrases", exported) == restored.items["phrases"]
    tools.run("favorites", shortcut)
    tools.run("edit", "Delete word left")
    tools.run("phrases", phrase)
    assert desktop.output.events == [
        ("G", ("Ctrl",)),
        ("Back", ("Ctrl",)),
        "王同學🌷",
        ("Enter", ()),
        "Mousyst",
    ]
    assert desktop.cancel_count == 3


def test_each_phrase_chunk_rechecks_field(desktop_tools):
    desktop, tools = desktop_tools
    phrase = tools.savePhrase("", "Long", "w" * 65, "", False)

    def redirect(text):
        desktop.output.events.append(text)
        desktop.field["identity"] = (2,)

    desktop.send_text = redirect
    tools.run("phrases", phrase)
    assert desktop.output.events == ["w" * 32]
    assert desktop.error


def test_pending_swipe_is_preserved_when_tools_are_pressed(desktop_tools):
    desktop, tools = desktop_tools
    desktop.pendingCount = 1
    assert not tools.ready()
    tools.run("edit", "Cut")
    assert desktop.output.events == []
    assert desktop.cancel_count == 0


def test_classic_edit_word_delete_uses_verified_selection(desktop_tools):
    desktop, tools = desktop_tools
    desktop.field.update(classic_edit=True, has_selection=False)
    selection = dict(desktop.field, has_selection=True)
    snapshots = iter([desktop.field, selection])
    desktop.snapshot = lambda: next(snapshots)
    tools.run("edit", "Delete word left")
    assert desktop.output.events == [("Left", ("Ctrl", "Shift")), ("Back", ())]


def test_classic_edit_word_delete_aborts_on_focus_change(desktop_tools):
    desktop, tools = desktop_tools
    desktop.field.update(classic_edit=True, has_selection=False)
    snapshots = iter(
        [desktop.field, dict(desktop.field, identity=(2,), has_selection=True)]
    )
    desktop.snapshot = lambda: next(snapshots)
    tools.run("edit", "Delete word left")
    assert desktop.output.events == [("Left", ("Ctrl", "Shift"))]
    assert desktop.error


@pytest.mark.parametrize(
    "change",
    [
        {"hwnd": 100},
        {"identity": (2,)},
        {"identity": None},
        {"password": True},
    ],
)
def test_changed_private_or_unknown_target_blocks_output(desktop_tools, change):
    desktop, tools = desktop_tools
    desktop.field.update(change)
    assert not tools.allowPhraseShelf()
    tools.run("edit", "Cut")
    tools.run("favorites", "screenshot")
    assert desktop.output.events == []
    assert desktop.error


def test_invalid_import_preserves_library(desktop_tools, tmp_path):
    _, tools = desktop_tools
    library = tools.library
    phrase = tools.savePhrase("", "Thanks", "Thank you", "", False)
    before = library.path("phrases").read_bytes()
    with pytest.raises(ValueError):
        library.replace("phrases", [dict(library.items["phrases"][0], text="x" * 2001)])
    assert library.path("phrases").read_bytes() == before
    assert library.items["phrases"][0]["id"] == phrase
    assert not tools.saveFavorite("", "Broken", "Calculator.exe", ["Win"])
    assert not tools.saveFavorite("", "Broken", "H", [])
    with pytest.raises(ValueError):
        validate("phrases", {"version": 1, "phrases": [{}] * (LIMITS["phrases"] + 1)})
    oversized = tmp_path / "large.json"
    oversized.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(ValueError):
        read_library("phrases", oversized)
    assert tools.change("phrases", phrase, "pin")
    assert tools.phrases[0]["pinned"]
    assert tools.change("phrases", phrase, "delete")
    assert tools.phrases == []
