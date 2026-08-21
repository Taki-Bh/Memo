import json

import re
from tools.tools import TOOLS_DEFINITIONS,TOOLS
from agents.skills_prompts import *
from agents.skill_store import *


def extract_skill_state(response: str):
    """Pull the <skill_state>{...}</skill_state> block out of an executor response.
    Returns (state_or_None, cleaned_response_text)."""
    match = re.search(r"<skill_state>\s*(\{.*?\})\s*</skill_state>", response, re.DOTALL)
    cleaned = re.sub(r"<skill_state>.*?</skill_state>", "", response, flags=re.DOTALL).strip()
    if not match:
        return None, cleaned
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, cleaned
    if not REQUIRED_STATE_KEYS.issubset(state) or state.get("status") not in VALID_STATUSES:
        return None, cleaned
    return state, cleaned

class SkillExecutionLoop:
    """
    Executes a loaded skill until the task is finished.

    The LLM may either:
      - return a normal response
      - return a tool call
      - return a skill-state block indicating completion
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
            

            

            # ---------------------------------------------------------
            # 1. Check whether the LLM returned a tool call.
            # ---------------------------------------------------------
            tool_call = self._parse_tool_call(raw_response)
            print(f"Tool to call {tool_call}")
            if tool_call:
                result = self._execute_tool(tool_call)

                # Feed the tool result back into the next LLM iteration.
                current_state = self._update_prompt_state(
                    current_state,
                    tool_call,
                    result,
                )

                continue

            # ---------------------------------------------------------
            # 2. Normal skill response.
            # ---------------------------------------------------------
            new_state, cleaned_response = extract_skill_state(raw_response)

            if new_state:
                current_state = new_state

                if new_state.get("status") == "done":
                    return {
                        "status": "done",
                        "state": new_state,
                        "response": cleaned_response,
                    }

                # Skill isn't finished yet.
                # Continue the loop with the updated state.
                raw_response=self.provider.generate("Step is done with success, Continue")
                continue
            else:
                if current_state["status"]!="done":
                    aux_response=self.provider.generate("You did not provide the skill state dictionnary")
                    new_state,cleaned_response=extract_skill_state(aux_response)
            # ---------------------------------------------------------
            # 3. No state and no tool call = single-turn completion.
            # ---------------------------------------------------------
            print(f"New State:{new_state}")
            if new_state:
                    current_state = new_state
            
                    if new_state.get("status") == "done":
                        return {
                                "status": "done",
                                "state": new_state,
                                "response": cleaned_response,
                     }
                    raw_response=self.provider.generate("Step is done with success, Continue")

                    continue    
            return {
                "status": "done",
                "state": None,
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

    def _parse_tool_call(self, raw_response):
        """
        Extract a tool-call dictionary from the LLM response.

        Expected format:

        {
            "name": "read",
            "argv": ["skills/example/SKILL.md"],
            "argc": 1
        }
        """

        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        if "function_name" not in data:
            return None

        if "argv" not in data:
            return None

        if "argc" not in data:
            return None

        return data

    def _execute_tool(self, call):
        name = call["function_name"]
        argv = call["argv"]
        argc = call["argc"]

        # Validate argc.
        if argc != len(argv):
            return {
                "success": False,
                "error": (
                    f"Invalid tool call: argc={argc}, "
                    f"but argv contains {len(argv)} arguments."
                ),
            }

        # Validate tool existence.
        if name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {name!r}",
            }

        tool = self.tools[name]

        try:
            result = tool(*argv)

            return {
                "success": True,
                "tool": name,
                "result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "tool": name,
                "error": str(e),
            }

    def _update_prompt_state(self, state, tool_call, result):
        """
        Store the latest tool interaction so the next iteration
        can see what happened.

        The actual tool result is embedded into the skill state.
        """

        state = dict(state or {})

        state["last_tool_call"] = tool_call
        state["last_tool_result"] = result

        return state
