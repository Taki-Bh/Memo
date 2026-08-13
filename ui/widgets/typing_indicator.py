"""
TypingIndicator
================

A minimal "AI is thinking" row: a small glowing dot plus three
pulsing dots, matching the glass/neumorphic visual language. Driven
by a single QPropertyAnimation-free QTimer tick that advances a phase
counter -- deliberately simple, since this widget's only job is a
lightweight, cheap ambient animation.
"""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("typingIndicator")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)

        self.avatar = QLabel("✦")
        self.avatar.setObjectName("aiAvatar")
        layout.addWidget(self.avatar)

        self.dots = [QLabel("•") for _ in range(3)]
        for dot in self.dots:
            dot.setObjectName("typingDot")
            layout.addWidget(dot)

        self.text_label = QLabel("Thinking...")
        self.text_label.setObjectName("typingText")
        layout.addWidget(self.text_label)
        layout.addStretch(1)

        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._phase = (self._phase + 1) % len(self.dots)
        for i, dot in enumerate(self.dots):
            dot.setProperty("active", i == self._phase)
            dot.style().unpolish(dot)
            dot.style().polish(dot)
