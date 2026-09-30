import sys
import queue
import threading
from pathlib import Path
import os
import json
import traceback
from datetime import datetime

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout, QInputDialog

from ui.widgets.chat_view import ChatView
from ui.widgets.preferences_dialog import PreferencesDialog
from ui.widgets.files_dialog import FilesDialog
from ui.widgets.tools_dialog import ToolsDialog
from ui.widgets.sidebar import Sidebar
from ui.widgets.ui_loader import CustomUiLoader
from ui.widgets import theme_manager
from core.communication import ui_to_backend, backend_to_ui
from core.interface_new import Assistant, GUIInterface
from utilities.utilities import (
    get_conversations,
    update_conversation_name,
    delete_conversation,
    archive_conversation,
)


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
    userInputRequested = Signal(dict)

    agentSwapped = Signal(str)
    providerSwapped = Signal(str)
    requestedSuper = Signal(str)

    def __init__(self):
        super().__init__()

        self.interface = None
        self.execution_loop = None

        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._busy = threading.Event()

        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
        )
        self._thread.start()

    def run_prompt(self, prompt: str):
        self._queue.put(prompt)

    def is_busy(self) -> bool:
        return self._busy.is_set() or not self._queue.empty()

    # ---------------------------------------------------------
    # PROMPT CANCELLATION
    # ---------------------------------------------------------

    def stop_prompt(self):
        """
        Request cancellation of the currently running prompt.

        This does NOT terminate the worker thread.
        It tells the active SkillExecutionLoop to stop
        cooperatively.
        """
        if self.execution_loop is not None:
            print("[LLMWorker] Requesting prompt cancellation...")
            self.execution_loop.stop()

    # ---------------------------------------------------------
    # WORKER SHUTDOWN
    # ---------------------------------------------------------

    def stop(self):
        """
        Shut down the worker thread.

        This is different from stop_prompt():
        stop_prompt() cancels the current prompt,
        while stop() terminates the worker loop.
        """
        self._queue.put(None)

    def wait(self, timeout: float | None = None):
        if self._thread.is_alive():
            self._thread.join(timeout)

    # ---------------------------------------------------------
    # Signal forwarding
    # ---------------------------------------------------------

    def _forward_state_updated(self, state):
        self.stateUpdated.emit(state)

    def _forward_user_input_requested(self, state):
        self.userInputRequested.emit(state)

    def _forward_requested_super(self, cmd: str):
        self.requestedSuper.emit(cmd)

    def _forward_provider_swapped(self, provider):
        print(provider)
        self.providerSwapped.emit(provider)

    # ---------------------------------------------------------
    # Execution loop signal management
    # ---------------------------------------------------------

    def _connect_execution_loop(self, execution_loop):
        if execution_loop is None:
            return

        self.execution_loop = execution_loop

        self.execution_loop.stateUpdated.connect(
            self._forward_state_updated
        )

        self.execution_loop.userInputRequested.connect(
            self._forward_user_input_requested
        )

        self.execution_loop.llmProviderChanged.connect(
            self._forward_provider_swapped
        )

        self.execution_loop.requestedSuper.connect(
            self._forward_requested_super
        )

    def _disconnect_execution_loop(self):
        if self.execution_loop is None:
            return

        try:
            self.execution_loop.stateUpdated.disconnect(
                self._forward_state_updated
            )
        except (TypeError, RuntimeError):
            pass

        try:
            self.execution_loop.userInputRequested.disconnect(
                self._forward_user_input_requested
            )
        except (TypeError, RuntimeError):
            pass

        try:
            self.execution_loop.llmProviderChanged.disconnect(
                self._forward_provider_swapped
            )
        except (TypeError, RuntimeError):
            pass

        try:
            self.execution_loop.requestedSuper.disconnect(
                self._forward_requested_super
            )
        except (TypeError, RuntimeError):
            pass

        self.execution_loop = None

    def _ensure_interface(self):
        """
        Create (or recreate) the backend interface
        and wire its signals.
        """
        self.interface = GUIInterface()

        execution_loop = (
            self.interface
            .assistant
            .agent_router
            .execution_loop
        )

        self._connect_execution_loop(execution_loop)

    # ---------------------------------------------------------
    # Worker loop
    # ---------------------------------------------------------

    def _loop(self):
        self._ensure_interface()

        while True:
            prompt = self._queue.get()

            if prompt is None:
                break

            self._busy.set()

            try:
                if self.interface is None:
                    self._ensure_interface()

                response = self.interface.run(prompt)

                self.finished.emit(response)

            except Exception as e:
                self.error.emit(
                    str(e) + "\n" + traceback.format_exc()
                )

                self._disconnect_execution_loop()
                self.interface = None

            finally:
                self._busy.clear()

        self._disconnect_execution_loop()


class MockAssistant:
    """Compatibility wrapper backed by the real Assistant implementation."""

    def init(self):
        self.assistant = Assistant()

    def reply_to(self, user_text: str, await_response=True) -> str:
        return self.assistant.send(
            user_text,
            await_response=await_response,
        )


class MemoApp(QObject):
    def __init__(self):
        super().__init__()

        self.is_requested_input = False

        loader = CustomUiLoader({})
        self.window = loader.load_ui(
            UI_DIR / "main_window.ui"
        )

        self.sidebar = Sidebar()

        sidebar_layout = QVBoxLayout(
            self.window.sidebarContainer
        )
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.sidebar)

        self.chat_view = ChatView()

        chat_layout = QVBoxLayout(
            self.window.chatViewContainer
        )
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
        self.sidebar.conversationSelected.connect(
            self._on_conversation_selected
        )

        self.sidebar.newConversationRequested.connect(
            self._on_new_conversation
        )

        self.sidebar.utilityActivated.connect(
            self._on_utility_activated
        )

        self.sidebar.conversationRenamed.connect(
            self._on_conversation_renamed
        )

        self.sidebar.conversationDeleted.connect(
            self._on_conversation_deleted
        )

        self.sidebar.conversationArchived.connect(
            self._on_conversation_archived
        )

        self.chat_view.messageSent.connect(
            self._on_message_sent
        )

        # -----------------------------------------------------
        # STOP BUTTON
        # -----------------------------------------------------

        self.chat_view.stopRequested.connect(
            self._on_stop_requested
        )

        self.chat_view.suggestionActivated.connect(
            self._on_suggestion_activated
        )

        self.window.rootSplitter.splitterMoved.connect(
            lambda *_: None
        )

        self.worker.finished.connect(
            self.on_llm_response
        )

        self.worker.error.connect(
            self.on_llm_error
        )

        self.worker.stateUpdated.connect(
            self._handle_state_update
        )

        self.worker.requestedSuper.connect(
            self._handle_super_requested
        )

        self.worker.userInputRequested.connect(
            self._handle_input_requested
        )

        self.worker.providerSwapped.connect(
            self._handle_provider_swapped
        )

    # ---------------------------------------------------------
    # STOP CURRENT PROMPT
    # ---------------------------------------------------------

    def _on_stop_requested(self):
        """
        Cancel the currently running prompt without
        terminating the worker thread.
        """
        if not self.worker.is_busy():
            return

        print("[MemoApp] Stop requested.")

        self.worker.stop_prompt()

        self.chat_view.show_typing(False)

    # ---------------------------------------------------------
    # CONVERSATIONS
    # ---------------------------------------------------------

    def _on_conversation_renamed(self, conversation_id: str):
        new_title, ok = QInputDialog.getText(
            self.window,
            "Rename Conversation",
            "Enter new title:",
        )

        if ok and new_title.strip():
            title = new_title.strip()

            success = update_conversation_name(
                conversation_id,
                title,
            )

            if success:
                self.sidebar.rename_conversation(
                    conversation_id,
                    title,
                )

    # ---------------------------------------------------------
    # SUPERUSER CONFIRMATION
    # ---------------------------------------------------------

    def _handle_super_requested(self, cmd: str):
        """
        Receive the command directly from the Qt signal.

        Do NOT call backend_to_ui.get() here because
        the command is already supplied as `cmd`.
        """
        cmd = str(cmd)

        print(
            f"[MemoApp] Superuser command requested: {cmd}"
        )

        self.chat_view.add_confirmation_message(
            f"Approve ?: {cmd}"
        )

    # ---------------------------------------------------------
    # PROVIDER SWAP
    # ---------------------------------------------------------

    def _handle_provider_swapped(self, provider):
        print("Trying swap")

        if self.worker.interface is None:
            print("Swap failed: interface is None")
            return

        new_execution_loop = (
            self.worker
            .interface
            .assistant
            .agent_router
            .execution_loop
        )

        self.worker._disconnect_execution_loop()

        self.worker._connect_execution_loop(
            new_execution_loop
        )

        print("Successful swap")

    # ---------------------------------------------------------
    # CONVERSATION MANAGEMENT
    # ---------------------------------------------------------

    def _on_conversation_deleted(self, conversation_id: str):
        success = delete_conversation(conversation_id)

        if success:
            self.sidebar.remove_conversation(
                conversation_id
            )

            if self._active_conversation == conversation_id:
                self.chat_view.clear_conversation()
                self._active_conversation = None

            if conversation_id in self._loaded_conversations_map:
                del self._loaded_conversations_map[
                    conversation_id
                ]

    def _on_conversation_archived(self, conversation_id: str):
        success = archive_conversation(
            conversation_id
        )

        if success:
            self.sidebar.remove_conversation(
                conversation_id
            )

            if self._active_conversation == conversation_id:
                self.chat_view.clear_conversation()
                self._active_conversation = None

            if conversation_id in self._loaded_conversations_map:
                del self._loaded_conversations_map[
                    conversation_id
                ]

    # ---------------------------------------------------------
    # STATE
    # ---------------------------------------------------------

    def _handle_state_update(self, state: dict):
        if not isinstance(state, dict):
            state = {
                "last_checkpoint": str(state)
            }

        print("State updated:", state)

        with open(
            PROJECT_ROOT / "state_log.net",
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                json.dumps(
                    state,
                    ensure_ascii=False,
                )
                + "\n"
            )

        self.chat_view.typing_indicator.change_typing_message(
            state.get(
                "last_checkpoint",
                "No message in state",
            )
        )

    # ---------------------------------------------------------
    # USER INPUT REQUEST
    # ---------------------------------------------------------

    def _handle_input_requested(self, state: dict):
        print(
            f"Received user input request: {state}"
        )

        self.is_requested_input = True

        self.chat_view.show_typing(False)

        self.chat_view.add_ai_message(
            state.get(
                "last_question_to_user",
                "Failed to extract request.",
            )
        )

    # ---------------------------------------------------------
    # CONVERSATIONS
    # ---------------------------------------------------------

    def _load_past_conversations(self):
        self._loaded_conversations_map = {}

        (
            conversations_list,
            self._loaded_conversations_map,
        ) = get_conversations()

        if not conversations_list:
            conversations_list = [
                {
                    "id": "c1",
                    "title": "Trip planning: Lisbon",
                    "group": "Today",
                    "icon": "🧳",
                },
                {
                    "id": "c2",
                    "title": "Refactor auth module",
                    "group": "Today",
                    "icon": "🛠️",
                },
                {
                    "id": "c3",
                    "title": "Weekly meal ideas",
                    "group": "Yesterday",
                    "icon": "🍲",
                },
                {
                    "id": "c4",
                    "title": "Explaining quantum tunneling",
                    "group": "Previous 7 Days",
                    "icon": "⚛️",
                },
                {
                    "id": "c5",
                    "title": "Resume feedback",
                    "group": "Previous 7 Days",
                    "icon": "📄",
                },
                {
                    "id": "c6",
                    "title": "First conversation",
                    "group": "Older",
                    "icon": "💬",
                },
            ]

            for c in conversations_list:
                self._loaded_conversations_map[
                    c["id"]
                ] = []

        self.sidebar.set_conversations(
            conversations_list
        )

    def _apply_split_ratio(self):
        total = max(
            self.window.width(),
            1000,
        )

        sidebar_width = int(
            total * SIDEBAR_RATIO
        )

        chat_width = (
            total - sidebar_width
        )

        self.window.rootSplitter.setSizes(
            [
                sidebar_width,
                chat_width,
            ]
        )

    def _on_conversation_selected(
        self,
        conversation_id: str,
    ):
        self._active_conversation = (
            conversation_id
        )

        self.chat_view.clear_conversation()

        if conversation_id in self._loaded_conversations_map:
            convs = self._loaded_conversations_map[
                conversation_id
            ]

            for msg in convs:
                role = msg.get("role")
                content = msg.get(
                    "content",
                    "",
                )

                if role == "user":
                    self.chat_view.add_user_message(
                        content,
                        animate=False,
                    )
                else:
                    self.chat_view.add_ai_message(
                        content,
                        animate=False,
                    )

    def _on_new_conversation(self):
        self.chat_view.clear_conversation()

        self._active_conversation = None

        self.sidebar.select_conversation("")

    # ---------------------------------------------------------
    # UTILITIES
    # ---------------------------------------------------------

    def _on_utility_activated(self, name: str):
        if name == "preferences":
            self._open_preferences()
            return

        if name == "attachments" or name == "files":
            self._open_files()
            return

        if name == "tools":
            self._open_tools()
            return

        print(
            f"[utility] {name} clicked"
        )

    def _open_preferences(self):
        dialog = PreferencesDialog(
            self.window
        )

        dialog.themeChanged.connect(
            self._on_theme_changed
        )

        dialog.exec()

    def _open_files(self):
        dialog = FilesDialog(
            self.window
        )

        dialog.exec()

    def _open_tools(self):
        dialog = ToolsDialog(
            self.window
        )

        dialog.exec()

    def _on_theme_changed(self, key: str):
        pass

    # ---------------------------------------------------------
    # SUGGESTIONS
    # ---------------------------------------------------------

    def _on_suggestion_activated(
        self,
        label: str,
    ):
        self.chat_view.composer.text_edit.setPlainText(
            label
        )

        self.chat_view.composer.text_edit.setFocus()

    # ---------------------------------------------------------
    # MESSAGE HANDLING
    # ---------------------------------------------------------

    def _on_message_sent(self, text: str):
        if text.strip() == "/quit":
            self.worker.stop()
            QApplication.quit()
            return

        if self.is_requested_input:
            self.chat_view.show_typing(True)

            ui_to_backend.put(
                f"user_input= {text}"
            )

            self.is_requested_input = False

        else:
            if self.worker.is_busy():
                return

            self.chat_view.show_typing(True)

            self.chat_view.add_user_message(
                text
            )

            self.worker.run_prompt(text)

    # ---------------------------------------------------------
    # SHUTDOWN
    # ---------------------------------------------------------

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait(2.0)
        event.accept()

    # ---------------------------------------------------------
    # RESPONSES
    # ---------------------------------------------------------

    def on_llm_response(self, response):
        self.chat_view.show_typing(False)

        self.chat_view.add_ai_message(
            response
        )

    def on_llm_error(self, error_message):
        self.chat_view.show_typing(False)

        self.chat_view.add_ai_message(
            f"Error: {error_message}"
        )

    def show(self):
        self.window.resize(
            1280,
            800,
        )

        self.window.show()


def load_stylesheet(app: QApplication):
    saved_theme = theme_manager.get_saved_theme()

    app.setStyleSheet(
        theme_manager.load_theme_qss(
            saved_theme
        )
    )


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Memo")

    load_stylesheet(app)

    memo = MemoApp()

    memo.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()