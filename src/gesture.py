"""Pure gesture state machine for the Mousyst practice prototype."""

from __future__ import annotations

import math
from dataclasses import dataclass

GROUPS = ("abcde", "fghij", "klmn", "opqr", "SPACE", "stuv", "wxyz", "BACK")
CENTER_RADIUS = 38
GROUP_RADIUS = 88
CONTROL_RADIUS = 128
FAN_RADIUS = 134
COMMIT_RADIUS = 218
FAN_WIDTH = 82.0


def angle_delta(angle: float, center: float) -> float:
    """Return signed angular distance in degrees."""
    return (angle - center + 180) % 360 - 180


@dataclass
class Gesture:
    """Latch a group until cancellation; emit only once per center visit."""

    armed: bool = False
    group: int | None = None
    selected: str | None = None
    previous_radius: float = 0.0
    previous_angle: float = 0.0
    previous_position: tuple[float, float] | None = None

    def cancel(self) -> None:
        """Require a center visit after focus loss or leaving the canvas."""
        self.armed = False
        self.group = None
        self.selected = None
        self.previous_radius = 0.0
        self.previous_angle = 0.0
        self.previous_position = None

    def move(self, x: float, y: float) -> str | None:
        """Sweep the movement path so fast events cannot skip small targets."""
        start = self.previous_position
        self.previous_position = (x, y)
        if start is None:
            return self._advance(x, y)
        steps = max(1, math.ceil(math.hypot(x - start[0], y - start[1]) / 4))
        for step in range(1, steps + 1):
            result = self._advance(
                start[0] + (x - start[0]) * step / steps,
                start[1] + (y - start[1]) * step / steps,
            )
            if result is not None:
                self.previous_radius = math.hypot(x, y)
                self.previous_angle = math.degrees(math.atan2(x, -y)) % 360
                return result
        return None

    def _advance(self, x: float, y: float) -> str | None:
        """Process a short path segment, emitting at most one action."""
        radius = math.hypot(x, y)
        angle = math.degrees(math.atan2(x, -y)) % 360
        previous = self.previous_radius
        previous_angle = self.previous_angle
        self.previous_radius = radius
        self.previous_angle = angle
        if radius <= CENTER_RADIUS:
            self.armed = True
            self.group = None
            self.selected = None
            return None
        if not self.armed:
            return None
        if self.group is None and radius >= GROUP_RADIUS:
            self.group = int((angle + 22.5) // 45) % 8
        if self.group is None:
            return None
        group = GROUPS[self.group]
        delta = angle_delta(angle, self.group * 45)
        previous_delta = angle_delta(previous_angle, self.group * 45)
        limit = 22.5 if group in ("SPACE", "BACK") else FAN_WIDTH / 2
        self.selected = None
        if (
            group not in ("SPACE", "BACK")
            and min(previous, radius) >= FAN_RADIUS
            and abs(previous_delta) < limit <= abs(delta)
        ):
            self.selected = group[0] if delta < 0 else group[-1]
            self.armed = False
            return self.selected
        if abs(delta) < limit:
            if group in ("SPACE", "BACK"):
                self.selected = group
            elif radius >= FAN_RADIUS:
                index = int((delta + limit) / (2 * limit) * len(group))
                self.selected = group[min(index, len(group) - 1)]
        boundary = CONTROL_RADIUS if group in ("SPACE", "BACK") else COMMIT_RADIUS
        if previous < boundary <= radius and self.selected is not None:
            result = self.selected
            self.armed = False
            return result
        return None
