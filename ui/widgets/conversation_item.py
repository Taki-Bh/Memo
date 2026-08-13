"""
ConversationItem
=================

A single row in the sidebar's conversation list. Built programmatically
(it's simple enough that a dedicated .ui file would add more overhead
than value), but every visual property is QSS-driven via objectName /
dynamic "selected" property, so it fully follows styles/theme.qss.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QWidget,
)


class ConversationItem(QWidget):
    clicked = Signal(str)          # emits conversation id
    renameRequested = Signal(str)
    deleteRequested = Signal(str)
    archiveRequested = Signal(str)

    def __init__(self, conversation_id: str, title: str, icon: str = "💬", parent=None):
        super().__init__(parent)
        self.conversation_id = conversation_id
        self._selected = False

        self.setObjectName("conversationItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("conversationIcon")
        self.icon_label.setFixedWidth(20)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("conversationTitle")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, 1)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.conversation_id)
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        archive_action = menu.addAction("Archive")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == rename_action:
            self.renameRequested.emit(self.conversation_id)
        elif chosen == archive_action:
            self.archiveRequested.emit(self.conversation_id)
        elif chosen == delete_action:
            self.deleteRequested.emit(self.conversation_id)
