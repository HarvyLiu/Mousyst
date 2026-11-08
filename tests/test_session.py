"""Practice metrics must remain honest after corrections and completion."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gesture import Gesture
from session import PracticeSession
from ui_geometry import fan_items, group_items


def test_corrections_keep_error_count() -> None:
    session = PracticeSession()
    session.enter("x", now=10)
    session.enter("BACK", now=11)
    session.enter("t", now=12)
    assert session.text == "t"
    assert (session.entries, session.errors, session.backspaces) == (2, 1, 1)
    assert session.wpm(now=22) == 1.0


def test_completion_freezes_time_and_input() -> None:
    session = PracticeSession()
    assert session.wpm() is None
    for index, char in enumerate(session.target):
        session.enter("SPACE" if char == " " else char, now=float(index))
    finished_text = session.text
    speed = session.wpm(now=100)
    session.enter("BACK", now=101)
    assert session.text == finished_text
    assert session.wpm(now=1000) == speed


def test_visual_label_centers_match_gesture_targets() -> None:
    groups = group_items()
    assert len(groups) == 8
    assert fan_items(None) == []
    for group in groups:
        index = int(str(group["index"]))
        for item in fan_items(index):
            gesture = Gesture()
            gesture.move(0, 0)
            gesture.move(float(str(group["x"])) - 280, float(str(group["y"])) - 300)
            x, y = float(str(item["x"])) - 280, float(str(item["y"])) - 300
            gesture.move(x, y)
            assert gesture.move(x * 225 / 176, y * 225 / 176) == item["value"]
