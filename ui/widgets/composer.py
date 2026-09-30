
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.widgets.auto_resize_text_edit import AutoResizeTextEdit
from ui.widgets.glass_button import GlassButton
from ui.widgets.ui_loader import CustomUiLoader


UI_DIR = Path(__file__).resolve().parent.parent / "ui"

MAX_CHARS = 4000  # Set to None to hide the counter entirely


class Composer(QWidget):
    messageSent = Signal(str)
    stopRequested = Signal()
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

        self._processing = False

        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.sendRequested.connect(self._send)
        self.send_button.clicked.connect(self._on_send_button_clicked)
        self.attachment_button.clicked.connect(
            self.attachmentRequested.emit
        )
        self.tools_button.clicked.connect(
            self.toolsRequested.emit
        )

        self._on_text_changed()

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        has_text = bool(text.strip())

        if not self._processing:
            self.send_button.setEnabled(has_text)
            self.send_button.setProperty("active", has_text)

        self.send_button.style().unpolish(self.send_button)
        self.send_button.style().polish(self.send_button)

        if MAX_CHARS:
            remaining = MAX_CHARS - len(text)
            self.char_count_label.setText(
                str(remaining) if remaining < 200 else ""
            )

    def _on_send_button_clicked(self):
        if self._processing:
            self.stopRequested.emit()
            print("STOOOOP")
            return

        self._send()

    def _send(self):
        text = self.text_edit.toPlainText().strip()

        if not text:
            return

        self.messageSent.emit(text)
        self.text_edit.clear_and_reset()

    def set_enabled_state(self, enabled: bool):
        """Enable normal input, or show a clickable greyed stop button."""
        self._processing = not enabled

        self.text_edit.setEnabled(enabled)
        self.attachment_button.setEnabled(enabled)
        self.tools_button.setEnabled(enabled)

        if enabled:
            self.send_button.setProperty("processing", False)
            self._on_text_changed()

        else:
            # Keep the button enabled so Qt can receive the click.
            # The greyed appearance is purely visual.
            self.send_button.setEnabled(True)
            self.send_button.setProperty("active", False)
            self.send_button.setProperty("processing", True)

            self.send_button.style().unpolish(self.send_button)
            self.send_button.style().polish(self.send_button)
