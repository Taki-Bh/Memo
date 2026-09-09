"""
Memo — AI Assistant desktop UI
=================================

Entry point. Loads ui/main_window.ui (a QMainWindow with a QSplitter
implementing the 20/80 sidebar/chat split), embeds the Sidebar and
ChatView custom widgets into it, applies styles/theme.qss, and wires
up past conversation loading upon start categorized into Today, Yesterday,
Previous 7 Days, and Older.
"""
import sys
import queue
import threading
from pathlib import Path
import os
import json
import traceback
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout

from ui.widgets.chat_view import ChatView
from ui.widgets.preferences_dialog import PreferencesDialog
from ui.widgets.sidebar import Sidebar
from ui.widgets.ui_loader import CustomUiLoader
from ui.widgets import theme_manager

from core.interface_new import GUIInterface

ROOT_DIR = Path(__file__).resolve().parent
if (ROOT_DIR.parent / "memory").exists() and not (ROOT_DIR / "memory").exists():
    PROJECT_ROOT = ROOT_DIR.parent
else:
    PROJECT_ROOT = ROOT_DIR

UI_DIR = PROJECT_ROOT / "ui" / "ui"
STYLES_DIR = PROJECT_ROOT / "styles"
MEMORY_DIR = PROJECT_ROOT / "memory"

SIDEBAR_RATIO = 0.20
CHAT_RATIO = 0.80


class LLMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)
    stateUpdated = Signal(dict)
    def __init__(self):
        super().__init__()
        self.interface = None
        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._busy = threading.Event()
        
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def run_prompt(self, prompt: str):
        self._queue.put(prompt)

    def is_busy(self) -> bool:
        return self._busy.is_set() or not self._queue.empty()

    def stop(self):
        self._queue.put(None)

    def _loop(self):
        self.interface = GUIInterface()
        if self.interface:
            self.interface.assistant.agent_router.execution_loop.stateUpdated.connect(self.stateUpdated.emit)
        while True:
            prompt = self._queue.get()
            if prompt is None:
                break

            self._busy.set()
            try:
                if self.interface is None:
                    self.interface = GUIInterface()
                    
                response = self.interface.run(prompt)
                if prompt.find("/swap") > -1:
                    self.interface.assistant.agent_router.execution_loop.stateUpdated.disconnect(self.stateUpdated.emit)
                    self.interface.assistant.agent_router.execution_loop.stateUpdated.connect(self.stateUpdated.emit)
                    
                self.finished.emit(response)
            except Exception as e:
                self.error.emit(str(e) + traceback.format_exc())
            finally:
                self._busy.clear()


class MockAssistant:
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
        self._loaded_conversations_map = {}

        self.worker = LLMWorker()
        
        self._wire_signals()
        self._load_past_conversations()
        self._apply_split_ratio()

        self.window.closeEvent = self.closeEvent

    def _wire_signals(self):
        self.sidebar.conversationSelected.connect(self._on_conversation_selected)
        self.sidebar.newConversationRequested.connect(self._on_new_conversation)
        self.sidebar.utilityActivated.connect(self._on_utility_activated)

        self.chat_view.messageSent.connect(self._on_message_sent)
        self.chat_view.suggestionActivated.connect(self._on_suggestion_activated)

        self.window.rootSplitter.splitterMoved.connect(lambda *_: None)
        self.worker.finished.connect(self.on_llm_response)
        self.worker.error.connect(self.on_llm_error)
        self.worker.stateUpdated.connect(self._handle_state_update)

    def _handle_state_update(self, state: dict):
        print("State updated:", state)
        with open("state_log.net", "a") as f:
            f.write(json.dumps(state) + "\n")
        self.chat_view.add_ai_message(state.get("last_checkpoint", "No message in state"))
    def _load_past_conversations(self):
        conversations_list = []
        self._loaded_conversations_map = {}

        now = datetime.now()
        conversations_file = MEMORY_DIR / "conversations.json"

        try:
            with open(conversations_file, "rt") as f:
                conversations = json.load(f)
                data = conversations.get("entities", [])

                for i, entity in enumerate(data):
                    title = entity.get("name", "Untitled Conversation")
                    date_str = entity.get("date", now.isoformat())
                    convs = entity.get("messages", [])

                    try:
                        dt = datetime.fromisoformat(date_str)
                    except Exception:
                        dt = now

                    delta_days = (now.date() - dt.date()).days

                    if delta_days == 0:
                        group = "Today"
                    elif delta_days == 1:
                        group = "Yesterday"
                    elif delta_days <= 7:
                        group = "Previous 7 Days"
                    else:
                        group = "Older"

                    conv_id = i
                    self._loaded_conversations_map[conv_id] = convs

                    conversations_list.append({
                        "id": conv_id,
                        "title": title,
                        "group": group,
                        "icon": "💬"
                    })

        except Exception as e:
            print(f"Error loading conversation file: {e}")

        if not conversations_list:
            conversations_list = [
                {"id": "c1", "title": "Trip planning: Lisbon", "group": "Today", "icon": "🧳"},
                {"id": "c2", "title": "Refactor auth module", "group": "Today", "icon": "🛠️"},
                {"id": "c3", "title": "Weekly meal ideas", "group": "Yesterday", "icon": "🍲"},
                {"id": "c4", "title": "Explaining quantum tunneling", "group": "Previous 7 Days", "icon": "⚛️"},
                {"id": "c5", "title": "Resume feedback", "group": "Previous 7 Days", "icon": "📄"},
                {"id": "c6", "title": "First conversation", "group": "Older", "icon": "💬"},
            ]

        self.sidebar.set_conversations(conversations_list)

    def _apply_split_ratio(self):
        total = max(self.window.width(), 1000)
        sidebar_width = int(total * SIDEBAR_RATIO)
        chat_width = total - sidebar_width
        self.window.rootSplitter.setSizes([sidebar_width, chat_width])

    def _on_conversation_selected(self, conversation_id: str):
        self._active_conversation = conversation_id
        self.chat_view.clear_conversation()
        if conversation_id in self._loaded_conversations_map:
            convs = self._loaded_conversations_map[conversation_id]
            for msg in convs:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    self.chat_view.add_user_message(content)
                else:
                    self.chat_view.add_ai_message(content)

    def _on_new_conversation(self):
        self.chat_view.clear_conversation()
        self._active_conversation = None
        self.sidebar.select_conversation("")

    def _on_utility_activated(self, name: str):
        if name == "preferences":
            self._open_preferences()
            return
        print(f"[utility] {name} clicked")

    def _open_preferences(self):
        dialog = PreferencesDialog(self.window)
        dialog.themeChanged.connect(self._on_theme_changed)
        dialog.exec()

    def _on_theme_changed(self, key: str):
        # Handle theme change if needed globally or update components
        pass

    def _on_suggestion_activated(self, label: str):
        self.chat_view.composer.text_edit.setPlainText(label)
        self.chat_view.composer.text_edit.setFocus()

    def _on_message_sent(self, text: str):
        if self.worker.is_busy():
            return

        self.chat_view.add_user_message(text)
        self.chat_view.show_typing(True)
        self.worker.run_prompt(text)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

    def on_llm_response(self, response):
        self.chat_view.show_typing(False)
        self.chat_view.add_ai_message(response)

    def on_llm_error(self, error_message):
        self.chat_view.show_typing(False)
        self.chat_view.add_ai_message(f"Error: {error_message}")

    def show(self):
        self.window.resize(1280, 800)
        self.window.show()


def load_stylesheet(app: QApplication):
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