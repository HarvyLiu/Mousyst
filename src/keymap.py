"""Displayed US-English characters, separate from native shortcut key codes."""

SHIFT_SYMBOLS = dict(
    zip("1234567890-=[]\\;',./`", '!@#$%^&*()_+{}|:"<>?~', strict=True)
)


def shifted_text(value):
    return SHIFT_SYMBOLS.get(value, value.upper())
