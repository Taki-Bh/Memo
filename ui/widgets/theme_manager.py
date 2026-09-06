"""
theme_manager
=============

Small, fully self-contained helper for switching the app's colour theme.

This is intentionally backend-independent: it never touches
`core.interface` or makes any network/model call. It only:

  1. Knows which .qss files exist and what to call them in the UI.
  2. Applies a theme to the running QApplication.
  3. Remembers the user's choice locally between runs, via Qt's
     QSettings (which just reads/writes a small config file / registry
     key on disk — no server, no account, no internet required).

Swap in a different persistence mechanism later if you want (e.g. a
user-profile file synced with the backend) — everything else in the
UI only talks to this module, never to QSettings directly.
"""
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"

ORG_NAME = "Memo"
APP_NAME = "MemoAssistant"
SETTINGS_KEY = "appearance/theme"

DEFAULT_THEME = "dark"

# key -> (display label, qss filename, swatch colors for the preferences UI)
THEMES = {
    "dark": {
        "label": "Dark",
        "file": "theme_dark.qss",
        "swatch": [QColor("#0B0F17"), QColor("#111827"), QColor("#5CC8FF")],
    },
    "light": {
        "label": "Light (White)",
        "file": "theme_light.qss",
        "swatch": [QColor("#FFFFFF"), QColor("#F4F6F9"), QColor("#2B8CE6")],
    },
    "light_blue": {
        "label": "Light Blue",
        "file": "theme_light_blue.qss",
        "swatch": [QColor("#EAF3FC"), QColor("#F4F9FE"), QColor("#2F87D6")],
    },
    "midnight_purple": {
        "label": "Midnight Purple",
        "file": "theme_midnight_purple.qss",
        "swatch": [QColor("#120B1E"), QColor("#1E1430"), QColor("#B388FF")],
    },
    "forest": {
        "label": "Forest",
        "file": "theme_forest.qss",
        "swatch": [QColor("#0E1710"), QColor("#16241A"), QColor("#5FD68A")],
    },
    "solarized_dark": {
        "label": "Solarized Dark",
        "file": "theme_solarized_dark.qss",
        "swatch": [QColor("#002B36"), QColor("#073642"), QColor("#B58900")],
    },
    "solarized_light": {
        "label": "Solarized Light",
        "file": "theme_solarized_light.qss",
        "swatch": [QColor("#FDF6E3"), QColor("#EEE8D5"), QColor("#268BD2")],
    },
    "high_contrast": {
        "label": "High Contrast",
        "file": "theme_high_contrast.qss",
        "swatch": [QColor("#000000"), QColor("#1A1A1A"), QColor("#FFD500")],
    },
    "rose_gold": {
        "label": "Rose Gold",
        "file": "theme_rose_gold.qss",
        "swatch": [QColor("#2A1B1E"), QColor("#3A2529"), QColor("#F0A9A0")],
    },
    "amber_terminal": {
        "label": "Amber Terminal",
        "file": "theme_amber_terminal.qss",
        "swatch": [QColor("#0C0A00"), QColor("#1A1400"), QColor("#FFB000")],
    },
    "thug_barber": {
        "label": "Thug Life & Erotic Barber Hood",
        "file": "theme_thug_barber.qss",
        "swatch": [QColor("#120A0F"), QColor("#21121C"), QColor("#FF1493")],
    },
}


def available_themes() -> list[str]:
    """Ordered list of valid theme keys."""
    return list(THEMES.keys())


def theme_label(key: str) -> str:
    return THEMES.get(key, THEMES[DEFAULT_THEME])["label"]


def theme_swatch(key: str):
    return THEMES.get(key, THEMES[DEFAULT_THEME])["swatch"]


def _theme_path(key: str) -> Path:
    filename = THEMES.get(key, THEMES[DEFAULT_THEME])["file"]
    return STYLES_DIR / filename


def load_theme_qss(key: str) -> str:
    path = _theme_path(key)
    if not path.exists():
        path = _theme_path(DEFAULT_THEME)
    return path.read_text(encoding="utf-8")


def get_saved_theme() -> str:
    """Read the last-chosen theme from local settings (no backend call)."""
    settings = QSettings(ORG_NAME, APP_NAME)
    key = settings.value(SETTINGS_KEY, DEFAULT_THEME)
    return key if key in THEMES else DEFAULT_THEME


def save_theme(key: str) -> None:
    """Persist the chosen theme locally so it's remembered next launch."""
    if key not in THEMES:
        return
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(SETTINGS_KEY, key)


def apply_theme(app: QApplication, key: str, persist: bool = True) -> None:
    """Apply a theme to the running app immediately, no restart needed."""
    app.setStyleSheet(load_theme_qss(key))
    if persist:
        save_theme(key)
