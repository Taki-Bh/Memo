
import json
import queue

import threading


from tools.tools import (
    TOOLS,
    TOOLS_DEFINITIONS,
)
from core.communication import (
    backend_to_ui,
    ui_to_backend,
)
import re
from json_repair import repair_json

from PySide6.QtCore import QObject, Signal

from agents.skill_store import *
from agents.skills_prompts import *



from runner.runner import Runner



STOP_RESPONSE = "{Skill execution stopped by user.}"


# ==============================================================
# DIRTY JSON
# ==============================================================

def _try_json_loads(text: str):
    """
    Fast JSON parser.

    Returns the parsed object or None.
    """

    if not isinstance(text, str):
        return None

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _repair_json(text: str):
    """
    Repair malformed LLM JSON using json-repair.

    Handles common LLM mistakes such as:

        - unescaped quotes
        - single quotes
        - missing commas
        - trailing commas
        - missing closing braces
        - missing quotes around keys
        - incomplete objects
        - multiline strings
        - extra/malformed JSON syntax
    """

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Fast path.
    parsed = _try_json_loads(text)

    if parsed is not None:
        return parsed

    # Dirty JSON repair.
    try:
        repaired = repair_json(
            text,
            skip_json_loads=False,
        )

        if not repaired:
            return None

        return json.loads(repaired)

    except Exception:
        return None


def _extract_json_candidates(text: str):
    """
    Extract likely JSON objects from an LLM response.

    Handles:

        normal JSON
        ```json ... ```
        text before JSON
        text after JSON
        nested JSON objects
        incomplete JSON objects
    """

    if not isinstance(text, str):
        return []

    candidates = []

    # ----------------------------------------------------------
    # Markdown JSON blocks
    # ----------------------------------------------------------

    fenced_blocks = re.findall(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    candidates.extend(fenced_blocks)

    # ----------------------------------------------------------
    # Balanced JSON object extraction
    #
    # We do NOT use:
    #
    #     r"\{.*\}"
    #
    # because that breaks easily with nested objects and braces
    # inside strings.
    # ----------------------------------------------------------

    start = None
    depth = 0

    in_string = False
    escaped = False

    for index, char in enumerate(text):

        if in_string:

            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":

            if depth == 0:
                start = index

            depth += 1

        elif char == "}":

            if depth > 0:
                depth -= 1

                if depth == 0 and start is not None:
                    candidates.append(
                        text[start:index + 1]
                    )

                    start = None

    # ----------------------------------------------------------
    # Incomplete JSON object
    #
    # Example:
    #
    # {
    #     "call": {
    #         "op_name": "write",
    #         "args": "test.txt||hello
    #
    # json-repair may be able to recover this.
    # ----------------------------------------------------------

    if start is not None:
        candidates.append(
            text[start:]
        )

    return candidates


def _lenient_json_loads(text: str):
    """
    Robust JSON parser designed for LLM output.

    Parsing order:

        1. Normal json.loads()
        2. json-repair on entire response
        3. Extract JSON candidates
        4. Normal json.loads() on candidates
        5. json-repair on candidates

    Normal valid JSON therefore stays on the fastest path.
    """

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # ==========================================================
    # 1. Normal JSON
    # ==========================================================

    parsed = _try_json_loads(text)

    if parsed is not None:
        return parsed

    # ==========================================================
    # 2. Repair the complete response
    # ==========================================================

    parsed = _repair_json(text)

    if parsed is not None:
        return parsed

    # ==========================================================
    # 3. Extract possible JSON blocks
    # ==========================================================

    candidates = _extract_json_candidates(text)

    # Larger candidates first.
    candidates.sort(
        key=len,
        reverse=True,
    )

    # ==========================================================
    # 4/5. Parse / repair candidates
    # ==========================================================

    for candidate in candidates:

        parsed = _try_json_loads(candidate)

        if parsed is not None:
            return parsed

        parsed = _repair_json(candidate)

        if parsed is not None:
            return parsed

    return None


def extract_unified_output(response: str):
    """
    Extract the Unified Output Object from an LLM response.

    Returns:

        call,
        task_state,
        cleaned_response

    The parser intentionally accepts dirty JSON because LLMs can
    produce things like:

        {'call': {'op_name': 'read', 'args': 'test.txt'}}

    or:

        {
            "call": {
                "op_name": "exec",
                "cmd": "python -c \"print('hello')\""
            },
            "task_state": {
                ...
            }
        }

    or JSON surrounded by explanatory text.
    """

    if not isinstance(response, str):
        return None, None, response

    stripped = response.strip()

    if not stripped:
        return None, None, stripped

    # ----------------------------------------------------------
    # Parse response
    # ----------------------------------------------------------

    data = _lenient_json_loads(stripped)

    json_span = None

    # ----------------------------------------------------------
    # Find JSON span for cleaned response
    # ----------------------------------------------------------

    if data is not None:

        # Entire response is JSON.
        if (
            stripped.startswith("{")
            and stripped.endswith("}")
        ):
            json_span = (
                0,
                len(stripped),
            )

        else:
            # Try to locate the actual JSON object.
            start = stripped.find("{")
            end = stripped.rfind("}")

            if (
                start != -1
                and end != -1
                and end > start
            ):
                json_span = (
                    start,
                    end + 1,
                )

    # ----------------------------------------------------------
    # If normal extraction failed, try candidate extraction
    # directly and determine its position.
    # ----------------------------------------------------------

    if data is None:

        candidates = _extract_json_candidates(
            stripped
        )

        candidates.sort(
            key=len,
            reverse=True,
        )

        for candidate in candidates:

            candidate_data = _try_json_loads(
                candidate
            )

            if candidate_data is None:
                candidate_data = _repair_json(
                    candidate
                )

            if candidate_data is None:
                continue

            if not isinstance(
                candidate_data,
                dict,
            ):
                continue

            if (
                "call" not in candidate_data
                and "task_state" not in candidate_data
            ):
                continue

            data = candidate_data

            start = stripped.find(candidate)

            if start != -1:
                json_span = (
                    start,
                    start + len(candidate),
                )

            break

    # ----------------------------------------------------------
    # Clean response
    # ----------------------------------------------------------

    if json_span is not None:

        cleaned = (
            stripped[:json_span[0]]
            + stripped[json_span[1]:]
        ).strip()

    else:
        cleaned = stripped

    # ----------------------------------------------------------
    # Top-level validation
    # ----------------------------------------------------------

    if not isinstance(data, dict):
        return None, None, cleaned

    if (
        "call" not in data
        and "task_state" not in data
    ):
        return None, None, cleaned

    print(
        "[UnifiedOutput]",
        data,
    )

    # ==========================================================
    # Parse tool call
    # ==========================================================

    call = data.get("call")

    if not (
        isinstance(call, dict)
        and isinstance(
            call.get("op_name"),
            str,
        )
        and call.get("op_name").strip()
    ):
        call = None

    # ==========================================================
    # Parse task state
    # ==========================================================

    task_state = data.get(
        "task_state"
    )

    if isinstance(
        task_state,
        dict,
    ):

        if (
            not REQUIRED_STATE_KEYS.issubset(
                task_state
            )
            or task_state.get("status")
            not in VALID_STATUSES
        ):
            task_state = None

    else:
        task_state = None

    return (
        call,
        task_state,
        cleaned,
    )

