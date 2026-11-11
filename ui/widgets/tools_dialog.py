import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from ui.widgets.glass_button import GlassButton

class ToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolsDialog")
        self.setWindowTitle("Tools & Capabilities")
        self.setMinimumWidth(400)
        self.setMinimumHeight(320)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(16)

        title = QLabel("Manage Capabilities & Tools")
        title.setObjectName("preferencesTitle")
        outer.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("toolsListWidget")
        outer.addWidget(self.list_widget)

        self._load_tools()

        footer = QVBoxLayout()
        close_button = GlassButton("Close")
        close_button.setObjectName("preferencesCloseButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        outer.addLayout(footer)

    def _load_tools(self):
        tools_path = Path(__file__).resolve().parent.parent.parent / "tools" / "tools.json"
        if tools_path.exists():
            try:
                with open(tools_path, "r") as f:
                    tools = json.load(f)
                    for item in tools:
                        func = item.get("function", {})
                        name = func.get("name", "unknown")
                        desc = func.get("description", "")
                        w_item = QListWidgetItem(f"🧩  {name} — {desc}")
                        self.list_widget.addItem(w_item)
            except Exception as e:
                self.list_widget.addItem(f"(Error loading tools: {e})")
        if self.list_widget.count() == 0:
            self.list_widget.addItem("(No tools configured)")
