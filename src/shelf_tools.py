"""Qt binding for target-bound editing actions and explicitly saved local content."""

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from user_content import EDITS, KEYS, UserLibrary, read_library, write_library


class ShelfTools(QObject):
    changed = Signal()
    noticeChanged = Signal()

    def __init__(self, desktop):
        super().__init__(desktop)
        self.desktop = desktop
        self.library = UserLibrary(desktop.settings.path.parent)
        self.notice = " ".join(self.library.errors)

    @Property(str, notify=noticeChanged)
    def message(self):
        return self.notice

    def report(self, message):
        self.notice = message
        self.noticeChanged.emit()

    @Property("QStringList", constant=True)
    def keys(self):
        return KEYS

    @Property("QVariantList", constant=True)
    def edits(self):
        return [{"label": label, "id": label} for label, key, mods in EDITS]

    @Property("QVariantList", notify=changed)
    def favorites(self):
        return self.library.items["favorites"]

    @Property("QVariantList", notify=changed)
    def phrases(self):
        return sorted(
            self.library.items["phrases"], key=lambda item: not item["pinned"]
        )

    def update(self, action):
        try:
            result = action()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.report(str(exc))
            return ""
        self.changed.emit()
        self.report("Saved.")
        return result or "ok"

    @Slot(str, str, str, "QStringList", result=str)
    def saveFavorite(self, identifier, label, key, modifiers):
        return self.update(
            lambda: self.library.save(
                "favorites",
                identifier,
                {
                    "label": label.strip(),
                    "key": key,
                    "modifiers": modifiers,
                },
            )
        )

    @Slot(str, str, str, str, bool, result=str)
    def savePhrase(self, identifier, label, text, category, pinned):
        return self.update(
            lambda: self.library.save(
                "phrases",
                identifier,
                {
                    "label": label.strip(),
                    "text": text.replace("\r\n", "\n").replace("\r", "\n"),
                    "category": category.strip(),
                    "pinned": pinned,
                },
            )
        )

    @Slot(str, str, str, result=bool)
    def change(self, kind, identifier, operation):
        return bool(
            self.update(lambda: self.library.change(kind, identifier, operation))
        )

    @Slot(str, bool)
    def transfer(self, kind, importing):
        if kind not in ("favorites", "phrases"):
            return
        label = "Import" if importing else "Export"
        dialog = (
            QFileDialog.getOpenFileName if importing else QFileDialog.getSaveFileName
        )
        path, _ = dialog(
            None,
            f"{label} {kind}",
            "" if importing else kind + ".json",
            "JSON files (*.json)",
        )
        if not path:
            return
        if importing:
            self.update(lambda: self.library.replace(kind, read_library(kind, path)))
        else:
            self.update(lambda: write_library(kind, path, self.library.items[kind]))

    def verify(self, needs_editable=False):
        desktop = self.desktop
        field = (
            desktop.snapshot()
            if desktop.output and desktop.output.is_current()
            else None
        )
        if (
            not field
            or not desktop.output.is_current()
            or not field.get("identity")
            or field["identity"] != desktop.current_field
            or field.get("hwnd") != desktop.output.target
            or field.get("password", False)
            or (needs_editable and not field.get("editable"))
        ):
            raise RuntimeError(
                "Middle-click a non-password text field to use this tool."
            )
        return field

    @Slot(result=bool)
    def allowPhraseShelf(self):
        try:
            self.verify(True)
            return True
        except RuntimeError:
            return False

    @Slot(result=bool)
    def ready(self):
        if self.desktop.pendingCount:
            self.desktop.status = "Finish pending input before using these tools."
            self.desktop.changed.emit()
            return False
        return True

    @Slot(str, str)
    def run(self, kind, identifier):
        desktop = self.desktop
        if not self.ready():
            return
        desktop.cancel()

        def perform():
            field = self.verify(kind == "phrases")
            if kind == "edit":
                if identifier == "Delete word left" and field.get("classic_edit"):
                    # A classic Win32 EDIT inserts DEL for Ctrl+Backspace.
                    if not field.get("has_selection"):
                        desktop.output.chord("Left", ["Ctrl", "Shift"])
                        if not self.verify(True).get("has_selection"):
                            return
                    desktop.output.chord("Back", [])
                    return
                action = next(
                    ((key, mods) for label, key, mods in EDITS if label == identifier),
                    None,
                )
                if action is None:
                    return
                desktop.output.chord(*action)
            elif kind in ("phrases", "favorites"):
                try:
                    item = self.library.items[kind][self.library.find(kind, identifier)]
                except ValueError:
                    raise RuntimeError("This entry no longer exists.") from None
                if kind == "favorites":
                    desktop.output.chord(item["key"], item["modifiers"])
                else:
                    for number, line in enumerate(item["text"].split("\n")):
                        if number:
                            self.verify(True)
                            desktop.output.chord("Enter", [])
                        for offset in range(0, len(line), 32):
                            self.verify(True)
                            desktop.send_text(line[offset : offset + 32])

        desktop.dispatch(perform)
        desktop.changed.emit()
