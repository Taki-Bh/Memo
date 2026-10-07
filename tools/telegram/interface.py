import os
import sys
import asyncio
import threading
import queue
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

# Make sure Memo's directory is importable
MEMO_PATH = os.path.expanduser("~/Programs/Memo")

if MEMO_PATH not in sys.path:
    sys.path.insert(0, MEMO_PATH)

from core.interface_new import Assistant

log = logging.getLogger("memo.telegram")


@dataclass
class _Job:
    kind: str                      # "message" | "reset"
    chat_id: int
    text: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future


class MemoTelegramInterface:
    """
    Bridges the async Telegram bot and the blocking, Playwright-driven Assistant.

    Why a dedicated worker thread?
      * Playwright (sync API) objects are bound to the thread that created them,
        so every Assistant is created AND used on the single worker thread.
      * Assistant.send() blocks for a long time (browser automation); running it
        on the bot's event loop would freeze Telegram polling.
      * One browser-driven session can't safely handle two prompts at once, so
        jobs are processed strictly one at a time (FIFO queue).

    Each Telegram chat gets its own Assistant (own context / history). Sessions
    are kept in an LRU cache so only `max_sessions` browsers are alive at once.
    """

    HELP_TEXT = (
        "Memo on Telegram\n\n"
        "Just send a message to chat.\n\n"
        "/agent <prompt>   - send a request to the agent router\n"
        "/computer <prompt> - computer-use command\n"
        "/swap <provider>  - switch provider (chatgpt / gemini / ollama)\n"
        "/save [path]      - save this conversation\n"
        "/reset            - start a fresh conversation\n"
        "/help             - show this message"
    )

    def __init__(
        self,
        max_sessions: int = 3,
        request_timeout: float = 300.0,
        allowed_chat_ids: Optional[set[int]] = None,
    ):
        self.max_sessions = max_sessions
        self.request_timeout = request_timeout

        # Optional allow-list. Falls back to TELEGRAM_ALLOWED_CHAT_IDS="123,456".
        if allowed_chat_ids is None:
            raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")
            ids = {int(x) for x in raw.replace(" ", "").split(",") if x}
            allowed_chat_ids = ids or None
        self.allowed_chat_ids = allowed_chat_ids

        self._jobs: "queue.Queue[Optional[_Job]]" = queue.Queue()
        self._sessions: "OrderedDict[int, Assistant]" = OrderedDict()  # worker thread only
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

    # ------------------------------------------------------------------ lifecycle

    def start(self):
        """Start the worker thread (idempotent)."""
        with self._start_lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._worker_loop, name="memo-worker", daemon=True
            )
            self._thread.start()
            log.info("Memo worker thread started")

    def stop(self):
        """Ask the worker to finish and close all sessions."""
        self._jobs.put(None)
        if self._thread:
            self._thread.join(timeout=30)

    # ------------------------------------------------------------------ public async API

    def is_allowed(self, chat_id: int) -> bool:
        return self.allowed_chat_ids is None or chat_id in self.allowed_chat_ids

    async def handle_message(self, chat_id: int, text: str) -> str:
        """
        Called by the bot for every incoming text message.
        Returns the text to send back. Never blocks the event loop.
        """
        text = (text or "").strip()
        if not text:
            return "Empty message."

        if not self.is_allowed(chat_id):
            log.warning("Rejected chat %s", chat_id)
            return "Not authorized."

        # Commands handled locally (no browser needed)
        lowered = text.lower()
        if lowered in ("/start", "/help"):
            return self.HELP_TEXT
        if lowered == "/quit":
            return "/quit is not available over Telegram."

        kind = "reset" if lowered == "/reset" else "message"

        self.start()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._jobs.put(_Job(kind, chat_id, text, loop, future))

        try:
            return await asyncio.wait_for(future, timeout=self.request_timeout)
        except asyncio.TimeoutError:
            return (
                f"Timed out after {int(self.request_timeout)}s. "
                "The browser may still be working; try again in a moment."
            )
        except Exception as e:  # error raised inside the worker
            log.exception("Job failed")
            return f"Error: {e}"

    # ------------------------------------------------------------------ worker thread

    def _worker_loop(self):
        while True:
            job = self._jobs.get()
            if job is None:
                break
            # The caller timed out / cancelled while this was queued.
            if job.future.cancelled():
                continue
            try:
                result = self._process(job)
                self._resolve(job, result=result)
            except Exception as e:
                self._resolve(job, error=e)

        for chat_id in list(self._sessions):
            self._close_session(chat_id)
        log.info("Memo worker thread stopped")

    def _process(self, job: _Job) -> str:
        if job.kind == "reset":
            self._close_session(job.chat_id)
            self._get_session(job.chat_id)  # create a fresh one
            return "Started a fresh conversation."

        assistant = self._get_session(job.chat_id)
        response = assistant.send(job.text)
        return str(response).strip() if response else "(no response)"

    def _get_session(self, chat_id: int) -> Assistant:
        if chat_id in self._sessions:
            self._sessions.move_to_end(chat_id)
            return self._sessions[chat_id]

        # Evict least-recently-used sessions to cap the number of browsers.
        while len(self._sessions) >= self.max_sessions:
            oldest = next(iter(self._sessions))
            log.info("Evicting session for chat %s", oldest)
            self._close_session(oldest)

        log.info("Creating Assistant for chat %s", chat_id)
        assistant = Assistant()
        self._sessions[chat_id] = assistant
        return assistant

    def _close_session(self, chat_id: int):
        assistant = self._sessions.pop(chat_id, None)
        if assistant is None:
            return
        # Best effort: close the Playwright browser if the provider exposes a closer.
        for target in (assistant, getattr(assistant, "llm", None)):
            for name in ("close", "shutdown", "quit"):
                fn = getattr(target, name, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        log.exception("Error while closing session")
                    return

    @staticmethod
    def _resolve(job: _Job, result: Optional[str] = None, error: Optional[Exception] = None):
        """Hand the result back to the bot's event loop thread-safely."""

        def _set():
            if job.future.done():
                return
            if error is not None:
                job.future.set_exception(error)
            else:
                job.future.set_result(result)

        job.loop.call_soon_threadsafe(_set)