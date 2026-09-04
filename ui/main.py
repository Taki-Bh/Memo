"""
Memo — AI Assistant desktop UI
=================================

Entry point. Loads ui/main_window.ui (a QMainWindow with a QSplitter
implementing the 20/80 sidebar/chat split), embeds the Sidebar and
ChatView custom widgets into it, applies styles/theme.qss, and wires
up a small in-memory demo "backend" (fake conversations + a canned,
slightly-delayed AI reply) so the app is genuinely runnable out of the
box. Swap `MockAssistant` for a real API call whenever you're ready —
everything else (UI, composer, message rendering) is already decoupled
from it via signals.
"""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer,QObject
from PySide6.QtWidgets import QApplication, QVBoxLayout

from ui.widgets.chat_view import ChatView
from ui.widgets.preferences_dialog import PreferencesDialog
from ui.widgets.sidebar import Sidebar
from ui.widgets.ui_loader import CustomUiLoader
from ui.widgets import theme_manager

import asyncio
from PySide6.QtCore import QThread, Signal, QObject

from core.interface_new import GUIInterface
ROOT_DIR = Path(__file__).resolve().parent
UI_DIR = ROOT_DIR / "ui"
STYLES_DIR = ROOT_DIR / "styles"

# ----------------------------------------------------------------------
# Sidebar split ratio — change these two numbers to change the 20/80
# proportion. They're passed to QSplitter.setSizes() on first show and
# whenever the window is resized, so Designer's own splitter geometry
# is only a starting point.
# ----------------------------------------------------------------------
SIDEBAR_RATIO = 0.20
CHAT_RATIO = 0.80


DEMO_CONVERSATIONS = [
    {"id": "c1", "title": "Trip planning: Lisbon", "group": "Today", "icon": "🧳"},
    {"id": "c2", "title": "Refactor auth module", "group": "Today", "icon": "🛠️"},
    {"id": "c3", "title": "Weekly meal ideas", "group": "Yesterday", "icon": "🍲"},
    {"id": "c4", "title": "Explaining quantum tunneling", "group": "Previous 7 Days", "icon": "⚛️"},
    {"id": "c5", "title": "Resume feedback", "group": "Previous 7 Days", "icon": "📄"},
    {"id": "c6", "title": "First conversation", "group": "Older", "icon": "💬"},
]


class LLMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)
    requestReady = Signal(str)   # main thread emits this to hand off a prompt

    def __init__(self):
        super().__init__()
        self.interface = None
        self.requestReady.connect(self._run)  # queued automatically once moved to another thread

    def _run(self, prompt: str):
        try:
            if self.interface is None:
                self.interface = GUIInterface()   # constructed on THIS thread, once
            response = self.interface.run(prompt)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))
class MockAssistant:
    """Stand-in for a real model/API call — replace freely."""
    
    def reply_to(self, user_text: str,await_response=True) -> str:
        #response=get_response(user_text,await_response=await_response)
        response=GUIInterface().run(user_text)
        """return (
            f"Here's a thought on **\"{user_text[:60]}\"**:\n\n"
            "This is a demo reply rendered through Qt's built-in Markdown "
            "support, so it can show:\n\n"
            "- bullet points\n"
            "- `inline code`\n"
            "- and fenced code blocks\n\n"
            "```python\n"
            "def greet(name):\n"
            "    return f\"Hello, {name}!\"\n"
            "```\n\n"
            "Wire `MockAssistant.reply_to` up to a real API call whenever you're ready."
        )"""
        return response


class MemoApp(QObject):
    def __init__(self):
        loader = CustomUiLoader({})
        self.window = loader.load_ui(UI_DIR / "main_window.ui")

        self.sidebar = Sidebar()
        sidebar_layout = QVBoxLayout(self.window.sidebarContainer)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.sidebar)

        self.chat_view = ChatView()
        chat_layout = QVBoxLayout(self.window.chatViewContainer)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.addWidget(self.chat_view)

        self.assistant = MockAssistant()
        self._active_conversation = None
        self.thread = QThread()
        self.worker = LLMWorker()
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_llm_response)
        self.worker.error.connect(self.on_llm_error)
        self.thread.start()  
        self._wire_signals()
        self._load_demo_data()
        self._apply_split_ratio()

    # ------------------------------------------------------------------
    def _wire_signals(self):
        self.sidebar.conversationSelected.connect(self._on_conversation_selected)
        self.sidebar.newConversationRequested.connect(self._on_new_conversation)
        self.sidebar.utilityActivated.connect(self._on_utility_activated)

        self.chat_view.messageSent.connect(self._on_message_sent)
        self.chat_view.suggestionActivated.connect(self._on_suggestion_activated)

        self.window.rootSplitter.splitterMoved.connect(lambda *_: None)

    def _load_demo_data(self):
        self.sidebar.set_conversations(DEMO_CONVERSATIONS)

    def _apply_split_ratio(self):
        total = max(self.window.width(), 1000)
        sidebar_width = int(total * SIDEBAR_RATIO)
        chat_width = total - sidebar_width
        self.window.rootSplitter.setSizes([sidebar_width, chat_width])

    # ------------------------------------------------------------------
    # Sidebar interactions
    # ------------------------------------------------------------------
    def _on_conversation_selected(self, conversation_id: str):
        self._active_conversation = conversation_id
        self.chat_view.clear_conversation()
        # In a real app: load & render this conversation's message history here.

    def _on_new_conversation(self):
        self.chat_view.clear_conversation()
        self._active_conversation = None
        self.sidebar.select_conversation("")

    def _on_utility_activated(self, name: str):
        if name == "preferences":
            self._open_preferences()
            return
        # Hook up real Settings/Files/Tools/Help panels here.
        print(f"[utility] {name} clicked")

    def _open_preferences(self):
        # Purely client-side: no backend/model call involved anywhere
        # in this dialog, it only reads/writes local app settings.
        dialog = PreferencesDialog(self.window)
        dialog.exec()

    # ------------------------------------------------------------------
    # Chat interactions
    # ------------------------------------------------------------------
    def _on_suggestion_activated(self, label: str):

        self.chat_view.composer.text_edit.setPlainText(label)
        self.chat_view.composer.text_edit.setFocus()

    def _on_message_sent(self, text: str):

        self.chat_view.add_user_message(text)
        self.chat_view.show_typing(True)
        self.worker.requestReady.emit(text)   # queued connection delivers this on the worker thread
    def closeEvent(self, event):  # or wherever you tear the app down
        self.thread.quit()
        self.thread.wait()

    def on_llm_response(self, response):

        self.chat_view.show_typing(False)
        self.chat_view.add_ai_message(response)
        
    def on_llm_error(self, error_message):

        self.chat_view.show_typing(False)
        self.chat_view.add_ai_message(f"Error: {error_message}")
        
    def _deliver_reply(self, user_text: str):
        self.chat_view.show_typing(False)
        reply = self.assistant.reply_to(user_text)
        self.chat_view.add_ai_message(reply)

    def show(self):
        self.window.resize(1280, 800)
        self.window.show()


def load_stylesheet(app: QApplication):
    # Loads whichever theme the user picked last time (local settings
    # only — see widgets/theme_manager.py), defaulting to Dark.
    saved_theme = theme_manager.get_saved_theme()
    app.setStyleSheet(theme_manager.load_theme_qss(saved_theme))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Memo")
    load_stylesheet(app)

    memo= MemoApp()
    memo.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
