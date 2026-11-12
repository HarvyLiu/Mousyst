"""Local shortcut exercises; never sends OS input or reads the system clipboard."""

from dataclasses import dataclass, field


@dataclass
class ShortcutPractice:
    clipboard: str = ""
    history: list[str] = field(default_factory=list)

    def apply(self, chord, text, start, end, cursor):
        start, end = sorted(
            (max(0, min(len(text), start)), max(0, min(len(text), end)))
        )
        cursor = max(0, min(len(text), cursor))
        if chord == "Ctrl+A":
            return text, (0, len(text)), "Selected all practice text."
        if chord == "Ctrl+C":
            if start == end:
                return text, None, "Select text first, then copy."
            self.clipboard = text[start:end]
            return text, None, "Copied selection to the practice clipboard."
        if chord == "Ctrl+X":
            if start == end:
                return text, None, "Select text first, then cut."
            self.clipboard = text[start:end]
            self.history.append(text)
            return text[:start] + text[end:], (start, start), "Cut selection."
        if chord == "Ctrl+V":
            if not self.clipboard:
                return text, None, "Practice clipboard is empty."
            self.history.append(text)
            if start == end:
                start = end = cursor
            result = text[:start] + self.clipboard + text[end:]
            position = start + len(self.clipboard)
            return result, (position, position), "Pasted from the practice clipboard."
        if chord == "Ctrl+Z":
            if self.history:
                result = self.history.pop()
                return (
                    result,
                    (len(result), len(result)),
                    "Undid the last shortcut edit.",
                )
            return text, None, "No shortcut edit to undo."
        if chord == "Win+Shift+S":
            return text, None, "Drag a region in the practice snipping area."
        return text, None, f"{chord} recorded; no local exercise action is assigned."
