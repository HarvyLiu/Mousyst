"""Conservative ownership checks for external text edits."""


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
