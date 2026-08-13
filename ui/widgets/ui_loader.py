"""
CustomUiLoader
==============

PySide6's QUiLoader loads .ui files at runtime (no compile step needed),
which is what lets this project stay 100% Qt-Designer-editable. The one
thing it needs help with is *promoted widgets* -- e.g. a QPlainTextEdit
in Designer that's promoted to our AutoResizeTextEdit class. This loader
maps the class name declared in the .ui file's <customwidgets> section
to the actual Python class, so promoted widgets come back as real,
fully-functional instances instead of generic base-class placeholders.

Usage:
    loader = CustomUiLoader({
        "AutoResizeTextEdit": AutoResizeTextEdit,
        "GlassButton": GlassButton,
    })
    widget = loader.load(ui_file_path)
"""
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader


class CustomUiLoader(QUiLoader):
    def __init__(self, custom_widgets: dict, parent=None):
        super().__init__(parent)
        self._custom_widgets = custom_widgets or {}

    def createWidget(self, class_name, parent=None, name=""):
        if class_name in self._custom_widgets:
            widget_cls = self._custom_widgets[class_name]
            widget = widget_cls(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(class_name, parent, name)

    def load_ui(self, ui_path, parent=None):
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise IOError(f"Could not open UI file: {ui_path}")
        try:
            widget = self.load(ui_file, parent)
        finally:
            ui_file.close()
        if widget is None:
            raise RuntimeError(f"Failed to load UI file: {ui_path}")
        return widget
