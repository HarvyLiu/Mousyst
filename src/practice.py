"""Isolated click/swipe experiment. Never imports desktop input hooks."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine

from keyboard_layout import keys
from shortcut_practice import ShortcutPractice
from text_model import Editor
from word_recognizer import Recognizer

TASKS = (
    (
        "can you meet after lunch?",
        "search for a quiet cafe",
        "label this folder summer",
        "send alex 2 files",
        "the total is 12 + 5",
        "hello anna, see you soon",
    ),
    (
        "could we talk after dinner?",
        "find a nearby pizza place",
        "name this folder winter",
        "give sam 3 photos",
        "the result is 10 - 4",
        "thanks emma, talk to you soon",
    ),
    (
        "will you call after work?",
        "look for a local bookshop",
        "mark this folder spring",
        "show ben 4 notes",
        "the answer is 15 / 3",
        "sorry ella, see you later",
    ),
)


class Controller(QObject):
    changed = Signal()
    trialReset = Signal()
    resultReady = Signal(int, int, object, float)
    selectionRequested = Signal(int, int)
    captureRequested = Signal()

    def __init__(self):
        super().__init__()
        self.editor = Editor()
        self.shortcuts = ShortcutPractice()
        self.modifiers = set()
        self.shortcut_events = []
        self.shortcut_activity = False
        self.mode = 1
        self.shift = False
        self.candidates = []
        self.generation = 0
        self.busy = False
        self.status = "Click letters or hold left-click and swipe a word."
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.recognizer = None
        self.resultReady.connect(self.receive)
        self.task_index = 0
        self.participant = 0
        self.started = time.perf_counter()
        self.first_entry = None
        self.travel = 0.0
        self.last_pointer = None
        self.corrections = 0
        self.latencies = []
        self.results = []
        self.recording = False
        self.strokes = []
        self.status = "Loading offline vocabulary…"
        self.executor.submit(self.load)

    def load(self):
        try:
            self.recognizer = Recognizer()
            self.resultReady.emit(-1, -1, [], 0)
        except (OSError, ValueError, KeyError) as exc:
            self.resultReady.emit(-2, -1, [str(exc)], 0)

    @Property("QVariantList", constant=True)
    def keys(self):
        return keys()

    @Property(str, notify=changed)
    def text(self):
        return self.editor.text

    @Property(str, notify=changed)
    def target(self):
        if self.shortcut_activity:
            return "Try Ctrl+A, Ctrl+C, End, Ctrl+V; then Win+Shift+S."
        return TASKS[(self.participant + self.mode) % 3][self.task_index % 6]

    @Property("QVariantList", notify=changed)
    def activeModifiers(self):
        return [m for m in ("Ctrl", "Alt", "Win") if m in self.modifiers]

    @Slot(str)
    def modifier(self, name):
        self.invalidate()
        if name in self.modifiers:
            self.modifiers.remove(name)
        else:
            self.modifiers.add(name)
        self.changed.emit()

    @Slot(bool)
    def shortcutActivity(self, enabled):
        self.shortcut_activity = enabled
        self.reset()
        if enabled:
            self.editor.external("copy this text")
        self.changed.emit()

    @Slot(str, int, int, int)
    def activateKey(self, key, start, end, cursor):
        if not self.modifiers:
            if key == "End":
                self.selectionRequested.emit(len(self.text), len(self.text))
            else:
                self.key(key)
            return
        self.entry()
        self.invalidate()
        mods = [m for m in ("Ctrl", "Alt", "Win") if m in self.modifiers]
        if self.shift:
            mods.append("Shift")
        chord = "+".join(mods + [key.upper()])
        text, selection, message = self.shortcuts.apply(
            chord, self.text, start, end, cursor
        )
        if text != self.text:
            self.editor.external(text)
        self.modifiers.clear()
        self.shift = False
        self.shortcut_events.append(
            {
                "chord": chord,
                "elapsed_seconds": time.perf_counter() - self.started,
                "activity": self.shortcut_activity,
                "trial": self.started,
            }
        )
        self.status = chord + " · " + message
        self.changed.emit()
        if selection is not None:
            self.selectionRequested.emit(*selection)
        if chord == "Win+Shift+S":
            self.captureRequested.emit()

    @Slot(int, int)
    def captureRegion(self, width, height):
        self.status = f"Win+Shift+S · Practice region selected: {width} × {height} px. No desktop screenshot taken."
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def suggestions(self):
        return self.candidates

    @Property(str, notify=changed)
    def message(self):
        return self.status

    @Property(bool, notify=changed)
    def shifted(self):
        return self.shift

    def invalidate(self):
        self.generation += 1
        self.busy = False
        self.candidates = []

    def entry(self):
        if self.first_entry is None:
            self.first_entry = time.perf_counter()

    @Slot()
    def cancel(self):
        self.invalidate()
        self.modifiers.clear()
        self.shift = False
        self.status = "Stroke cancelled."
        self.changed.emit()

    @Slot(int)
    def condition(self, mode):
        self.mode = mode
        self.reset()

    @Slot(int)
    def participantChanged(self, value):
        self.participant = value
        self.reset()

    @Slot(str)
    def physical(self, text):
        if self.mode == 2 and text != self.editor.text:
            self.entry()
            if len(text) < len(self.editor.text):
                self.corrections += 1
            self.invalidate()
            self.editor.external(text)
            self.changed.emit()

    @Slot(str)
    def key(self, value):
        self.entry()
        self.invalidate()
        if value == "Shift":
            self.shift = not self.shift
        elif value == "Back":
            self.editor.backspace()
            self.corrections += 1
        elif value == "Undo":
            self.editor.undo()
            self.corrections += 1
        else:
            self.editor.insert(value.upper() if self.shift else value)
            self.shift = False
        self.changed.emit()

    @Slot(int)
    def alternative(self, index):
        if 0 <= index < len(self.candidates):
            self.editor.replace(self.candidates[index])
            self.corrections += int(index != 0)
            self.changed.emit()

    @Slot("QVariantList")
    def stroke(self, points):
        if self.mode != 1 or self.recognizer is None:
            return
        path = [(float(p["x"]), float(p["y"])) for p in points]
        if len(path) < 2:
            return
        self.entry()
        self.invalidate()
        generation, revision = self.generation, self.editor.revision
        uppercase = self.shift
        self.busy = True
        started = time.perf_counter()
        if self.recording:
            self.strokes.append({"target": self.target, "points": path})

        def work():
            try:
                words = self.recognizer.recognize(path)
                if uppercase:
                    words = [w.capitalize() for w in words]
            except (ValueError, IndexError, KeyError):
                words = []
            self.resultReady.emit(
                generation, revision, words, (time.perf_counter() - started) * 1000
            )

        self.executor.submit(work)

    @Slot(int, int, object, float)
    def receive(self, generation, revision, words, latency):
        if generation < 0:
            self.status = (
                "Ready — all recognition runs offline."
                if generation == -1
                else "Vocabulary failed to load: " + str(words)
            )
        elif generation == self.generation and revision == self.editor.revision:
            self.busy = False
            if words:
                self.editor.word(words[0])
                self.candidates = words
                self.latencies.append(latency)
                self.status = f"{latency:.0f} ms · alternatives replace the last word"
                self.shift = False
            else:
                self.status = "No match. Click the letters to spell this word."
        self.changed.emit()

    @Slot(float)
    def distance(self, pixels):
        self.travel += pixels

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtQuick import QQuickWindow

        if isinstance(watched, QQuickWindow) and event.type() == QEvent.MouseMove:
            point = event.globalPosition()
            if self.last_pointer is not None:
                self.travel += (
                    (point.x() - self.last_pointer[0]) ** 2
                    + (point.y() - self.last_pointer[1]) ** 2
                ) ** 0.5
            self.last_pointer = (point.x(), point.y())
        return False

    @Slot()
    def reset(self):
        self.invalidate()
        self.modifiers.clear()
        self.shift = False
        self.shortcuts = ShortcutPractice()
        self.editor.external("copy this text" if self.shortcut_activity else "")
        self.started = time.perf_counter()
        self.first_entry = None
        self.travel = 0.0
        self.corrections = 0
        self.latencies = []
        self.last_pointer = None
        self.trialReset.emit()
        self.changed.emit()

    @Slot(int, str)
    def finish(self, comfort, preference):
        now = time.perf_counter()
        elapsed = now - self.started
        if self.shortcut_activity:
            self.results.append(
                {
                    "activity": "shortcuts",
                    "participant": self.participant,
                    "mode": self.mode,
                    "elapsed_seconds": elapsed,
                    "comfort": comfort,
                    "preference": preference,
                    "pointer_pixels": self.travel,
                    "events": [
                        event.copy()
                        for event in self.shortcut_events
                        if event["elapsed_seconds"] <= elapsed
                        and event.get("trial") == self.started
                    ],
                }
            )
            self.reset()
            self.status = (
                "Shortcut trial and rating retained in memory. Export when ready."
            )
            self.changed.emit()
            return
        self.results.append(
            {
                "participant": self.participant,
                "mode": self.mode,
                "target": self.target,
                "text": self.text,
                "correct": self.text.rstrip() == self.target,
                "elapsed_seconds": elapsed,
                "entry_wpm": len(self.text.rstrip())
                / 5
                * 60
                / max(0.001, now - (self.first_entry or self.started)),
                "remaining_errors": edit_distance(self.target, self.text.rstrip()),
                "corrections": self.corrections,
                "pointer_pixels": self.travel,
                "recognition_ms": self.latencies[:],
                "comfort": comfort,
                "preference": preference,
            }
        )
        self.task_index += 1
        self.reset()
        self.status = f"{len(self.results)} trials retained in memory. Export only when requested."
        self.changed.emit()

    @Slot(bool)
    def record(self, enabled):
        self.recording = enabled

    @Slot()
    def export(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            None, "Export local experiment", "mousyst-results.json", "JSON (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(
                    {
                        "trials": self.results,
                        "opt_in_strokes": self.strokes,
                        "shortcut_events": self.shortcut_events,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def main():
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    QQuickStyle.setStyle("Basic")
    app = QApplication([])
    controller = Controller()
    app.installEventFilter(controller)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("practice", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui/Practice.qml")))
    if not engine.rootObjects():
        return 1
    if args.smoke_test:
        smoke_started = time.perf_counter()

        def fail(message):
            folder = Path("build/practice")
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "smoke.json").write_text(
                json.dumps({"ok": False, "error": str(message)})
            )
            app.exit(1)

        def smoke():
            from PySide6.QtCore import QPoint, QPointF, Qt
            from PySide6.QtQuick import QQuickItem
            from PySide6.QtTest import QTest

            from keyboard_layout import CENTERS

            try:
                if (
                    controller.recognizer is None
                    and time.perf_counter() - smoke_started < 15
                ):
                    QTimer.singleShot(100, smoke)
                    return
                window = engine.rootObjects()[0]
                window.setProperty("keyboardOpen", True)
                QTest.qWait(30)
                board = window.findChild(QQuickItem, "letterBoard")
                pitch = float(window.property("pitch"))

                def position(c):
                    x, y = CENTERS[c]
                    p = board.mapToScene(QPointF(x * pitch - 1, y * pitch - 1))
                    return QPoint(round(p.x()), round(p.y()))

                assert controller.recognizer is not None, "Vocabulary not ready"
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position("a"))
                assert controller.text == "a", controller.text
                toggle = window.findChild(QQuickItem, "numericToggle")
                toggle_point = toggle.mapToScene(
                    QPointF(toggle.width() / 2, toggle.height() / 2)
                ).toPoint()
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, toggle_point)
                assert window.property("symbols"), "Numeric toggle did not activate"
                label = next(
                    child
                    for key in board.childItems()
                    for child in key.childItems()
                    if child.objectName() == "keyLabel_q"
                )
                assert label.property("text") == "1", "Numeric labels did not update"
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position("q"))
                assert controller.text == "a1", "Numeric key did not enter a digit"
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, toggle_point)
                assert label.property("text") == "q", "Alphabet labels did not return"
                controller.reset()
                window.setProperty("keyboardOpen", True)
                QTest.qWait(20)
                QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, position("h"))
                for c in "elo":
                    QTest.mouseMove(window, position(c), 10)
                QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, position("o"))

                def verify():
                    try:
                        if (
                            not controller.candidates
                            and time.perf_counter() - smoke_started < 15
                        ):
                            QTimer.singleShot(100, verify)
                            return
                        assert "hello" in controller.candidates, controller.candidates
                        controller.alternative(controller.candidates.index("hello"))
                        assert controller.text == "hello "
                        folder = Path("build/practice")
                        folder.mkdir(parents=True, exist_ok=True)
                        window.grabWindow().save(str(folder / "practice.png"))
                        controller.key(",")
                        assert controller.text == "hello,"
                        latency = controller.latencies[:]
                        controller.shortcutActivity(True)
                        window.setProperty("keyboardOpen", True)
                        QTest.qWait(30)

                        def find_item(item, name):
                            if item.objectName() == name:
                                return item
                            for child in item.childItems():
                                result = find_item(child, name)
                                if result is not None:
                                    return result
                            return None

                        def button(name):
                            item = find_item(window.contentItem(), name)
                            assert item is not None, name
                            point = item.mapToScene(
                                QPointF(item.width() / 2, item.height() / 2)
                            ).toPoint()
                            QTest.mouseClick(
                                window, Qt.LeftButton, Qt.NoModifier, point
                            )

                        def letter(c):
                            QTest.mouseClick(
                                window, Qt.LeftButton, Qt.NoModifier, position(c)
                            )

                        button("modifier_Ctrl")
                        letter("a")
                        button("modifier_Ctrl")
                        letter("c")
                        assert controller.shortcuts.clipboard == "copy this text"
                        button("endKey")
                        button("modifier_Ctrl")
                        letter("v")
                        assert (
                            controller.text == "copy this textcopy this text"
                        ), controller.text
                        assert not controller.activeModifiers
                        button("modifier_Win")
                        button("modifier_Shift")
                        letter("s")
                        snip = window.findChild(QQuickItem, "practiceSnip")
                        assert snip.isVisible(), "Snip exercise did not open"
                        QTest.mousePress(
                            window, Qt.LeftButton, Qt.NoModifier, QPoint(100, 150)
                        )
                        QTest.mouseMove(window, QPoint(300, 250), 10)
                        QTest.mouseRelease(
                            window, Qt.LeftButton, Qt.NoModifier, QPoint(300, 250)
                        )
                        assert not snip.isVisible()
                        assert "200 × 100" in controller.message, controller.message
                        window.grabWindow().save(str(folder / "shortcuts.png"))
                        (folder / "smoke.json").write_text(
                            json.dumps(
                                {
                                    "ok": True,
                                    "latency_ms": latency,
                                    "shortcuts": [
                                        "Ctrl+A",
                                        "Ctrl+C",
                                        "Ctrl+V",
                                        "Win+Shift+S",
                                    ],
                                }
                            )
                        )
                        app.exit(0)
                    except (AssertionError, AttributeError, RuntimeError) as exc:
                        fail(exc)

                QTimer.singleShot(500, verify)
            except (AssertionError, RuntimeError, AttributeError) as exc:
                fail(exc)

        QTimer.singleShot(700, smoke)
    result = app.exec()
    controller.executor.shutdown(wait=True, cancel_futures=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
