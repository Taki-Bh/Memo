import json
import re
from tools.tools import TOOLS_DEFINITIONS, TOOLS
from agents.skills_prompts import *
from agents.skill_store import *
from core.runner import Runner


def extract_unified_output(response: str):
    """
    Parse the Unified Output Object out of an executor response:

        {
          "call": {"op_name": "...", "args": "...", "cmd": "..."} | null,
          "task_state": {"last_checkpoint": "...", "status": "...", ...} | null
        }

    Returns (call_or_None, task_state_or_None, cleaned_response_text).

    - `call` is returned only if it is a dict containing at least "op_name".
    - `task_state` is returned only if it is a dict satisfying
      REQUIRED_STATE_KEYS and a valid VALID_STATUSES status.
    - `cleaned_response_text` is whatever text (if any) surrounded the JSON
      object, with the JSON blob itself stripped out.
    """
    if not isinstance(response, str):
        return None, None, response

    stripped = response.strip()

    data = None
    json_span = None

    # Expected case: the whole response IS the JSON object.
    try:
        data = json.loads(stripped)
        json_span = (0, len(stripped))
    except json.JSONDecodeError:
        # Fallback: locate a JSON object embedded in surrounding text.
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                json_span = match.span()
            except json.JSONDecodeError:
                data = None

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


class SkillExecutionLoop:
    """
    Executes a loaded skill until the task is finished.

    Each turn the LLM returns a single Unified Output Object:
        {"call": {...} | null, "task_state": {...} | null}

    - If "call" is present, the Runner executes it and the result is fed
      back into the next iteration.
    - "task_state" tracks whether the skill is still in progress, waiting
      on the user, blocked, or done.
    """

    def __init__(self, provider, tools, max_iterations: int = 20):
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
            print(f"Call: {call}")
            print(f"Task State: {task_state}")

            # ---------------------------------------------------------
            # 0. Nudge the model if it returned neither field at all.
            # ---------------------------------------------------------
            if call is None and task_state is None:
                if current_state and "last_tool_result" in current_state:
                    nudge = (
                        "You forgot to return the Unified Output Object "
                        f"({{\"call\": ..., \"task_state\": ...}}). The last "
                        f"tool result was {current_state['last_tool_result']}. "
                        "Return the object now."
                    )
                else:
                    nudge = (
                        "You forgot to return the Unified Output Object "
                        "({\"call\": ..., \"task_state\": ...}). Return it now."
                    )
                raw_response = self.provider.generate(nudge)
                call, task_state, cleaned_response = extract_unified_output(raw_response)
                print(f"Retry Call: {call}")
                print(f"Retry Task State: {task_state}")

                if call is None and task_state is None:
                    # Still nothing usable — treat it as a final plain-text answer.
                    return {
                        "status": "done",
                        "state": current_state,
                        "response": cleaned_response,
                    }

            # ---------------------------------------------------------
            # 1. Execute a Runner call if one was requested this turn.
            # ---------------------------------------------------------
            if call:
                result = self._execute_tool(call)
                print(f"Tool result: {result}")
                current_state = self._update_prompt_state(
                    task_state or current_state,
                    call,
                    result,
                )
                print(f"Current State Result: {current_state}")

                raw_response = self.provider.generate(
                    f"Runner result for '{call.get('op_name')}': {result}. "
                    "Continue the skill execution with the updated Unified "
                    "Output Object."
                )
                continue

            # ---------------------------------------------------------
            # 2. No call this turn — inspect task_state.
            # ---------------------------------------------------------
            if task_state:
                current_state = task_state

                if task_state.get("status") == "done":
                    return {
                        "status": "done",
                        "state": task_state,
                        "response": cleaned_response,
                    }

                # Skill isn't finished yet — keep going.
                raw_response = self.provider.generate(
                    "Continue the skill execution with the updated Unified Output Object"
                )
                continue

            # ---------------------------------------------------------
            # 3. No call and no usable task_state = single-turn completion.
            # ---------------------------------------------------------
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
        print(f"name={name}\n args={args} \n cmd={cmd}")

        if name == "exec":
            print(f"executing {cmd}")
            return Runner.run(str(cmd))
        if name == "write":
            sep_index = args.find("||")
            return Runner.write(args[:sep_index], args[sep_index + 1:])
        if name == "read":
            return Runner.read(args)

    def _update_prompt_state(self, state, call, result):
        """
        Store the latest Runner interaction so the next iteration
        can see what happened.

        The actual tool result is embedded into the skill state.
        """
        state = dict(state or {})

        state["last_tool_call"] = call
        state["last_tool_result"] = result

        return state