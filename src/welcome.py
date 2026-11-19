"""Startup tips in a lightweight window independent of the typing overlay."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from tray import app_icon


class WelcomeCard(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowTitle("Welcome to Mousyst")
        self.setObjectName("welcome")
        self.setStyleSheet("""
            QWidget#welcome { background: #19191d; border: 1px solid #44444b; }
            QLabel { color: #c7c7cc; font: 10pt 'Segoe UI'; }
            QLabel#title { color: #f1f1f3; font: 600 18pt 'Segoe UI'; }
            QPushButton { background: #c5e7d1; color: #18201b; border: none;
                border-radius: 5px; padding: 8px 18px; font: 600 10pt 'Segoe UI'; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(36, 36))
        layout.addWidget(logo)
        title = QLabel("Welcome to Mousyst")
        title.setObjectName("title")
        layout.addWidget(title)
        for tip in (
            "Click a text field, then press the middle mouse button to open the keyboard.",
            "Click letters or hold the left button and glide through a word. Scroll over the suggestions to change it.",
            "Middle-click again to hide the keyboard. Right-click the M in the system tray for tips, settings or Quit.",
        ):
            label = QLabel(tip)
            label.setWordWrap(True)
            layout.addWidget(label)
        done = QPushButton("Got it")
        done.clicked.connect(self.hide)
        layout.addWidget(done, alignment=Qt.AlignRight)

    def present(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry()
        self.setFixedWidth(min(370, bounds.width()))
        self.adjustSize()
        self.move(bounds.center() - self.rect().center())
        self.show()
        self.raise_()
        self.activateWindow()

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate and self.isVisible():
            self.hide()
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
