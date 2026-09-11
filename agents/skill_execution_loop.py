import json
import re
from tools.tools import TOOLS_DEFINITIONS, TOOLS
from agents.skills_prompts import *
from agents.skill_store import *
from core.runner import Runner
from PySide6.QtCore import QObject, Signal


_FREE_TEXT_FIELDS = ("cmd", "args", "last_question_to_user")


def _repair_free_text_field(text: str, field_name: str) -> str:
    pattern = re.compile(
        r'("' + re.escape(field_name) + r'"\s*:\s*")(.*?)("\s*'
        r'(?:,\s*"[a-zA-Z_]+"\s*:|\}\s*,\s*"[a-zA-Z_]+"\s*:|\}\s*\}))',
        re.DOTALL,
    )

    def _escape(m):
        prefix, value, suffix = m.group(1), m.group(2), m.group(3)
        fixed = value.replace("\\", "\\\\").replace('"', '\\"')
        return prefix + fixed + suffix

    new_text, count = pattern.subn(_escape, text, count=1)
    return new_text if count else text


def _lenient_json_loads(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    repaired = text
    for field in _FREE_TEXT_FIELDS:
        candidate = _repair_free_text_field(repaired, field)
        if candidate == repaired:
            continue
        repaired = candidate
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def extract_unified_output(response: str):
    if not isinstance(response, str):
        return None, None, response

    stripped = response.strip()
    data = _lenient_json_loads(stripped)
    json_span = (0, len(stripped)) if data is not None else None

    if data is None:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            data = _lenient_json_loads(match.group(0))
            if data is not None:
                json_span = match.span()

    if json_span:
        cleaned = (stripped[:json_span[0]] + stripped[json_span[1]:]).strip()
    else:
        cleaned = stripped

    if not isinstance(data, dict) or ("call" not in data and "task_state" not in data):
        return None, None, cleaned

    call = data.get("call")
    if not (isinstance(call, dict) and "op_name" in call):
        call = None

    task_state = data.get("task_state")
    if isinstance(task_state, dict):
        if not REQUIRED_STATE_KEYS.issubset(task_state) or task_state.get("status") not in VALID_STATUSES:
            task_state = None
    else:
        task_state = None

    return call, task_state, cleaned


class SkillExecutionLoop(QObject):
    stateUpdated = Signal(dict)

    def __init__(self, provider, tools, max_iterations: int = 20):
        super().__init__()
        self.provider = provider
        self.tools = tools
        self.max_iterations = max_iterations

    def execute(
        self,
        skill_name: str,
        skill_content: str,
        user_prompt: str,
        state=None,
        tools_definitions=None,
    ):
        current_state = state
        prompt = (
            LOAD_PROMPT
            .replace("{{SKILL_NAME}}", skill_name)
            .replace("{{SKILL_MD_CONTENT}}", skill_content)
            .replace(
                "{{SKILL_STATE_JSON}}",
                json.dumps(current_state) if current_state else "null",
            )
            .replace("{{ORIGINAL_USER_PROMPT}}", user_prompt)
        )

        raw_response = self.provider.generate(prompt)
        for iteration in range(self.max_iterations):
            call, task_state, cleaned_response = extract_unified_output(raw_response)

            if call is None and task_state is None:
                nudge = (
                    "You forgot to return the Unified Output Object "
                    '({"call": ..., "task_state": ...}). Return it now.'
                )
                raw_response = self.provider.generate(nudge)
                call, task_state, cleaned_response = extract_unified_output(raw_response)
                
                

            if call:
                self.stateUpdated.emit(current_state)
                result = self._execute_tool(call)
                current_state = self._update_prompt_state(
                    task_state or current_state,
                    call,
                    result,
                )
                

                raw_response = self.provider.generate(
                    f"Runner result for '{call.get('op_name')}': {result}. "
                    "Continue the skill execution with the updated Unified "
                    "Output Object."
                )
                continue

            if task_state:
                current_state = task_state
                self.stateUpdated.emit(current_state)

                if task_state.get("status") == "done":
                    return {
                        "status": "done",
                        "state": task_state,
                        "response": cleaned_response,
                    }

                raw_response = self.provider.generate(
                    "Continue the skill execution with the updated Unified Output Object"
                )
                continue

            return {
                "status": "done",
                "state": current_state,
                "response": cleaned_response,
            }

        return {
            "status": "error",
            "state": current_state,
            "response": (
                f"Skill execution exceeded the maximum of "
                f"{self.max_iterations} iterations."
            ),
        }

    def _execute_tool(self, call: dict):
        name = call.get("op_name")
        args = call.get("args") or ""
        cmd = call.get("cmd") or ""
        if name == "exec":
            return Runner.run(str(cmd))
        if name == "write":
            sep_index = args.find("||")
            return Runner.write(args[:sep_index-1], args[sep_index + 3:])
        if name == "read":
            return Runner.read(args)

    def _update_prompt_state(self, state, call, result):
        state = dict(state or {})
        state["last_tool_call"] = call
        state["last_tool_result"] = result
        return state
