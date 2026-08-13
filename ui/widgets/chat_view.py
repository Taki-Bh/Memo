"""
ChatView
========

Loads ui/chat_view.ui (header + scrollable message area + composer
placeholder) and layers on:

  * the empty state ("How can I help?" + suggestion cards)
  * appending user/AI ChatMessage bubbles
  * the animated "thinking" indicator
  * embedding the Composer widget into composerContainer
"""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.chat_message import ChatMessage
from ui.widgets.composer import Composer
from ui.widgets.glass_button import GlassButton
from ui.widgets.typing_indicator import TypingIndicator
from ui.widgets.ui_loader import CustomUiLoader

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

SUGGESTIONS = [
    ("💡", "Explain a concept"),
    ("✍️", "Write something"),
    ("📄", "Analyze a file"),
    ("🧠", "Help me brainstorm"),
]


class ChatView(QWidget):
    messageSent = Signal(str)
    suggestionActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = CustomUiLoader({"GlassButton": GlassButton})
        self.ui = loader.load_ui(UI_DIR / "chat_view.ui")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.ui.modelSelectorCombo.addItems(["Aurora — Balanced", "Aurora — Fast", "Aurora — Precise"])

        # Embed the composer into its placeholder container.
        composer_layout = QVBoxLayout(self.ui.composerContainer)
        composer_layout.setContentsMargins(0, 0, 0, 0)
        self.composer = Composer(self.ui.composerContainer)
        composer_layout.addWidget(self.composer)
        self.composer.messageSent.connect(self._on_message_sent)

        self._messages_layout: QVBoxLayout = self.ui.messagesLayout
        self._tail_spacer = self._messages_layout.takeAt(self._messages_layout.count() - 1)

        self.typing_indicator = TypingIndicator()
        self.typing_indicator.hide()

        self.empty_state = self._build_empty_state()
        self._messages_layout.addWidget(self.empty_state)
        self._messages_layout.addWidget(self.typing_indicator)
        self._messages_layout.addItem(self._tail_spacer)

        self._has_messages = False

    # ------------------------------------------------------------------
    # Empty state
    # ------------------------------------------------------------------
    def _build_empty_state(self):
        container = QWidget()
        container.setObjectName("emptyState")
        outer = QVBoxLayout(container)
        outer.addStretch(1)

        orb = QLabel("✦")
        orb.setObjectName("emptyStateOrb")
        orb.setAlignment(Qt.AlignCenter)
        outer.addWidget(orb)

        heading = QLabel("How can I help?")
        heading.setObjectName("emptyStateHeading")
        heading.setAlignment(Qt.AlignCenter)
        outer.addWidget(heading)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        cards_row.addStretch(1)
        for icon, label in SUGGESTIONS:
            card = GlassButton(f"{icon}  {label}")
            card.setObjectName("suggestionCard")
            card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            card.setMinimumHeight(46)
            card.clicked.connect(lambda _, t=label: self.suggestionActivated.emit(t))
            cards_row.addWidget(card)
        cards_row.addStretch(1)
        outer.addLayout(cards_row)

        outer.addStretch(2)
        return container

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------
    def _on_message_sent(self, text: str):
        self.messageSent.emit(text)

    def add_user_message(self, text: str):
        self._ensure_conversation_started()
        message = ChatMessage("user", text, timestamp=_now())
        self._insert_message(message)

    def add_ai_message(self, text: str) -> ChatMessage:
        self._ensure_conversation_started()
        message = ChatMessage("ai", text, timestamp=_now())
        self._insert_message(message)
        return message

    def _insert_message(self, message: ChatMessage):
        index = self._messages_layout.indexOf(self.typing_indicator)
        self._messages_layout.insertWidget(index, message)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _ensure_conversation_started(self):
        if not self._has_messages:
            self._has_messages = True
            self.empty_state.hide()

    def show_typing(self, show: bool):
        self.composer.set_enabled_state(not show)
        if show:
            self.typing_indicator.start()
        else:
            self.typing_indicator.stop()
        QTimer.singleShot(0, self._scroll_to_bottom)

    def clear_conversation(self):
        for i in reversed(range(self._messages_layout.count())):
            item = self._messages_layout.itemAt(i)
            widget = item.widget()
            if widget is None or widget in (self.empty_state, self.typing_indicator):
                continue
            self._messages_layout.takeAt(i)
            widget.deleteLater()
        self._has_messages = False
        self.empty_state.show()

    def _scroll_to_bottom(self):
        bar = self.ui.messageScrollArea.verticalScrollBar()
        bar.setValue(bar.maximum())


def _now() -> str:
    return datetime.now().strftime("%H:%M")
