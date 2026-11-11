
import os
import signal
import subprocess
import threading
from typing import Any

from tools.tools import read, write, screenshot
from core.config import SUDO_PASSWORD


class Runner:
    _process = None
    _thread = None
    _result = None
    _lock = threading.RLock()

    @classmethod
    def start(cls, command: str, enable_timeout: bool = True) -> str:
        """Start a shell command asynchronously."""

        with cls._lock:
            if cls._process is not None and cls._process.poll() is None:
                return "A command is already running."

            cls._result = None

            actual_command = command
            input_data = None

            if (
                SUDO_PASSWORD
                and "sudo" in command
                and "sudo -S" not in command
            ):
                actual_command = (
                    f"sudo -S {command.split('sudo', 1)[1].lstrip()}"
                )
                input_data = SUDO_PASSWORD + "\n"

            disable_timeout = any(
                word in command for word in ("install", "curl", "update")
            )

            timeout = (
                30
                if enable_timeout and not disable_timeout
                else None
            )

            try:
                process = subprocess.Popen(
                    actual_command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE if input_data else None,
                    text=True,
                    start_new_session=True,
                )
            except Exception as error:
                return f"Failed to start command: {error}"

            cls._process = process

            def worker():
                try:
                    output, _ = process.communicate(
                        input=input_data,
                        timeout=timeout,
                    )
                    result = (
                        f"[EXITCODE={process.returncode}]"
                        f"{output or ''}"
                    )
                except subprocess.TimeoutExpired:
                    cls._terminate_process(process)
                    output, _ = process.communicate()
                    result = (
                        f"[EXITCODE=-1]{output or ''}"
                        "[Command timed out after 30 seconds]"
                    )
                except Exception as error:
                    result = f"[EXITCODE=-1]Execution error: {error}"

                with cls._lock:
                    # Don't overwrite a result from a newer command.
                    if cls._process is process:
                        cls._result = result

                print(result)

            cls._thread = threading.Thread(
                target=worker,
                daemon=True,
            )
            cls._thread.start()

            return f"Started command (PID={process.pid})"

    @staticmethod
    def _terminate_process(process, grace: float = 2.0):
        """Terminate the shell and its process group."""
        if process.poll() is not None:
            return

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @classmethod
    def stop(cls) -> str:
        """Stop the currently running command."""
        with cls._lock:
            process = cls._process

        if process is None or process.poll() is not None:
            return "No command is currently running."

        cls._terminate_process(process)

        thread = cls._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)

        return "Stop signal sent to the command."

    @classmethod
    def is_running(cls) -> bool:
        with cls._lock:
            return (
                cls._process is not None
                and cls._process.poll() is None
            )

    @classmethod
    def get_result(cls) -> Any:
        """Get the result without blocking."""
        with cls._lock:
            return cls._result

    @staticmethod
    def run(command: str) -> str:
        """Keep the original synchronous interface."""
        from tools.tools import exec
        return exec(command)

    @staticmethod
    def read(path: str):
        return read(path)

    @staticmethod
    def write(path: str, text: str):
        return write(path, text)

    @staticmethod
    def screenshot():
        return screenshot()
