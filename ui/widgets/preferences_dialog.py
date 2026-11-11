"""
PreferencesDialog
==================

A small, self-contained dialog for app preferences. For now it only
holds one section — "Appearance" — with a colour-theme picker (Dark,
Light, Light Blue). Selecting an option applies it to the whole app
immediately and remembers it for next launch via `theme_manager`.

Everything here is client-side: no network call, no `core.interface`
import, nothing that depends on the assistant backend being present
or reachable. It's a good template for any other purely-local
preference you add later (font size, message density, keyboard
shortcuts, etc.) — just add another section the same way.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import theme_manager
from ui.widgets.glass_button import GlassButton


class _Swatch(QWidget):
    """Tiny 3-dot colour preview for a theme option."""

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for color in colors:
            dot = QLabel()
            dot.setObjectName("themeSwatch")
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(f"background-color: {color.name()};")
            layout.addWidget(dot)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


class _ThemeOptionButton(GlassButton):
    def __init__(self, theme_key: str, parent=None):
        super().__init__(parent)
        self.theme_key = theme_key
        self.setObjectName("themeOption")
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        layout.addWidget(_Swatch(theme_manager.theme_swatch(theme_key)))

        label = QLabel(theme_manager.theme_label(theme_key))
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(label)
        layout.addStretch(1)

        self._check = QLabel("✓")
        self._check.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._check)
        self.set_active(False)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self._check.setVisible(active)
        self.style().unpolish(self)
        self.style().polish(self)


class PreferencesDialog(QDialog):
    themeChanged = Signal(str)  # emits the new theme key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreferencesDialog")
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(16)

        title = QLabel("Preferences")
        title.setObjectName("preferencesTitle")
        outer.addWidget(title)

        section_label = QLabel("APPEARANCE — COLOUR THEME")
        section_label.setObjectName("preferencesSectionLabel")
        outer.addWidget(section_label)

        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)

        self._option_buttons = {}
        current = theme_manager.get_saved_theme()
        for key in theme_manager.available_themes():
            button = _ThemeOptionButton(key)
            button.clicked.connect(lambda _, k=key: self._select_theme(k))
            self._option_buttons[key] = button
            options_layout.addWidget(button)
        outer.addLayout(options_layout)

        outer.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        close_button = GlassButton("Close")
        close_button.setObjectName("preferencesCloseButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        outer.addLayout(footer)

        self._highlight(current)

    def _select_theme(self, key: str):
        theme_manager.apply_theme(QApplication.instance(), key)
        self._highlight(key)
        self.themeChanged.emit(key)

    def _highlight(self, active_key: str):
        for key, button in self._option_buttons.items():
            button.set_active(key == active_key)
