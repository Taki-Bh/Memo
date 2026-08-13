"""
Composer
========

Loads ui/composer.ui and wires up:

  * send-button enabled/disabled + subtle "active" QSS state based on
    whether there's text
  * Enter-to-send / Shift+Enter-for-newline (handled inside
    AutoResizeTextEdit itself; we just listen to its sendRequested
    signal)
  * a live character counter
  * clearing + resetting height after a message is sent
"""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from widgets.auto_resize_text_edit import AutoResizeTextEdit
from widgets.glass_button import GlassButton
from widgets.ui_loader import CustomUiLoader

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

MAX_CHARS = 4000  # tweak freely; set to None to hide the counter entirely


class Composer(QWidget):
    messageSent = Signal(str)
    attachmentRequested = Signal()
    toolsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = CustomUiLoader({
            "AutoResizeTextEdit": AutoResizeTextEdit,
            "GlassButton": GlassButton,
        })
        self.ui = loader.load_ui(UI_DIR / "composer.ui")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.text_edit: AutoResizeTextEdit = self.ui.messageInput
        self.send_button: GlassButton = self.ui.sendButton
        self.attachment_button: GlassButton = self.ui.attachmentButton
        self.tools_button: GlassButton = self.ui.toolsButton
        self.char_count_label = self.ui.charCountLabel

        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.sendRequested.connect(self._send)
        self.send_button.clicked.connect(self._send)
        self.attachment_button.clicked.connect(self.attachmentRequested.emit)
        self.tools_button.clicked.connect(self.toolsRequested.emit)

        self._on_text_changed()

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        has_text = bool(text.strip())
        self.send_button.setEnabled(has_text)
        self.send_button.setProperty("active", has_text)
        self.send_button.style().unpolish(self.send_button)
        self.send_button.style().polish(self.send_button)

        if MAX_CHARS:
            remaining = MAX_CHARS - len(text)
            self.char_count_label.setText(str(remaining) if remaining < 200 else "")

    def _send(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        self.messageSent.emit(text)
        self.text_edit.clear_and_reset()

    def set_enabled_state(self, enabled: bool):
        """Disable input while the assistant is 'thinking'."""
        self.text_edit.setEnabled(enabled)
        self.attachment_button.setEnabled(enabled)
        self.tools_button.setEnabled(enabled)
        if enabled:
            self._on_text_changed()
        else:
            self.send_button.setEnabled(False)
