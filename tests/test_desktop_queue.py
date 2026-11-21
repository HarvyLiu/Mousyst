"""Exercise the public desktop slots against a controllable worker and text field."""

import random
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop_app import DesktopController
from practice import Controller
from text_model import Editor


class FakeField:
    def __init__(self):
        self.text = ""
        self.identity = (1,)
        self.password = False
        self.events = []

    def snapshot(self):
        return {
            "identity": self.identity,
            "hwnd": 42,
            "password": self.password,
            "prefix": self.text[-512:],
            "caret": len(self.text),
            "editable": True,
        }

    def send(self, text):
        self.text += " " if text == "SPACE" else text

    def chord(self, key, modifiers):
        self.events.append((key, modifiers))
        if key == "Back":
            self.text = self.text[:-1]


class DelayedWorker:
    def __init__(self):
        self.calls = deque()

    def submit(self, callback):
        self.calls.append(callback)

    def finish(self):
        self.calls.popleft()()


class TestVocabulary:
    @staticmethod
    def recognize(path):
        return [["hello", "help"], ["world"], []][int(path[0][0])]


@pytest.fixture
def keyboard(monkeypatch, tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setenv("MOUSYST_SETTINGS_DIR", str(tmp_path))
    monkeypatch.setattr(Controller, "load", lambda self: None)
    c = DesktopController(smoke=True)
    c.executor.shutdown(wait=True)
    c.executor = DelayedWorker()
    c.recognizer = TestVocabulary()
    c.output = FakeField()
    c.snapshot = c.output.snapshot
    yield c
    c.cancel()
    assert app is not None


def swipe(keyboard, word=0):
    keyboard.stroke([{"x": word, "y": 0}, {"x": word + 1, "y": 1}])


def test_two_swipes_then_punctuation(keyboard):
    c = keyboard
    swipe(c)
    swipe(c, 1)
    c.key(".")
    assert c.pendingCount == 3 and len(c.executor.calls) == 1
    c.executor.finish()
    assert c.output.text == "hello " and len(c.executor.calls) == 1
    c.executor.finish()
    assert c.output.text == "hello world." and c.pendingCount == 0


def test_only_final_verified_swipe_choice_is_learned(keyboard):
    c = keyboard
    swipe(c)
    c.executor.finish()
    c.alternative(1)
    assert not c.learning.path.exists()
    c.key(".")
    assert c.learning.state[0] == {"help": 3}
    assert type(c.learning)(c.learning.path.parent).state == c.learning.state
    c.clearLearning()
    assert not c.learning.path.exists()
    swipe(c)
    c.executor.finish()
    c.key("Back")
    assert not c.learning.path.exists()


@pytest.mark.parametrize("reason", ["disabled", "password", "changed field"])
def test_unconfirmed_swipes_stay_out_of_profile(keyboard, reason):
    c = keyboard
    if reason == "disabled":
        c.settings.value["swipeLearning"] = False
    swipe(c)
    c.executor.finish()
    if reason == "password":
        c.output.password = True
    if reason == "changed field":
        c.output.identity = (999,)
    c.key(".")
    assert not c.learning.path.exists()


def test_delayed_worker_signal_preserves_order_on_gui_thread(keyboard, monkeypatch):
    c = keyboard
    recognize = c.recognizer.recognize

    def slow_recognize(path):
        time.sleep(0.2)
        return recognize(path)

    monkeypatch.setattr(c.recognizer, "recognize", slow_recognize)
    with ThreadPoolExecutor(max_workers=1) as worker:
        c.executor = worker
        swipe(c)
        swipe(c, 1)
        c.key("Back")
        deadline = time.monotonic() + 3
        while c.pendingCount and time.monotonic() < deadline:
            QCoreApplication.processEvents()
            time.sleep(0.005)
        assert c.pendingCount == 0 and c.output.text == "hello world"


def test_shift_and_chords_belong_to_the_submitted_action(keyboard):
    c = keyboard
    swipe(c)
    c.key("Shift")
    swipe(c, 1)
    c.key("Shift")
    c.key("1")
    c.key("Ctrl")
    c.key("c")
    c.executor.finish()
    c.executor.finish()
    assert c.output.text == "hello World!"
    assert c.output.events == [("Back", []), ("c", ["Ctrl"])]


def test_no_match_can_be_spelled_without_losing_punctuation(keyboard):
    c = keyboard
    swipe(c, 2)
    c.key(",")
    c.executor.finish()
    assert not c.output.text and c.needsSpelling
    c.spellWord()
    for ch in "mousyst":
        c.key(ch)
    c.key(" ")
    assert c.output.text == "mousyst," and c.pendingCount == 0


def test_full_queue_rejects_only_the_new_input(keyboard):
    c = keyboard
    swipe(c)
    for ch in "abcdefghi":
        c.key(ch)
    assert "full" in c.status and c.pendingCount == 9
    c.executor.finish()
    assert c.output.text == "hello abcdefgh"


@pytest.mark.parametrize(
    "change", ["focus", "caret", "password", "hide", "timeout", "reset"]
)
def test_cancellation_rejects_late_result_and_its_followups(keyboard, change):
    c = keyboard
    swipe(c)
    c.key("Back")
    if change == "focus":
        c.output.identity = (2,)
    elif change == "caret":
        c.output.text = "external edit"
    elif change == "password":
        c.output.password = True
    elif change == "timeout":
        c.recognition_timer.timeout.emit()
    elif change == "reset":
        c.reset()
    else:
        c.cancel()
    before = c.output.text
    c.executor.finish()
    assert c.output.text == before and not c.output.events and c.pendingCount == 0


def test_waits_for_actual_host_update_before_deleting_space(keyboard):
    c = keyboard
    unchanged = c.snapshot()
    swipe(c)
    c.key(".")
    c.snapshot = lambda: unchanged
    c.executor.finish()
    assert (
        c.output.text == "hello " and not c.output.events and c.verify_timer.isActive()
    )
    c.snapshot = c.output.snapshot
    c.drain_inputs()
    assert c.output.text == "hello." and c.pendingCount == 0


def test_mixed_delayed_sequences_match_sequential_edits(keyboard):
    c = keyboard
    rng = random.Random(42)
    for _ in range(50):
        c.cancel()
        c.output.text = ""
        reference = Editor()
        swipe(c)
        reference.word("hello")
        for action in rng.choices(["world", ".", " ", "x", "Back"], k=7):
            if action == "world":
                swipe(c, 1)
                reference.word("world")
            elif action == "Back":
                c.key("Back")
                reference.backspace()
            else:
                c.key(action)
                reference.insert(action)
        while c.executor.calls:
            c.executor.finish()
        assert c.output.text == reference.text


def test_zhuyin_highlight_then_commit_once(keyboard):
    for symbol in "ㄕˋ":
        keyboard.phonetic(symbol)
    assert len(keyboard.readingChoices) > 9
    keyboard.cycleSuggestion(7)
    assert keyboard.highlightedReading == 7 and keyboard.output.text == ""
    for symbol in "ㄐㄧㄝˋ":
        keyboard.phonetic(symbol)
    assert keyboard.readingChoices[0] == "世界"
    keyboard.key(" ")
    keyboard.commitReading(0)
    assert keyboard.output.text == "世界" and keyboard.pronunciation == ""


def test_zhuyin_backspace_and_changed_field(keyboard):
    for symbol in "ㄕˊ":
        keyboard.phonetic(symbol)
    keyboard.key("Back")
    assert keyboard.pronunciation == "ㄕ" and not keyboard.output.events
    keyboard.phonetic("ˋ")
    keyboard.output.identity = (2,)
    keyboard.commitReading(0)
    assert keyboard.output.text == "" and keyboard.pronunciation == ""
    keyboard.output.password = True
    keyboard.phonetic("ㄕ")
    assert keyboard.pronunciation == ""


def test_contraction_space_verifies_the_field(keyboard):
    for key in "dont ":
        keyboard.key(key)
    assert keyboard.output.text == "don't "
    for key in "youre":
        keyboard.key(key)
    keyboard.output.identity = (2,)
    keyboard.key(" ")
    assert keyboard.output.text.endswith("youre ")


def test_zhuyin_trace_declines_a_moved_caret(keyboard):
    keyboard.beginPhoneticGesture()
    keyboard.output.text = "moved"
    keyboard.phoneticTrace(["ㄕˋㄐㄧㄝˋ"])
    assert not keyboard.readingChoices and keyboard.output.text == "moved"
