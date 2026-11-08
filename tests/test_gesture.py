"""Headless regression tests for accidental entry and gesture geometry."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture import GROUPS, Gesture


def move(gesture: Gesture, radius: float, angle: float) -> str | None:
    """Move at a clockwise angle from twelve o'clock."""
    return gesture.move(
        radius * math.sin(math.radians(angle)),
        -radius * math.cos(math.radians(angle)),
    )


def test_all_letters_and_controls_are_reachable() -> None:
    for group_index, group in enumerate(GROUPS):
        items = [group] if group in ("SPACE", "BACK") else list(group)
        for index, character in enumerate(items):
            gesture = Gesture()
            gesture.move(0, 0)
            move(gesture, 100, group_index * 45)
            if group in ("SPACE", "BACK"):
                assert move(gesture, 129, group_index * 45) == group
                assert move(gesture, 180, group_index * 45) is None
                assert move(gesture, 225, group_index * 45) is None
                continue
            angle = group_index * 45
            if len(items) > 1:
                angle += -41 + (index + 0.5) * 82 / len(items)
            assert move(gesture, 180, angle) is None
            assert move(gesture, 225, angle) == character
            assert move(gesture, 240, angle) is None
            assert move(gesture, 150, angle) is None
            assert move(gesture, 225, angle) is None


def test_requires_center_visit() -> None:
    gesture = Gesture()
    assert move(gesture, 225, 0) is None
    gesture.move(0, 0)
    assert move(gesture, 225, 0) == "c"
    gesture.move(0, 0)
    assert move(gesture, 225, 0) == "c"


def test_cancel_and_group_latching() -> None:
    gesture = Gesture()
    gesture.move(0, 0)
    move(gesture, 100, 0)
    assert move(gesture, 225, 90) is None
    assert gesture.group == 0
    # Follow an outside arc: a single chord would re-enter the fan and
    # legitimately cross its outer edge again under swept hit testing.
    move(gesture, 250, 90)
    for angle in range(89, -1, -1):
        assert move(gesture, 250, angle) is None
    gesture.move(0, 0)
    move(gesture, 100, 90)
    assert gesture.group == 2
    gesture.cancel()
    assert move(gesture, 225, 90) is None


def test_return_before_commit_cancels() -> None:
    gesture = Gesture()
    gesture.move(0, 0)
    move(gesture, 180, 0)
    assert gesture.selected == "c"
    assert gesture.move(0, 0) is None
    assert gesture.group is None


def test_fast_swipe_can_overshoot_window() -> None:
    gesture = Gesture()
    gesture.move(0, 0)
    assert gesture.move(0, -500) == "c"
    assert gesture.move(0, -550) is None


def test_fast_return_can_cross_center_between_events() -> None:
    gesture = Gesture()
    gesture.move(0, 0)
    assert gesture.move(0, -225) == "c"
    # Neither endpoint is in the center, but the movement passes through it.
    assert gesture.move(0, 180) == "SPACE"
    assert gesture.move(0, 240) is None


def test_both_sides_of_every_letter_fan_commit_once() -> None:
    for index, group in enumerate(GROUPS):
        if group in ("SPACE", "BACK"):
            continue
        for sign, expected in ((-1, group[0]), (1, group[-1])):
            gesture = Gesture()
            gesture.move(0, 0)
            move(gesture, 100, index * 45)
            assert move(gesture, 176, index * 45 + sign * 32) is None
            assert move(gesture, 176, index * 45 + sign * 55) == expected
            assert move(gesture, 190, index * 45 + sign * 60) is None


def test_return_inward_from_edge_letter_cancels() -> None:
    gesture = Gesture()
    gesture.move(0, 0)
    move(gesture, 100, 0)
    move(gesture, 176, 34)
    assert gesture.move(0, 0) is None
    assert gesture.armed and gesture.group is None
