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

class FilesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FilesDialog")
        self.setWindowTitle("Files")
        self.setMinimumWidth(380)
        self.setMinimumHeight(300)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(16)

        title = QLabel("Attached Files")
        title.setObjectName("preferencesTitle")
        outer.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("filesListWidget")
        outer.addWidget(self.list_widget)

        self._load_files()

        footer = QVBoxLayout()
        close_button = GlassButton("Close")
        close_button.setObjectName("preferencesCloseButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        outer.addLayout(footer)

    def _load_files():
        pass

    def _load_files(self):
        files_dir = Path(__file__).resolve().parent.parent.parent / "files"
        if files_dir.exists():
            for item in sorted(files_dir.iterdir()):
                if item.is_file():
                    w_item = QListWidgetItem(f"📄  {item.name}")
                    self.list_widget.addItem(w_item)
        if self.list_widget.count() == 0:
            self.list_widget.addItem("(No files found)")
