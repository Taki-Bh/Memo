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
import queue
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout

from ui.widgets.chat_view import ChatView
from ui.widgets.preferences_dialog import PreferencesDialog
from ui.widgets.sidebar import Sidebar
from ui.widgets.ui_loader import CustomUiLoader
from ui.widgets import theme_manager

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
    """
    Runs every GUIInterface/Playwright call on ONE dedicated, persistent
    plain thread — never QThread, and never a fresh thread per call.

    Sync Playwright requires all of its calls to happen on the exact
    same OS thread for the entire lifetime of the browser (not just
    non-overlapping calls — the *same* thread, every time). So instead
    of spawning a thread per prompt (which breaks the moment that
    thread exits and a new one takes over), we start one background
    thread that loops forever, pulling prompts off a queue and running
    them one at a time. That thread — and the browser/GUIInterface
    living on it — stays alive for the whole app session.
    """
    finished = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.interface = None
        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._busy = threading.Event()
        
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def run_prompt(self, prompt: str):
        """Call this from the main thread — enqueues work for the single worker thread."""
        self._queue.put(prompt)

    def is_busy(self) -> bool:
        return self._busy.is_set() or not self._queue.empty()

    def stop(self):
        """Signal the worker loop to exit (call on app shutdown)."""
        self._queue.put(None)

    def _loop(self):
        self.interface = GUIInterface()
        # Runs entirely on this one dedicated thread for the whole
        # app's lifetime. GUIInterface (and the browser it opens) is
        # created here, on first use, and reused for every prompt.
        while True:
            prompt = self._queue.get()
            if prompt is None:  # sentinel → shut down
                break

            self._busy.set()
            try:
                if self.interface is None:
                    self.interface = GUIInterface()   # constructed once, on this thread
                response = self.interface.run(prompt)
                self.finished.emit(response)
            except Exception as e:
                self.error.emit(str(e))
            finally:
                self._busy.clear()


class MockAssistant:
    """Stand-in for a real model/API call — replace freely."""

    def reply_to(self, user_text: str, await_response=True) -> str:
        response = GUIInterface().run(user_text)
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

        self.worker = LLMWorker()
        self.worker.finished.connect(self.on_llm_response)
        self.worker.error.connect(self.on_llm_error)

        self._wire_signals()
        self._load_demo_data()
        self._apply_split_ratio()

        # Route the window's close event to our own teardown logic.
        self.window.closeEvent = self.closeEvent

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
        if self.worker.is_busy():
            # A prompt is already in flight — ignore/ or queue if you'd
            # rather; for now we just avoid overlapping browser calls.
            return

        self.chat_view.add_user_message(text)
        self.chat_view.show_typing(True)
        self.worker.run_prompt(text)   # spawns a plain background thread

    def closeEvent(self, event):
        # Ask the single persistent worker thread to exit its loop.
        # It's a daemon thread either way, so this is mostly for a
        # clean shutdown rather than a hard requirement.
        self.worker.stop()
        event.accept()

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

    memo = MemoApp()
    memo.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()