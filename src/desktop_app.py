"""Compact mouse keyboard desktop host and explicit target-bound input adapter."""

import argparse
import json
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QLockFile,
    QObject,
    QPoint,
    QStandardPaths,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QGuiApplication, QPalette
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from accessibility import FocusObserver
from desktop import DesktopInput, MiddleButtonHook
from input_session import accepts_insertion, matches_owner
from keymap import shifted_text
from practice import Controller
from settings import DEFAULTS, Settings
from shelf_tools import ShelfTools
from swipe_learning import SwipeLearning
from tray import app_icon
from welcome import WelcomeCard
from window_behavior import KeyboardActivationFilter


@dataclass(frozen=True)
class QueuedInput:
    value: str | list
    shift: bool
    modifiers: tuple[str, ...]


def expected_edit(field, removed, inserted):
    """Predict a collapsed caret after a known local output for queue verification."""
    if not field or field.get("password"):
        return None
    if field["prefix"] is None or field["caret"] is None:
        return field
    prefix = field["prefix"]
    if removed > len(inserted) and field["caret"] > len(prefix):
        # The newly exposed start of the 512-character prefix is unknown.
        return None
    return dict(
        field,
        prefix=((prefix[:-removed] if removed else prefix) + inserted)[-512:],
        caret=max(0, field["caret"] - removed) + len(inserted),
    )


class DesktopController(Controller):
    desktopChanged = Signal()
    hideRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, smoke=False):
        super().__init__()
        self.changed.connect(self.desktopChanged.emit)
        self.settings = Settings()
        self.learning = SwipeLearning(self.settings.path.parent)
        self.learning_points = None
        self.shelf_tools = ShelfTools(self)
        self.output = None if smoke else DesktopInput()
        self.observer = None if smoke else FocusObserver()
        self.owner = None
        self.selected_candidate = 0
        self.current_field = None
        self.suppressed = None
        self.repeat_key = ""
        self.repeating = False
        self.repeat_timer = QTimer(self)
        self.repeat_timer.timeout.connect(self.repeat_tick)
        self.pending_inputs = deque()
        self.inflight_job = None
        self.pending_field = None
        self.waiting_target = None
        self.last_edit_target = None
        self.verify_timer = QTimer(self)
        self.verify_timer.setSingleShot(True)
        self.verify_timer.timeout.connect(self.drain_inputs)
        self.recognition_timer = QTimer(self)
        self.recognition_timer.setSingleShot(True)
        self.recognition_timer.timeout.connect(
            lambda: self.stop_pending(
                "Recognition timed out. Enter the pending input again."
            )
        )
        self.spelling = None
        self.no_match = False
        self.status = self.settings.error or "Middle-click a text field to type."

    @Property(QObject, constant=True)
    def tools(self):
        return self.shelf_tools

    @Property("QVariantMap", notify=desktopChanged)
    def preferences(self):
        return self.settings.value

    @Property(str, notify=desktopChanged)
    def settingsJson(self):
        return json.dumps(self.preferences, indent=2)

    @Property(bool, notify=desktopChanged)
    def isRepeating(self):
        return self.repeating

    @Property(int, notify=desktopChanged)
    def selectedSuggestion(self):
        return self.selected_candidate if self.candidates else 0

    @Property(int, notify=desktopChanged)
    def suggestionSession(self):
        return self.generation

    @Property(bool, notify=desktopChanged)
    def needsSpelling(self):
        return self.no_match

    @Property(bool, notify=desktopChanged)
    def isSpelling(self):
        return self.spelling is not None

    @Property(int, notify=desktopChanged)
    def pendingCount(self):
        return len(self.pending_inputs) + int(self.busy or self.no_match)

    @Slot(int)
    def cycleSuggestion(self, steps):
        if self.candidates:
            index = max(
                0, min(len(self.candidates) - 1, self.selectedSuggestion + steps)
            )
            if index != self.selectedSuggestion:
                self.alternative(index)

    @Slot(str, result=str)
    def shiftLabel(self, value):
        return shifted_text(value)

    @Slot(float, float, result=str)
    def aim(self, x, y):
        from keyboard_layout import CENTERS

        candidates = sorted(
            CENTERS, key=lambda c: (CENTERS[c][0] - x) ** 2 + (CENTERS[c][1] - y) ** 2
        )
        best = candidates[0]
        bx, by = CENTERS[best]
        if abs(bx - x) > 0.6 or abs(by - y) > 0.6:
            return ""
        if (
            not self.preferences["hitboxAssist"]
            or self.modifiers
            or getattr(self, "password", False)
        ):
            return best
        if abs(bx - x) < 0.4 and abs(by - y) < 0.4:
            return best
        prefix = self.editor.text.split(" ")[-1].lower()
        weights = {c: 1.0 for c in candidates[:2]}
        if self.recognizer:
            for rank, word in enumerate(self.recognizer.words[:5000]):
                if (
                    word.startswith(prefix)
                    and len(word) > len(prefix)
                    and word[len(prefix)] in weights
                ):
                    weights[word[len(prefix)]] += 1 / (rank + 1)
        return min(
            candidates[:2],
            key=lambda c: (
                (CENTERS[c][0] - x) ** 2 + (CENTERS[c][1] - y) ** 2 - 0.02 * weights[c]
            ),
        )

    @Slot(str)
    def saveSettings(self, text):
        try:
            self.settings.save(json.loads(text))
            self.sync_personal_words()
            self.cancel()
            self.status = "Settings saved."
        except (OSError, ValueError, TypeError) as exc:
            self.status = "Settings: " + str(exc)
        self.changed.emit()

    @Slot()
    def reloadSettings(self):
        self.cancel()
        self.settings.reload()
        self.sync_personal_words()
        self.status = self.settings.error or "Configuration reloaded."
        self.changed.emit()

    @Slot(str, "QVariant")
    def setPreference(self, name, value):
        self.saveSettings(json.dumps(dict(self.preferences, **{name: value})))

    def sync_personal_words(self):
        if self.recognizer is not None:
            self.recognizer.set_personal_words(self.preferences["personalWords"])
            self.sync_learning()

    def sync_learning(self):
        if self.recognizer is not None:
            self.recognizer.learned = self.learning.state if self.preferences["swipeLearning"] else ({}, (0, 0))

    @Slot()
    def clearLearning(self):
        self.learning_points = None
        try:
            self.learning.clear()
            self.sync_learning()
            self.status = "Swipe learning cleared."
        except OSError as exc:
            self.status = str(exc)
        self.changed.emit()

    def confirm_swipe(self, field):
        points, self.learning_points = self.learning_points, None
        if (not points or not self.preferences["swipeLearning"] or not self.candidates
                or not matches_owner(self.owner, field)):
            return
        try:
            self.learning.remember(self.candidates[self.selected_candidate], points, self.selected_candidate != 0)
            self.sync_learning()
        except OSError:
            self.status = "Could not save swipe learning."

    @Slot(str, int, result=bool)
    def editPersonalWord(self, spelling, index):
        words = list(self.preferences["personalWords"])
        if index == -1:
            words.append(spelling.strip())
        elif 0 <= index < len(words):
            if spelling:
                words[index] = spelling.strip()
            else:
                del words[index]
        else:
            return False
        self.setPreference("personalWords", words)
        return self.preferences["personalWords"] == words

    @Slot(str, str)
    def setSymbol(self, key, value):
        symbols = dict(self.preferences["symbols"])
        symbols[key] = value
        self.setPreference("symbols", symbols)

    @Slot()
    def importSettings(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            None, "Import Mousyst settings", "", "JSON (*.json)"
        )
        if path:
            try:
                self.saveSettings(Path(path).read_text(encoding="utf-8"))
            except OSError as exc:
                self.status = str(exc)
                self.changed.emit()

    @Slot()
    def exportSettings(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            None, "Export Mousyst settings", "mousyst-settings.json", "JSON (*.json)"
        )
        if path:
            try:
                Path(path).write_text(self.settingsJson, encoding="utf-8")
            except OSError as exc:
                self.status = str(exc)
                self.changed.emit()

    @Slot()
    def resetSettings(self):
        self.saveSettings(json.dumps(DEFAULTS))

    @Slot()
    def configFolder(self):
        self.settings.path.parent.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.settings.path.parent)))

    def snapshot(self):
        return self.observer.verify() if self.observer else None

    def send_text(self, text):
        if self.output:
            units = text.encode("utf-16-le", errors="surrogatepass")
            for index in range(0, len(units), 2):
                char = chr(int.from_bytes(units[index : index + 2], "little"))
                self.output.send("SPACE" if char == " " else char)

    def dispatch(self, callback):
        try:
            callback()
            return True
        except (RuntimeError, OSError) as exc:
            self.cancel()
            self.status = str(exc)
            self.changed.emit()
            return False

    @Slot(str)
    def key(self, value):
        if value == "Escape":
            self.cancel()
            self.hideRequested.emit()
            return
        if value == "Shift":
            self.shift = not self.shift
            self.changed.emit()
            return
        if value in ("Ctrl", "Alt", "Win"):
            if value in self.modifiers:
                self.modifiers.remove(value)
            else:
                self.modifiers.add(value)
            self.changed.emit()
            return
        if self.spelling is not None:
            if self.output and not accepts_insertion(
                self.pending_field, self.snapshot()
            ):
                self.stop_pending("Field or caret changed. Pending input cancelled.")
                return
            if value in (" ", "Enter"):
                self.finishSpelling()
            elif value == "Back":
                self.spelling = self.spelling[:-1]
            elif len(value) == 1 and not self.modifiers:
                self.spelling += shifted_text(value) if self.shift else value
                self.shift = False
            if self.spelling is not None:
                self.status = self.spelling or "Click letters to spell your word."
                self.changed.emit()
            return
        self.submit_input(value)

    def submit_input(self, value):
        action = QueuedInput(value, self.shift, tuple(self.activeModifiers))
        if self.busy or self.waiting_target is not None or self.no_match:
            if self.no_match:
                self.status = "Spell the unrecognized word or cancel pending input."
                self.changed.emit()
                return
            if len(self.pending_inputs) >= 8:
                self.status = "Queue full. This input was not added."
                self.changed.emit()
                return
            # While recognition runs the target should still match its start.
            # During verification the host may still be applying our last output.
            if (
                self.busy
                and self.output
                and not accepts_insertion(self.pending_field, self.snapshot())
            ):
                self.stop_pending("Field or caret changed. Pending input cancelled.")
                return
            self.pending_inputs.append(action)
            self.shift = False
            self.modifiers.clear()
            self.changed.emit()
            return
        self.shift = False
        self.modifiers.clear()
        if isinstance(value, str):
            self.last_edit_target = self.commit_key(
                action, self.snapshot() if self.output else None
            )
        else:
            self.begin_stroke(action, self.snapshot())
        self.changed.emit()

    def commit_key(self, action, current):
        value = action.value
        if not action.modifiers and (len(value) == 1 or value in ("Enter", "SPACE")):
            self.confirm_swipe(current)
        else:
            self.learning_points = None
        mods = list(action.modifiers) + (["Shift"] if action.shift else [])
        if self.last_edit_target and not matches_owner(self.last_edit_target, current):
            self.editor.external("")
            self.last_edit_target = None
        if action.modifiers:
            self.owner = None
            self.editor.external("")
            self.invalidate()
            if self.output:
                self.dispatch(lambda: self.output.chord(value, mods))
            self.changed.emit()
            return None
        named = (
            "Back",
            "Enter",
            "Tab",
            "Left",
            "Right",
            "Up",
            "Down",
            "Home",
            "End",
            "Delete",
            "PageUp",
            "PageDown",
            "NumLock",
            "Add",
            "Subtract",
            "Multiply",
            "Divide",
            "Decimal",
        )
        if (
            value in named
            or value.startswith("F")
            and value[1:].isdigit()
            or value.startswith("Num")
        ):
            self.owner = None
            self.invalidate()
            if self.output and not self.dispatch(
                lambda: self.output.chord(value, mods)
            ):
                return None
            if value == "Back":
                self.editor.backspace()
            else:
                self.editor.external("")
            self.changed.emit()
            if value == "Back" and not mods:
                return expected_edit(current, 1, "")
            return None
        text = shifted_text(value) if action.shift else value
        sensitive = self.output and (not current or current.get("password", False))
        if (
            self.output
            and self.editor.auto_space
            and not matches_owner(self.owner, current)
        ):
            # A local trailing space is not permission to delete external text.
            self.editor.external("")
        before = self.editor.text
        self.editor.insert(text)
        after = self.editor.text
        if after == before:
            return current

        removed = int(bool(before) and not after.startswith(before))

        def send():
            if removed and self.output:
                self.output.chord("Back", [])
            self.send_text(text)

        if not self.dispatch(send):
            return None
        if sensitive:
            self.editor.external("")
        self.owner = None
        self.invalidate()
        self.changed.emit()
        return expected_edit(current, removed, text)

    @Slot(str)
    def secondary(self, letter):
        self.releaseHold()
        symbol = self.preferences["symbols"].get(letter, "")
        if symbol:
            self.key(symbol)

    @Slot(int, int, object, float)
    def receive(self, generation, revision, words, latency):
        if generation < 0:
            super().receive(generation, revision, words, latency)
            if generation == -1:
                self.sync_personal_words()
                self.status = (
                    "Middle-click to show or hide · Right-click a letter for its symbol"
                )
                self.changed.emit()
            return
        if generation != self.generation:
            return
        self.inflight_job = None
        self.recognition_timer.stop()
        if revision != self.editor.revision:
            self.stop_pending("Text changed. Pending input cancelled.")
            return
        before = self.snapshot()
        pending = getattr(self, "pending_field", None)
        if self.output and not accepts_insertion(pending, before):
            self.cancel()
            self.status = "Field changed or could not be verified. Use exact clicks."
            self.changed.emit()
            return
        if before and before["password"]:
            self.cancel()
            return
        old = self.editor.text
        self.selected_candidate = 0
        next_shift = self.shift
        super().receive(generation, revision, words, latency)
        self.shift = next_shift
        if not words:
            self.no_match = True
            self.status = "No match. Spell your word or cancel pending input."
            self.changed.emit()
            return
        addition = self.editor.text[len(old) :]
        if addition and not self.dispatch(lambda: self.send_text(addition)):
            return
        self.owner = None
        if before and before["prefix"] is not None:
            self.owner = expected_edit(before, 0, addition)
        elif self.output:
            self.candidates = []
            self.editor.external("")
            self.status = "Word entered. Alternatives unavailable in this text control."
        if self.pending_inputs:
            self.wait_for_output(self.owner or before)
            self.drain_inputs()
        self.changed.emit()

    @Slot("QVariantList")
    def stroke(self, points):
        if len(points) >= 2:
            self.submit_input(points)

    def begin_stroke(self, action, target):
        self.confirm_swipe(target)
        self.pending_field = target
        if self.output and (
            not self.pending_field or self.pending_field.get("password", False)
        ):
            self.cancel()
            self.status = (
                "Field could not be verified for swipe typing. Use exact clicks."
            )
            self.changed.emit()
            return
        if self.recognizer is None:
            self.status = "Swipe vocabulary unavailable. Click letters to type."
            self.changed.emit()
            return
        if self.output and not (
            matches_owner(self.owner, self.pending_field)
            or matches_owner(self.last_edit_target, self.pending_field)
        ):
            self.editor.external("")
            self.owner = None
        self.last_edit_target = None
        if self.preferences["swipeLearning"] and target and not target.get("password", True):
            self.learning_points = [(p["x"], p["y"]) for p in (action.value[0], action.value[-1])]
        self.inflight_job = self.start_stroke(action.value, action.shift)
        if self.busy:
            self.recognition_timer.start(5000)
            self.status = "Recognizing swipe…"

    def stop_pending(self, message):
        self.cancel()
        self.status = message
        self.changed.emit()

    def wait_for_output(self, target):
        # SendInput returning does not mean the host's accessibility tree has updated.
        self.waiting_target = (target, time.monotonic() + 0.4)

    def drain_inputs(self):
        while self.pending_inputs and self.waiting_target is not None:
            target, deadline = self.waiting_target
            current = self.snapshot() if self.output else None
            if self.output and not accepts_insertion(target, current):
                if (
                    target
                    and current
                    and not current.get("password")
                    and current.get("identity") == target.get("identity")
                    and current.get("hwnd") == target.get("hwnd")
                    and time.monotonic() < deadline
                ):
                    self.verify_timer.start(16)
                    return
                self.stop_pending("Field or caret changed. Pending input cancelled.")
                return
            self.waiting_target = None
            action = self.pending_inputs.popleft()
            if isinstance(action.value, list):
                self.begin_stroke(action, current)
                self.changed.emit()
                return
            if (
                self.output
                and current["caret"] is None
                and (len(action.value) != 1 or action.modifiers)
            ):
                self.stop_pending("Caret unavailable. Use this editing key directly.")
                return
            after = self.commit_key(action, current)
            self.last_edit_target = after
            if self.pending_inputs:
                if self.output and after is None:
                    self.stop_pending(
                        "Command changed the editing context. Enter remaining input again."
                    )
                    return
                self.wait_for_output(after)
        self.changed.emit()

    @Slot()
    def spellWord(self):
        if self.no_match:
            self.spelling = ""
            self.status = "Click letters, then press Insert word."
            self.changed.emit()

    @Slot()
    def finishSpelling(self):
        if not self.spelling or not self.no_match:
            return
        word = self.spelling
        self.learning_points = None
        self.spelling = None
        self.no_match = False
        self.receive(self.generation, self.editor.revision, [word], 0)

    @Slot(int)
    def alternative(self, index):
        if self.pendingCount or not 0 <= index < len(self.candidates):
            return
        current = self.snapshot()
        if self.output and not matches_owner(self.owner, current):
            self.owner = None
            self.invalidate()
            self.status = "Caret or field changed; alternatives cleared."
            self.changed.emit()
            return
        if self.editor.span is None:
            return
        start, end = self.editor.span
        old = self.editor.text[start:end]
        new = self.candidates[index] + " "
        if old.startswith(" "):
            new = " " + new

        def replace():
            if self.output:
                for _ in old:
                    self.output.chord("Back", [])
            self.send_text(new)

        if self.dispatch(replace):
            self.editor.replace(self.candidates[index])
            self.selected_candidate = index
            if self.owner:
                self.owner["prefix"] = (self.owner["prefix"][: -len(old)] + new)[-512:]
                self.owner["caret"] += len(new) - len(old)
        self.changed.emit()

    @Slot()
    def undoWord(self):
        if self.pendingCount or self.editor.span is None:
            return
        current = self.snapshot()
        if self.output and not matches_owner(self.owner, current):
            self.cancel()
            return
        start, end = self.editor.span
        if self.output and not self.dispatch(
            lambda: [self.output.chord("Back", []) for _ in range(end - start)]
        ):
            self.editor.external("")
            return
        self.editor.undo()
        self.owner = None
        self.invalidate()
        self.changed.emit()

    @Slot(str)
    def hold(self, key):
        self.releaseHold()
        self.repeat_key = key
        self.repeating = False
        if key in ("Back", "Left", "Right", "Up", "Down"):
            self.key(key)
        if not self.modifiers:
            self.repeat_timer.start(int(self.preferences["repeatDelay"]))

    def repeat_tick(self):
        if not self.repeat_key:
            return
        self.repeating = True
        value = self.repeat_key.upper() if self.shift else self.repeat_key
        self.key(value)
        self.repeat_key = value
        self.repeat_timer.setInterval(int(self.preferences["repeatInterval"]))

    @Slot()
    def releaseHold(self):
        self.repeat_timer.stop()
        self.repeat_key = ""

    @Slot(int)
    def scrub(self, steps):
        self.releaseHold()
        for _ in range(abs(steps)):
            self.key("Right" if steps > 0 else "Left")

    @Slot(int)
    def scrubVertical(self, steps):
        self.releaseHold()
        for _ in range(abs(steps)):
            self.key("Down" if steps > 0 else "Up")

    @Slot()
    def cancel(self):
        self.learning_points = None
        if self.inflight_job is not None:
            self.inflight_job.cancel()
            self.inflight_job = None
        self.pending_inputs.clear()
        self.verify_timer.stop()
        self.recognition_timer.stop()
        self.waiting_target = None
        self.last_edit_target = None
        self.spelling = None
        self.no_match = False
        if hasattr(self, "repeat_timer"):
            self.releaseHold()
        self.owner = None
        self.pending_field = None
        self.editor.external("")
        super().cancel()
        self.status = (
            "Middle-click to show or hide · Right-click a letter for its symbol"
        )

    @Slot()
    def reset(self):
        self.cancel()
        super().reset()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--test-layout-report", type=Path)
    args = parser.parse_args()
    development = args.development or Path(sys.executable).stem.lower() == "mousystnext"
    if development:
        import os

        os.environ["MOUSYST_SETTINGS_DIR"] = str(
            Path(__file__).resolve().parents[1] / "build/development-settings"
        )
    instance_name = "MousystNext" if development else "MousystDesktop"
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv[:1])
    if args.smoke_test:
        # Offscreen Qt does not discover system fonts on some Windows runners.
        import os
        from tempfile import TemporaryDirectory

        from PySide6.QtGui import QFontDatabase

        smoke_root = Path("build/desktop").resolve()
        smoke_root.mkdir(parents=True, exist_ok=True)
        smoke_profile = TemporaryDirectory(prefix="profile-", dir=smoke_root)
        os.environ["MOUSYST_SETTINGS_DIR"] = smoke_profile.name

        QFontDatabase.addApplicationFont(
            str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf")
        )
    app.setApplicationName("Mousyst")
    app.setWindowIcon(app_icon())
    palette = QPalette()
    for role, color in (
        (QPalette.Window, "#171719"),
        (QPalette.Base, "#25252b"),
        (QPalette.AlternateBase, "#202025"),
        (QPalette.Text, "#eeeeef"),
        (QPalette.WindowText, "#eeeeef"),
        (QPalette.Button, "#2c2c33"),
        (QPalette.ButtonText, "#eeeeef"),
        (QPalette.Highlight, "#666674"),
        (QPalette.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(
        str(
            Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
            / ("mousyst-next.lock" if development else "mousyst-desktop.lock")
        )
    )
    if not args.smoke_test and not lock.tryLock(100):
        socket = QLocalSocket()
        socket.connectToServer(instance_name)
        if socket.waitForConnected(300):
            socket.write(b"show")
            socket.waitForBytesWritten(300)
        return 0
    controller = DesktopController(args.smoke_test)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("mousyst", controller)
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(e.toString() for e in errors)
    )
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui/Desktop.qml")))
    if not engine.rootObjects():
        Path("build/desktop-errors.json").write_text(json.dumps(warnings))
        controller.executor.shutdown(wait=True)
        return 1
    window = engine.rootObjects()[0]
    welcome = WelcomeCard()
    activation = KeyboardActivationFilter(
        window, lambda: controller.output.target if controller.output else 0
    )
    app.installNativeEventFilter(activation)
    window.visibleChanged.connect(activation.apply)
    if args.test_layout_report:

        def report_layout():
            from PySide6.QtCore import QPointF
            from PySide6.QtQuick import QQuickItem

            board = window.findChild(QQuickItem, "desktopLetters")
            if not window.isVisible() or not board:
                return
            pitch = float(window.property("pitch"))
            point = board.mapToGlobal(QPointF(1.5 * pitch, 0.5 * pitch))
            args.test_layout_report.write_text(
                json.dumps({"q": [round(point.x()), round(point.y())]})
            )

        for signal in (
            window.visibleChanged,
            window.xChanged,
            window.yChanged,
            window.widthChanged,
            window.heightChanged,
        ):
            signal.connect(lambda: QTimer.singleShot(60, report_layout))

    def hide():
        controller.suppressed = controller.current_field
        controller.cancel()
        window.hide()

    def show(hwnd=None):
        welcome.hide()
        if controller.output and not controller.output.capture(
            hwnd or int(__import__("desktop").user32.GetForegroundWindow())
        ):
            return
        field = controller.snapshot()
        controller.password = bool(field and field["password"])
        controller.current_field = field["identity"] if field else None
        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point) or app.primaryScreen()
        bounds = screen.availableGeometry()
        window.setPosition(
            QPoint(
                max(
                    bounds.left(),
                    min(
                        point.x() - window.width() // 2, bounds.right() - window.width()
                    ),
                ),
                max(
                    bounds.top(), min(point.y() + 20, bounds.bottom() - window.height())
                ),
            )
        )
        controller.editor.external("")
        controller.cancel()
        activation.apply()
        window.show()

    controller.hideRequested.connect(hide)
    server = QLocalServer()
    if not args.smoke_test:
        QLocalServer.removeServer(instance_name)
        server.listen(instance_name)

        def activate_existing():
            connection = server.nextPendingConnection()
            if connection:
                connection.disconnectFromServer()
            welcome.hide()
            window.setProperty("settingsOpen", True)

        server.newConnection.connect(activate_existing)
    menu = QMenu()
    menu.addAction("Show keyboard", lambda: show())
    menu.addAction("Welcome & tips", welcome.present)
    menu.addAction("Settings", lambda: window.setProperty("settingsOpen", True))
    menu.addAction("Quit", app.quit)
    tray = QSystemTrayIcon(app.windowIcon(), app)
    tray.setContextMenu(menu)
    tray.setToolTip(
        "Mousyst NEXT · testing branch"
        if development
        else "Mousyst · middle-click to type"
    )
    tray.activated.connect(
        lambda reason: show() if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()
    hook = MiddleButtonHook()
    hook.toggled.connect(lambda hwnd: hide() if window.isVisible() else show(int(hwnd)))
    hook.failed.connect(
        lambda message: (
            setattr(controller, "status", message) or controller.changed.emit()
        )
    )
    if not args.smoke_test:
        hook.start()
        app.aboutToQuit.connect(hook.stop)
        app.aboutToQuit.connect(controller.observer.stop)
        guard = QTimer()
        guard.setInterval(100)
        guard.timeout.connect(
            lambda: (
                hide()
                if window.isVisible()
                and not window.property("settingsOpen")
                and controller.output.target
                and not controller.output.is_current()
                else None
            )
        )
        guard.start()
        if not args.test_layout_report:
            welcome.present()
    else:
        window.show()

        def smoke():
            from PySide6.QtCore import QPointF, Qt
            from PySide6.QtGui import QWheelEvent
            from PySide6.QtQuick import QQuickItem
            from PySide6.QtTest import QTest

            from keyboard_layout import CENTERS

            folder = Path("build/desktop")
            folder.mkdir(parents=True, exist_ok=True)
            try:
                board = window.findChild(QQuickItem, "desktopLetters")
                x, y = CENTERS["q"]
                pitch = float(window.property("pitch"))
                point = board.mapToScene(QPointF((x + 1) * pitch, y * pitch)).toPoint()
                enter = window.findChild(QQuickItem, "desktopEnter")
                back = window.findChild(QQuickItem, "desktopBackspace")
                stable = (
                    board.mapToScene(QPointF(0, 0)),
                    enter.mapToScene(QPointF(0, 0)),
                    window.height(),
                )
                for words in (["hello"], ["hello", "help", "held"]):
                    controller.candidates = words
                    controller.changed.emit()
                    QTest.qWait(25)
                    assert (
                        board.mapToScene(QPointF(0, 0)),
                        enter.mapToScene(QPointF(0, 0)),
                        window.height(),
                    ) == stable, "Suggestions moved the keyboard"
                controller.editor.external("")
                controller.receive(
                    controller.generation,
                    controller.editor.revision,
                    ["hello", "help", "held"],
                    20,
                )
                QTest.qWait(25)
                suggestions = window.findChild(QQuickItem, "desktopSuggestions")
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    suggestions.mapToScene(
                        QPointF(suggestions.width() / 2 - 15, 17)
                    ).toPoint(),
                )
                QTest.qWait(25)
                assert (
                    controller.editor.text == "help "
                    and controller.selectedSuggestion == 1
                )
                wheel_point = suggestions.mapToScene(
                    QPointF(suggestions.width() / 2, 17)
                )

                def wheel(delta):
                    event = QWheelEvent(
                        wheel_point,
                        QPointF(window.mapToGlobal(wheel_point.toPoint())),
                        QPoint(),
                        QPoint(0, delta),
                        Qt.NoButton,
                        Qt.NoModifier,
                        Qt.NoScrollPhase,
                        False,
                    )
                    QApplication.sendEvent(window, event)
                    QTest.qWait(25)

                wheel(-120)
                assert (
                    controller.editor.text == "held "
                    and controller.selectedSuggestion == 2
                )
                wheel(240)
                assert (
                    controller.editor.text == "hello "
                    and controller.selectedSuggestion == 0
                )
                wheel(-60)
                assert suggestions.property("wheelDelta") == -60
                controller.cancel()
                controller.receive(
                    controller.generation,
                    controller.editor.revision,
                    ["world", "word"],
                    20,
                )
                QTest.qWait(25)
                assert suggestions.property("wheelDelta") == 0
                assert suggestions.property("candidateIndex") == 0
                from types import SimpleNamespace

                navigation = []
                controller.output = SimpleNamespace(
                    chord=lambda key, mods: navigation.append(("key", key)),
                    send=lambda text: navigation.append(("text", text)),
                )
                space_point = window.property("spaceCenter").toPoint()
                for dx, dy in [(-18, 0), (18, 0), (0, -26), (0, 26)]:
                    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, space_point)
                    QTest.mouseMove(window, space_point + QPoint(dx, dy), 25)
                    QTest.mouseRelease(
                        window,
                        Qt.LeftButton,
                        Qt.NoModifier,
                        space_point + QPoint(dx, dy),
                    )
                assert navigation == [
                    ("key", k) for k in ("Left", "Left", "Right", "Right", "Up", "Down")
                ], navigation
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, space_point)
                assert navigation[-1] == ("text", "SPACE")
                controller.output = None
                controller.cancel()
                controller.editor.external("hello ")
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    back.mapToScene(
                        QPointF(back.width() / 2, back.height() / 2)
                    ).toPoint(),
                )
                QTest.qWait(25)
                assert not controller.candidates
                assert (
                    board.mapToScene(QPointF(0, 0)),
                    enter.mapToScene(QPointF(0, 0)),
                    window.height(),
                ) == stable, "Backspace moved Enter"
                controller.editor.external("")
                QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, point)
                for letter in "efve":
                    px, py = CENTERS[letter]
                    QTest.mouseMove(
                        window,
                        board.mapToScene(
                            QPointF((px + 1) * pitch, py * pitch)
                        ).toPoint(),
                        18,
                    )
                QTest.qWait(20)
                window.grabWindow().save(str(folder / "glide.png"))
                visible_points = board.property("visualPoints").toVariant()
                assert 1 < len(visible_points) <= 48, "Trail was not sampled or bounded"
                QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, point)
                controller.cancel()
                controller.editor.external("")
                QTest.qWait(300)
                assert not board.property("visualPoints").toVariant(), (
                    "Glide trail did not fade"
                )
                QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point)
                assert controller.editor.text == "1", controller.editor.text
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
                assert controller.editor.text == "1q", controller.editor.text
                QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, point)
                QTest.qWait(570)
                QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, point)
                assert len(controller.editor.text) >= 4, controller.editor.text
                controller.cancel()
                toggle = window.findChild(QQuickItem, "numericLayerToggle")
                number_board = window.findChild(QQuickItem, "desktopNumbers")
                format_toggle = window.findChild(QQuickItem, "numberFormatToggle")

                def click_item(item):
                    QTest.mouseClick(
                        window,
                        Qt.LeftButton,
                        Qt.NoModifier,
                        item.mapToScene(
                            QPointF(item.width() / 2, item.height() / 2)
                        ).toPoint(),
                    )
                    QTest.qWait(25)

                fixed = (window.height(), toggle.mapToScene(QPointF(0, 0)))
                click_item(toggle)
                assert (
                    window.property("numbers")
                    and number_board.isVisible()
                    and not board.isVisible()
                )
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "Number layer expanded or moved controls"
                before = controller.editor.text
                digit_point = (
                    QPointF(4 * pitch, 1.875 * pitch)
                    if controller.preferences["numberFormat"] == "Numpad"
                    else QPointF(0.5 * pitch, 0.5 * pitch)
                )
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    number_board.mapToScene(digit_point).toPoint(),
                )
                QTest.qWait(25)
                assert controller.editor.text == before + "1", (
                    "Number layer did not type digit"
                )
                click_item(format_toggle)
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "Numpad switch expanded keyboard"
                click_item(toggle)
                assert (
                    not window.property("numbers")
                    and board.isVisible()
                    and not number_board.isVisible()
                )
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "ABC failed to restore same geometry"
                window.setProperty("numbers", True)
                for preset in ("Standard", "Full", "Compact"):
                    controller.settings.value = dict(
                        controller.preferences, layout=preset, numberFormat="Numpad"
                    )
                    controller.changed.emit()
                    QTest.qWait(20)
                window.grabWindow().save(str(folder / "keyboard.png"))
                window.setProperty("numbers", False)
                controller.settings.value = dict(controller.preferences)
                controller.changed.emit()
                QTest.qWait(30)
                window.grabWindow().save(str(folder / "keyboard-clean.png"))
                window.setProperty("settingsOpen", True)
                QTest.qWait(80)
                from PySide6.QtQuick import QQuickWindow

                settings_window = window.findChild(QQuickWindow, "desktopSettings")
                settings_window.grabWindow().save(str(folder / "settings.png"))

                def settings_click(name):
                    def find_item(parent):
                        if parent.objectName() == name:
                            return parent
                        for child in parent.childItems():
                            found = find_item(child)
                            if found is not None:
                                return found
                        return None

                    item = find_item(settings_window.contentItem())
                    assert item is not None, name
                    QTest.mouseClick(
                        settings_window,
                        Qt.LeftButton,
                        Qt.NoModifier,
                        item.mapToScene(
                            QPointF(item.width() / 2, item.height() / 2)
                        ).toPoint(),
                    )
                    QTest.qWait(50)

                original_accent = controller.preferences["accent"]
                settings_click("settingsAccentColor")
                settings_click("colorSwatch#bfe8d5")
                assert controller.preferences["accent"] == original_accent
                settings_window.grabWindow().save(str(folder / "color-picker.png"))
                settings_click("settingsColorCancel")
                assert controller.preferences["accent"] == original_accent
                settings_click("settingsAccentColor")
                settings_click("colorSwatch#bfe8d5")
                settings_click("settingsColorApply")
                assert controller.preferences["accent"] == "#bfe8d5"
                settings_click("settingsAccentColor")
                settings_click("colorHue")
                settings_click("settingsColorApply")
                assert controller.preferences["accent"] != "#bfe8d5"
                controller.setPreference("accent", original_accent)
                word_editor = settings_window.findChild(QObject, "personalWordInput")
                word_editor.setProperty("text", "Mousyst")
                word_editor.saveWord()
                assert controller.preferences["personalWords"] == ["Mousyst"]
                assert "Mousyst" in controller.recognizer.recognize([CENTERS[c] for c in "mousyst"])
                assert controller.editPersonalWord("", 0)
                window.setProperty("settingsOpen", False)
                (folder / "smoke.json").write_text(
                    json.dumps(
                        {
                            "ok": True,
                            "checks": [
                                "save a personal spelling from Settings, recognize its swipe, and remove it",
                                "right-click symbol",
                                "click",
                                "hold repeat",
                                "three layouts",
                                "numpad",
                                "matching line icons",
                                "bounded crossing trail and fade-out",
                                "fixed suggestion area and Enter position after Backspace",
                                "ABC/numbers replace keys without expansion; digit entry; numpad switch",
                                "in-panel color picker: preview, Cancel, Apply, hue slider",
                                "suggestion click, wheel in both directions, multi-notch wheel, reset between words",
                                "Spacebar caret scrub in four directions without stray spaces; tap inserts space",
                            ],
                        }
                    )
                )
                app.exit(0)
            except (AssertionError, AttributeError, RuntimeError) as exc:
                import traceback

                (folder / "smoke.json").write_text(
                    json.dumps(
                        {
                            "ok": False,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                )
                app.exit(1)

        QTimer.singleShot(1800, smoke)
    result = app.exec()
    controller.executor.shutdown(wait=True, cancel_futures=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
