"""Conservative ownership checks for external text edits."""


def accepts_insertion(origin, current):
    """Allow append-only input in an unchanged editable control without caret APIs.

    Missing caret data grants no permission to replace or delete existing text.
    If either snapshot exposes a caret, both must agree completely.
    """
    if not origin or not current:
        return False
    if any(f.get("password", False) for f in (origin, current)):
        return False
    if not origin.get("identity") or not origin.get("hwnd"):
        return False
    if any(origin.get(k) != current.get(k) for k in ("identity", "hwnd")):
        return False
    if any(
        f.get("caret") is not None or f.get("prefix") is not None
        for f in (origin, current)
    ):
        return matches_owner(origin, current)
    return bool(origin.get("editable") and current.get("editable"))


def matches_owner(owner, current):
    """Only a known, collapsed caret in the same non-password field is owned."""
    return bool(
        owner
        and current
        and not owner.get("password", False)
        and not current.get("password", False)
        and owner.get("identity") is not None
        and owner.get("prefix") is not None
        and owner.get("caret") is not None
        and all(owner.get(k) == current.get(k) for k in ("identity", "prefix", "caret"))
        and owner.get("hwnd") == current.get("hwnd")
    )
