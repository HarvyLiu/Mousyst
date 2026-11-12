"""Shared keyboard coordinates in units of one key pitch."""

ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
CENTERS = {
    c: (i + (0, 0.5, 1.5)[r] + 0.5, r + 0.5)
    for r, row in enumerate(ROWS)
    for i, c in enumerate(row)
}


def keys() -> list[dict[str, object]]:
    return [
        {"letter": c, "kx": x - 0.5, "ky": y - 0.5} for c, (x, y) in CENTERS.items()
    ]
