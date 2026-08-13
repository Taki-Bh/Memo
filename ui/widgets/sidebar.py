"""
Sidebar
=======

Loads ui/sidebar.ui at runtime (so the layout/spacing/proportions stay
Qt-Designer-editable) and layers on the conversation-list behaviour:
grouping by recency, search filtering, selection state, and the
rename/delete/archive context-menu actions.
"""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from widgets.conversation_item import ConversationItem
from widgets.glass_button import GlassButton
from widgets.ui_loader import CustomUiLoader

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

GROUP_ORDER = ["Today", "Yesterday", "Previous 7 Days", "Older"]


class Sidebar(QWidget):
    conversationSelected = Signal(str)
    newConversationRequested = Signal()
    conversationRenamed = Signal(str)
    conversationDeleted = Signal(str)
    conversationArchived = Signal(str)
    utilityActivated = Signal(str)  # "settings" | "theme" | "attachments" | "tools" | "help"

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = CustomUiLoader({"GlassButton": GlassButton})
        self.ui = loader.load_ui(UI_DIR / "sidebar.ui")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self._items = {}          # conversation_id -> ConversationItem
        self._group_labels = {}   # group name -> QLabel header
        self._conversations = []  # ordered list of (id, title, group, icon)

        self.ui.newConversationButton.clicked.connect(self.newConversationRequested.emit)
        self.ui.conversationSearch.textChanged.connect(self._filter_conversations)

        self.ui.settingsButton.clicked.connect(lambda: self.utilityActivated.emit("settings"))
        self.ui.themeButton.clicked.connect(lambda: self.utilityActivated.emit("theme"))
        self.ui.attachmentsButton.clicked.connect(lambda: self.utilityActivated.emit("attachments"))
        self.ui.toolsUtilityButton.clicked.connect(lambda: self.utilityActivated.emit("tools"))
        self.ui.helpButton.clicked.connect(lambda: self.utilityActivated.emit("help"))

        self._list_layout: QVBoxLayout = self.ui.conversationListLayout
        # Keep the trailing stretch/spacer as the last item at all times.
        self._tail_spacer = self._list_layout.takeAt(self._list_layout.count() - 1)

    # ------------------------------------------------------------------
    # Populating conversations
    # ------------------------------------------------------------------
    def set_conversations(self, conversations):
        """
        conversations: list of dicts, e.g.
            {"id": "c1", "title": "Trip planning", "group": "Today", "icon": "💬"}
        Groups are rendered in GROUP_ORDER; unknown groups are appended after.
        """
        self._conversations = conversations
        self._rebuild()

    def select_conversation(self, conversation_id: str):
        for cid, item in self._items.items():
            item.set_selected(cid == conversation_id)

    def _rebuild(self):
        while self._list_layout.count():
            child = self._list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._items.clear()
        self._group_labels.clear()

        groups = {}
        for conv in self._conversations:
            groups.setdefault(conv.get("group", "Older"), []).append(conv)

        ordered_groups = [g for g in GROUP_ORDER if g in groups]
        ordered_groups += [g for g in groups if g not in GROUP_ORDER]

        for group in ordered_groups:
            header = QLabel(group.upper())
            header.setObjectName("conversationGroupLabel")
            self._group_labels[group] = header
            self._list_layout.addWidget(header)

            for conv in groups[group]:
                item = ConversationItem(conv["id"], conv["title"], conv.get("icon", "💬"))
                item.clicked.connect(self._on_item_clicked)
                item.renameRequested.connect(self.conversationRenamed.emit)
                item.deleteRequested.connect(self.conversationDeleted.emit)
                item.archiveRequested.connect(self.conversationArchived.emit)
                self._items[conv["id"]] = item
                self._list_layout.addWidget(item)

        self._list_layout.addItem(self._tail_spacer)

    def _on_item_clicked(self, conversation_id: str):
        self.select_conversation(conversation_id)
        self.conversationSelected.emit(conversation_id)

    def _filter_conversations(self, query: str):
        query = query.strip().lower()
        for conv in self._conversations:
            item = self._items.get(conv["id"])
            if not item:
                continue
            item.setVisible(query in conv["title"].lower() or not query)

        for group, header in self._group_labels.items():
            visible_items = [
                self._items[c["id"]]
                for c in self._conversations
                if c.get("group") == group and self._items[c["id"]].isVisible()
            ]
            header.setVisible(bool(visible_items))
