"""
ConfirmationMessage
===================

Renders a confirmation message in the conversation.

Uses the same general structure as ChatMessage:
    * Same outer alignment/layout
    * Same message bubble
    * Same message body
    * Same QSS object/property hooks
    * Same sizing behavior

The bottom section is reserved for a Yes / No selection.
It is intended to occupy roughly one fifth of the message bubble's
content area.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.glass_button import GlassButton


class ConfirmationMessage(QWidget):
    yesRequested = Signal()
    noRequested = Signal()

    def __init__(
        self,
        role: str,
        text: str,
        timestamp: str = "",
        parent=None,
    ):
        """
        role: "user" or "ai"
        """
        super().__init__(parent)

        self.role = role
        self.setProperty("role", role)
        self.setObjectName("confirmationMessage")
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 6, 16, 6)

        # ---------------------------------------------------------
        # Message bubble
        # ---------------------------------------------------------

        bubble = QWidget(self)
        bubble.setObjectName("messageBubble")
        bubble.setProperty("role", role)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 10, 16, 10)
        bubble_layout.setSpacing(6)

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Message body
        # ---------------------------------------------------------

        self.body = QTextBrowser(bubble)
        self.body.setObjectName("messageBody")
        self.body.setOpenExternalLinks(True)
        self.body.setFrameShape(QTextBrowser.NoFrame)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum,
        )

        if role == "ai":
            self.body.setMarkdown(text)
        else:
            self.body.setPlainText(text)

        self.body.document().documentLayout().documentSizeChanged.connect(
            self._fit_body_height
        )

        bubble_layout.addWidget(self.body)

        # ---------------------------------------------------------
        # Confirmation area
        #
        # This is the bottom ~20% section of the message.
        # The stretch keeps it visually separated from the body
        # while allowing the bubble itself to remain responsive.
        # ---------------------------------------------------------

        self.confirmation_area = QWidget(bubble)
        self.confirmation_area.setObjectName("confirmationArea")
        self.confirmation_area.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        confirmation_layout = QHBoxLayout(self.confirmation_area)
        confirmation_layout.setContentsMargins(0, 4, 0, 0)
        confirmation_layout.setSpacing(6)

        confirmation_layout.addStretch(1)

        self.no_button = GlassButton("No")
        self.no_button.setObjectName("confirmationButton")
        self.no_button.clicked.connect(self.noRequested.emit)
        confirmation_layout.addWidget(self.no_button)

        self.yes_button = GlassButton("Yes")
        self.yes_button.setObjectName("confirmationButton")
        self.yes_button.clicked.connect(self.yesRequested.emit)


        confirmation_layout.addWidget(self.yes_button)

        confirmation_layout.addStretch(1)

        bubble_layout.addWidget(self.confirmation_area)

        # ---------------------------------------------------------
        # Bubble sizing / alignment
        # ---------------------------------------------------------

        bubble.setMaximumWidth(720)
        bubble.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Minimum,
        )

        if role == "user":
            outer.addStretch(1)
            outer.addWidget(bubble, 0)
        else:
            outer.addWidget(bubble, 0)
            outer.addStretch(1)

        self._raw_text = text

        self._fit_body_height()

    # -------------------------------------------------------------
    # Body sizing
    # -------------------------------------------------------------

    def _fit_body_height(self, *_):
        doc_height = self.body.document().size().height()

        # Leave room for the confirmation section at the bottom.
        self.body.setFixedHeight(int(doc_height) + 8)