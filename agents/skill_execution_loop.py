
import json
import queue

import threading

from agents.jsonparser import extract_unified_output
from tools.tools import (
    TOOLS,
    TOOLS_DEFINITIONS,
)
from core.communication import (
    backend_to_ui,
    ui_to_backend,
)

from PySide6.QtCore import QObject, Signal

from agents.skill_store import *
from agents.skills_prompts import *



from runner.runner import Runner



STOP_RESPONSE = "{Skill execution stopped by user.}"
# ==============================================================
# SKILL EXECUTION LOOP
# ==============================================================

class SkillExecutionLoop(QObject):

    stateUpdated = Signal(dict)
    userInputRequested = Signal(dict)
    llmProviderChanged = Signal(str)
    requestedSuper = Signal(str)

    def __init__(
        self,
        provider,
        tools,
        max_iterations: int = 20,
    ):
        super().__init__()

        self.provider = provider
        self.tools = tools
        self.max_iterations = max_iterations

        # Cooperative cancellation.
        self._stop_requested = threading.Event()

    # ==========================================================
    # CANCELLATION
    # ==========================================================

    def stop(self):
        """
        Request cooperative cancellation.

        This does not kill the worker thread.
        """

        self._stop_requested.set()

    def is_stop_requested(self) -> bool:
        return self._stop_requested.is_set()

    def _stopped_result(
        self,
        state=None,
    ):
        """
        Standard result returned when execution is cancelled.
        """
        print(f"[SkillExecutionLoop] Execution cancelled.")
        return {
            "status": "blocked",
            "state": state or {"last_checkpoint": "Execution cancelled."},
            "response": STOP_RESPONSE,
        }

    # ==========================================================
    # EXECUTION
    # ==========================================================

    def execute(
        self,
        skill_name: str,
        skill_content: str,
        user_prompt: str,
        state=None,
        tools_definitions=None,
    ):
        """
        Execute a skill until:

            - completion
            - failure
            - user input
            - cancellation
            - max iterations
        """

        # A new execution starts fresh.
        self._stop_requested.clear()

        current_state = state

        prompt = (
            LOAD_PROMPT

            .replace(
                "{{SKILL_NAME}}",
                skill_name,
            )

            .replace(
                "{{SKILL_MD_CONTENT}}",
                skill_content,
            )

            .replace(
                "{{SKILL_STATE_JSON}}",
                (
                    json.dumps(current_state)
                    if current_state
                    else "null"
                ),
            )

            .replace(
                "{{ORIGINAL_USER_PROMPT}}",
                user_prompt,
            )
        )

        # ======================================================
        # Initial provider call
        # ======================================================

        if self._stop_requested.is_set():
            return self._stopped_result(
                current_state
            )

        raw_response = self.provider.generate(
            prompt
        )

        if self._stop_requested.is_set():
            return self._stopped_result(
                current_state
            )

        # ======================================================
        # Main execution loop
        # ======================================================

        for iteration in range(
            self.max_iterations
        ):

            if self._stop_requested.is_set():
                return self._stopped_result(
                    current_state
                )

            print(
                f"[SkillExecutionLoop] "
                f"Iteration {iteration + 1}/"
                f"{self.max_iterations}"
            )

            # ==================================================
            # Parse LLM output
            # ==================================================

            (
                call,
                task_state,
                cleaned_response,
            ) = extract_unified_output(
                raw_response
            )

            # ==================================================
            # Invalid unified output
            # ==================================================

            if (
                call is None
                and task_state is None
            ):

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                nudge = (
                    "You forgot to return the Unified "
                    "Output Object or returned it in the "
                    "wrong format!\n\n"

                    "EXAMPLE SCHEMA:\n\n"

                    "```json\n"

                    "{\n"

                    '  "call": {'
                    '"op_name": '
                    '"write|read|exec|screenshot", '
                    '"args": "placeholder"'
                    "},\n"

                    '  "task_state": {\n'

                    '    "last_checkpoint": '
                    '"placeholder",\n'

                    '    "status": '
                    '"in_progress|done",\n'

                    '    "last_question_to_user": '
                    "null,\n"

                    '    "remaining_work": '
                    '["placeholder"],\n'

                    '    "context": {}\n'

                    "  }\n"

                    "}\n"

                    "```\n\n"

                    "Use call: null when there is no "
                    "tool to execute.\n"

                    "Set task_state.status to done "
                    "only after the requested task has "
                    "actually been completed.\n\n"

                    + JSON_CONSTRAINT
                )

                raw_response = (
                    self.provider.generate(
                        nudge
                    )
                )

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                continue

            # ==================================================
            # Tool call
            # ==================================================

            if call:

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                if task_state:

                    current_state = task_state

                    self.stateUpdated.emit(
                        current_state
                    )

                result = self._execute_tool(
                    call
                )

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                current_state = (
                    self._update_prompt_state(
                        task_state
                        or current_state,
                        call,
                        result,
                    )
                )

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                raw_response = (
                    self.provider.generate(
                        f"Runner result for "
                        f"'{call.get('op_name')}': "
                        f"{result}. "
                        "Continue the skill execution "
                        "with the updated Unified Output "
                        "Object."
                    )
                )

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                continue

            # ==================================================
            # Task state without a tool call
            # ==================================================

            if task_state:

                status = str(
                    task_state.get(
                        "status",
                        "",
                    )
                ).lower()

                # ==============================================
                # DONE
                # ==============================================

                if status == "done":

                    # Prevent immediate false completion.
                    if iteration == 0:

                        if self._stop_requested.is_set():
                            return self._stopped_result(
                                current_state
                            )

                        raw_response = (
                            self.provider.generate(
                                "You are not to return Done "
                                "at the start of skill "
                                "execution. You must perform "
                                "the required task because "
                                "it has not been performed yet."
                            )
                        )

                        if self._stop_requested.is_set():
                            return self._stopped_result(
                                current_state
                            )

                        continue

                    return {
                        "status": "done",
                        "state": task_state,
                        "response": cleaned_response,
                    }

                # ==============================================
                # BLOCKED / FAILED
                # ==============================================

                if status in {
                    "blocked",
                    "failed",
                }:

                    return {
                        "status": "blocked",
                        "state": task_state,
                        "response": cleaned_response,
                    }

                # ==============================================
                # WAITING FOR USER
                # ==============================================

                if (
                    status
                    == "awaiting_user_input"
                ):

                    result = (
                        self._wait_for_user_input(
                            task_state
                        )
                    )

                    if result is None:
                        return self._stopped_result(
                            current_state
                        )

                    user_response = result

                    if self._stop_requested.is_set():
                        return self._stopped_result(
                            current_state
                        )

                    print(
                        "Received the response: "
                        f"{user_response}"
                    )

                    raw_response = (
                        self.provider.generate(
                            user_response
                        )
                    )

                    if self._stop_requested.is_set():
                        return self._stopped_result(
                            current_state
                        )

                    print(
                        f"Response = {raw_response}"
                    )

                    continue

                # ==============================================
                # IN PROGRESS / OTHER VALID STATUS
                # ==============================================

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                raw_response = (
                    self.provider.generate(
                        "Continue the skill execution "
                        "with the updated Unified Output "
                        "Object."
                    )
                )

                if self._stop_requested.is_set():
                    return self._stopped_result(
                        current_state
                    )

                continue

            # ==================================================
            # No valid output
            # ==================================================

            error_state = {
                "status": "error",
                "state": current_state,
                "response": cleaned_response,
            }

            print(
                "Error: No valid call or task_state "
                f"found in the response. {error_state}"
            )

            print(
                f"Raw response: {raw_response}"
            )

            if self._stop_requested.is_set():
                return self._stopped_result(
                    current_state
                )

            raw_response = (
                "Error: No valid call or task_state "
                "found in the response. "
                "Please return the Unified Output Object."
            )

        # ======================================================
        # Maximum iterations exceeded
        # ======================================================

        return {
            "status": "error",
            "state": current_state,
            "response": (
                "Skill execution exceeded the "
                "maximum of "
                f"{self.max_iterations} iterations."
            ),
        }

    # ==========================================================
    # USER INPUT
    # ==========================================================

    def _wait_for_user_input(
        self,
        task_state,
    ):
        """
        Wait for UI input without blocking cancellation.

        Returns:

            str  -> user response
            None -> execution was cancelled
        """

        backend_to_ui.put(
            task_state
        )

        self.userInputRequested.emit(
            task_state
        )

        while not self._stop_requested.is_set():

            try:

                return ui_to_backend.get(
                    timeout=0.1
                )

            except queue.Empty:
                continue

        return None

    # ==========================================================
    # TOOL EXECUTION
    # ==========================================================

    def _execute_tool(
        self,
        call: dict,
    ):

        if self._stop_requested.is_set():
            return STOP_RESPONSE

        name = call.get(
            "op_name"
        )

        args = call.get(
            "args"
        ) or ""

        cmd = call.get(
            "cmd"
        ) or ""

        # ======================================================
        # EXEC
        # ======================================================

        if name == "exec":

            if not cmd:
                return "No command provided."

            if self._stop_requested.is_set():
                return STOP_RESPONSE

            # NOTE:
            #
            # This is a textual check.
            #
            # If your security model needs proper shell
            # command parsing, replace this with a dedicated
            # command parser.

            requires_confirmation = (
                "sudo" in cmd
            )

            if requires_confirmation:

                self.requestedSuper.emit(
                    cmd
                )

                backend_to_ui.put(
                    cmd
                )

                confirmation = (
                    self._wait_for_confirmation()
                )

                if confirmation is None:
                    return STOP_RESPONSE

                if confirmation:

                    if self._stop_requested.is_set():
                        return STOP_RESPONSE

                    return Runner.run(
                        str(cmd)
                    )

                return (
                    "Request for command denied."
                )

            if self._stop_requested.is_set():
                return STOP_RESPONSE

            return Runner.run(
                str(cmd)
            )

        # ======================================================
        # WRITE
        # ======================================================

        if name == "write":

            separator = "||"

            sep_index = args.find(
                separator
            )

            if sep_index == -1:

                return (
                    "Invalid write arguments. "
                    "Expected: path||content"
                )

            path = args[
                :sep_index
            ].strip()

            content = args[
                sep_index + len(separator):
            ]

            if not path:

                return (
                    "Invalid write arguments: "
                    "missing path."
                )

            if self._stop_requested.is_set():
                return STOP_RESPONSE

            return Runner.write(
                path,
                content,
            )

        # ======================================================
        # READ
        # ======================================================

        if name == "read":

            if not args:
                return "No file path provided."

            if self._stop_requested.is_set():
                return STOP_RESPONSE

            return Runner.read(
                args
            )

        # ======================================================
        # SCREENSHOT
        # ======================================================

        if name == "screenshot":

            if self._stop_requested.is_set():
                return STOP_RESPONSE

            screenshot = Runner.screenshot()

            return (
                "[THIS A BASE 64 ENCRYPTED IMAGE]"
                + screenshot
                + "[END OF BASE 64 ENCRYPTED IMAGE]"
            )

        # ======================================================
        # UNKNOWN TOOL
        # ======================================================

        return (
            f"Unknown tool operation: {name}"
        )

    # ==========================================================
    # SUDO CONFIRMATION
    # ==========================================================

    def _wait_for_confirmation(self):
        """
        Wait for sudo confirmation without blocking Stop.
        """

        while not self._stop_requested.is_set():

            try:

                return ui_to_backend.get(
                    timeout=5
                )

            except queue.Empty:
                continue

        return None

    # ==========================================================
    # STATE
    # ==========================================================

    def _update_prompt_state(
        self,
        state,
        call,
        result,
    ):

        state = dict(
            state or {}
        )

        state[
            "last_tool_call"
        ] = call

        state[
            "last_tool_result"
        ] = result

        return state

