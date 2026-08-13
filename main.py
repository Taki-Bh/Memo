# main.py

from core.context import LLMContext
from providers.chatgpt import ChatGPTProvider
from core.interface import chat
from core.streaming import stream_output
from ui.main import mainUI
def main():
    chat()


import sys

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QGraphicsDropShadowEffect,QWidget



def apply_shadow_to_widget(widget):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(100)
    shadow.setOffset(0, 10)
    shadow.setColor(QColor(0, 0, 0, 70))
    widget.setGraphicsEffect(shadow)
class MainWindow(QMainWindow):
   def __init__(self):
        super().__init__()

        uic.loadUi("ai_assistant_light.ui", self)

        # Find chatInput from Qt Designer
        """chat_input = self.findChild(QLineEdit, "chatInput")
        chat_panel = self.findChild(QWidget, "chatPanel")
        # Create shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(100)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 70))

        # Apply shadow
        apply_shadow_to_widget(chat_panel)
        apply_shadow_to_widget(chat_input)"""

#xd

def main2():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
if __name__ == "__main__":
    mainUI()