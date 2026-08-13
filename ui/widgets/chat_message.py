"""
ChatMessage
============

Renders a single message in the conversation. Two flavors, selected via
the `role` argument ("user" or "ai"), which drives both layout
(right-aligned vs left-aligned) and QSS styling (objectName +
dynamic "role" property).

AI messages use QTextBrowser with Qt's built-in Markdown support
(`setMarkdown`, available since Qt 5.14 / Qt6), which gives us:
    * headings, bold/italic, lists
    * fenced code blocks (monospace, background box)
    * tables
for free, in your own words / actual model output -- no extra
Markdown-parsing dependency required.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from widgets.glass_button import GlassButton


class ChatMessage(QWidget):
    regenerateRequested = Signal()

    def __init__(self, role: str, text: str, timestamp: str = "", parent=None):
        """
        role: "user" or "ai"
        """
        super().__init__(parent)
        self.role = role
        self.setProperty("role", role)
        self.setObjectName("chatMessage")
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 6, 16, 6)

        bubble = QWidget(self)
        bubble.setObjectName("messageBubble")
        bubble.setProperty("role", role)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 10, 16, 10)
        bubble_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        if role == "ai":
            avatar = QLabel("✦")
            avatar.setObjectName("aiAvatar")
            header_row.addWidget(avatar)
            name = QLabel("Assistant")
            name.setObjectName("messageAuthor")
            header_row.addWidget(name)
        header_row.addStretch(1)
        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setObjectName("messageTimestamp")
            header_row.addWidget(time_label)
        bubble_layout.addLayout(header_row)

        self.body = QTextBrowser(bubble)
        self.body.setObjectName("messageBody")
        self.body.setOpenExternalLinks(True)
        self.body.setFrameShape(QTextBrowser.NoFrame)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if role == "ai":
            self.body.setMarkdown(text)
        else:
            self.body.setPlainText(text)
        self.body.document().documentLayout().documentSizeChanged.connect(
            self._fit_body_height
        )
        bubble_layout.addWidget(self.body)

        self.actions_row = QWidget(bubble)
        actions_layout = QHBoxLayout(self.actions_row)
        actions_layout.setContentsMargins(0, 2, 0, 0)
        actions_layout.setSpacing(4)

        self.copy_button = GlassButton("Copy")
        self.copy_button.setObjectName("messageActionButton")
        self.copy_button.clicked.connect(self._copy_text)
        actions_layout.addWidget(self.copy_button)

        if role == "ai":
            self.regenerate_button = GlassButton("Regenerate")
            self.regenerate_button.setObjectName("messageActionButton")
            self.regenerate_button.clicked.connect(self.regenerateRequested.emit)
            actions_layout.addWidget(self.regenerate_button)

        actions_layout.addStretch(1)
        self.actions_row.setVisible(False)
        bubble_layout.addWidget(self.actions_row)

        bubble.setMaximumWidth(720)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if role == "user":
            outer.addStretch(1)
            outer.addWidget(bubble, 0)
        else:
            outer.addWidget(bubble, 0)
            outer.addStretch(1)

        self._raw_text = text
        self._fit_body_height()

    def _fit_body_height(self, *_):
        doc_height = self.body.document().size().height()
        self.body.setFixedHeight(int(doc_height) + 8)

    def _copy_text(self):
        QApplication.clipboard().setText(self._raw_text)

    def enterEvent(self, event):
        self.actions_row.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.actions_row.setVisible(False)
        super().leaveEvent(event)
