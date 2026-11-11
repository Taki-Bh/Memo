"""
AutoResizeTextEdit
===================

A QPlainTextEdit that grows to fit its content (typed newlines OR
wrapped lines) and shrinks back down, between a configurable minimum
and maximum height. Once the content would exceed the maximum height,
an internal scrollbar takes over instead of growing further.

Design notes / why this approach:

* No QTimer polling. Height is recalculated synchronously whenever
  Qt tells us the document changed (`textChanged`) or the widget was
  resized (which can change how many lines the *same* text wraps
  into). This avoids jitter/flicker entirely.
* Height comes from `QPlainTextEdit.document().size()` /
  `documentLayout().documentSize()`, i.e. real layout metrics rather
  than a naive "count '\n' characters" heuristic -- so soft-wrapped
  lines are measured correctly too.
* Cursor position is never touched by the resize logic, so typing
  and navigation feel completely normal.
* Enter-to-send / Shift+Enter-for-newline is implemented here via
  keyPressEvent and exposed as a `sendRequested` signal, so the
  parent Composer decides what "send" actually does.

Safe to promote in Qt Designer:
    base class   -> QPlainTextEdit
    promoted to  -> AutoResizeTextEdit
    header file  -> widgets.auto_resize_text_edit
"""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextOption
from PySide6.QtWidgets import QPlainTextEdit, QSizePolicy


class AutoResizeTextEdit(QPlainTextEdit):
    sendRequested = Signal()
    heightChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- configurable bounds (easy to tweak / expose to Designer
        # via dynamic properties if desired) -------------------------
        self.min_height = 52
        self.max_height = 220
        self.send_on_enter = True  # Enter sends, Shift+Enter = newline

        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setTabChangesFocus(True)
        self.setFrameShape(QPlainTextEdit.NoFrame)
        self.setPlaceholderText("Ask anything...")

        self._current_height = self.min_height
        self.setFixedHeight(self._current_height)

        self._height_anim = QPropertyAnimation(self, b"minimumHeight", self)
        self._height_anim.setDuration(140)
        self._height_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.document().documentLayout().documentSizeChanged.connect(
            self._recalculate_height
        )

    # ------------------------------------------------------------------
    # Height management
    # ------------------------------------------------------------------
    def _recalculate_height(self, *_):
        margins = self.contentsMargins()
        doc_height = self.document().size().height()
        frame = 2 * self.frameWidth()
        target = int(doc_height + margins.top() + margins.bottom() + frame + 10)
        target = max(self.min_height, min(target, self.max_height))

        if target == self._current_height:
            return

        needs_scroll = target >= self.max_height
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded if needs_scroll else Qt.ScrollBarAlwaysOff
        )

        self._current_height = target
        self._height_anim.stop()
        self._height_anim.setStartValue(self.height())
        self._height_anim.setEndValue(target)
        self._height_anim.start()
        self.setMaximumHeight(target)
        self.heightChanged.emit(target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Wrapping depends on width, so a width change can change how
        # many visual lines the *same* text occupies.
        self._recalculate_height()

    # ------------------------------------------------------------------
    # Enter-to-send / Shift+Enter-for-newline
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        is_return = event.key() in (Qt.Key_Return, Qt.Key_Enter)
        if is_return and self.send_on_enter and not (event.modifiers() & Qt.ShiftModifier):
            if self.toPlainText().strip():
                self.sendRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def clear_and_reset(self):
        self.clear()
        self._current_height = self.min_height
        self.setMaximumHeight(self.min_height)
        self.updateGeometry()
