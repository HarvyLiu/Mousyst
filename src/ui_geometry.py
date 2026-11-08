"""Vector geometry sharing the gesture engine's angles and radii."""

from __future__ import annotations

import math

from gesture import COMMIT_RADIUS, FAN_RADIUS, FAN_WIDTH, GROUPS


def point(radius: float, angle: float) -> tuple[float, float]:
    """Map clockwise polar coordinates into the keyboard canvas."""
    angle = math.radians(angle)
    return 280 + radius * math.sin(angle), 300 - radius * math.cos(angle)


def sector(inner: float, outer: float, start: float, end: float) -> str:
    """Create a rounded annular SVG path with the exact commit radius."""
    corner = 5.0
    trim_outer = math.degrees(corner / outer)
    trim_inner = math.degrees(corner / inner)

    def p(radius: float, angle: float) -> str:
        x, y = point(radius, angle)
        return f"{x:.3f},{y:.3f}"

    return (
        f"M {p(outer, start + trim_outer)} "
        f"A {outer},{outer} 0 0 1 {p(outer, end - trim_outer)} "
        f"Q {p(outer, end)} {p(outer - corner, end)} "
        f"L {p(inner + corner, end)} "
        f"Q {p(inner, end)} {p(inner, end - trim_inner)} "
        f"A {inner},{inner} 0 0 0 {p(inner, start + trim_inner)} "
        f"Q {p(inner, start)} {p(inner + corner, start)} "
        f"L {p(outer - corner, start)} "
        f"Q {p(outer, start)} {p(outer, start + trim_outer)} Z"
    )


def group_items() -> list[dict[str, object]]:
    """Build eight stable, rounded groups."""
    result: list[dict[str, object]] = []
    for index, group in enumerate(GROUPS):
        x, y = point(94, index * 45)
        result.append(
            {
                "index": index,
                "label": {"SPACE": "␣", "BACK": "⌫"}.get(group, group.upper()),
                "x": x,
                "y": y,
                "path": sector(55, 128, index * 45 - 21, index * 45 + 21),
            }
        )
    return result


def fan_items(group_index: int | None) -> list[dict[str, object]]:
    """Build letter targets matching the gesture engine's angular split."""
    if group_index is None:
        return []
    group = GROUPS[group_index]
    if group in ("SPACE", "BACK"):
        return []
    items = [group] if group in ("SPACE", "BACK") else list(group)
    width = 45.0 if len(items) == 1 else FAN_WIDTH
    result: list[dict[str, object]] = []
    for index, letter in enumerate(items):
        start = group_index * 45 - width / 2 + index * width / len(items)
        end = start + width / len(items)
        x, y = point(176, (start + end) / 2)
        result.append(
            {
                "value": letter,
                "label": {"SPACE": "␣", "BACK": "⌫"}.get(letter, letter.upper()),
                "x": x,
                "y": y,
                "path": sector(FAN_RADIUS, COMMIT_RADIUS, start + 0.4, end - 0.4),
            }
        )
    return result
