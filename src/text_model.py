"""Practice-only editing, with revision-safe word replacement."""

from dataclasses import dataclass


@dataclass
class Editor:
    text: str = ""
    revision: int = 0
    span: tuple[int, int] | None = None
    auto_space: bool = False

    def external(self, text):
        self.text = text
        self.revision += 1
        self.span = None
        self.auto_space = False

    def insert(self, text):
        if text == " " and self.auto_space:
            return
        base = self.text[:-1] if self.auto_space and text in ".,!?;:)" else self.text
        self.external(base + text)

    def word(self, word):
        start = len(self.text)
        prefix = "" if not self.text or self.text[-1].isspace() else " "
        self.external(self.text + prefix + word + " ")
        self.span = (start, len(self.text))
        self.auto_space = True

    def replace(self, word):
        if self.span is not None:
            start, end = self.span
            prefix = " " if self.text[start : start + 1] == " " else ""
            self.text = self.text[:start] + prefix + word + " " + self.text[end:]
            self.revision += 1
            self.span = (start, start + len(prefix + word + " "))
            self.auto_space = True

    def undo(self):
        if self.span is not None:
            start, end = self.span
            self.external(self.text[:start] + self.text[end:])

    def backspace(self):
        self.external(self.text[:-1])
