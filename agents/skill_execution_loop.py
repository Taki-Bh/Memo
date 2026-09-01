import json

import re
from tools.tools import TOOLS_DEFINITIONS,TOOLS
from agents.skills_prompts import *
from agents.skill_store import *
from core.runner import Runner

def extract_skill_state(response: str):
    """Pull the <task_state>{...}</task_state> block out of an executor response.
    Returns (state_or_None, cleaned_response_text)."""
    match = re.search(r"<task_state>\s*(\{.*?\})\s*</task_state>", response, re.DOTALL)
    cleaned = re.sub(r"<task_state>.*?</task_state>", "", response, flags=re.DOTALL).strip()
    if not match:
        return None, cleaned
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, cleaned
    print(f"state_dict={state}")
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
        print("Hello WOrld!")
        raw_response = self.provider.generate(prompt)

        for iteration in range(self.max_iterations):
            

            

            # ---------------------------------------------------------
            # 1. Check whether the LLM returned a tool call.
            # ---------------------------------------------------------
            tool_call = self._parse_tool_call(raw_response)
            print(f"Tool to call {tool_call}")
            if tool_call:
                result = self._execute_tool(tool_call)
                print(f"Tool result: {result}")
                # Feed the tool result back into the next LLM iteration.
                current_state = self._update_prompt_state(
                    current_state,
                    tool_call,
                    result,
                )
                print(f"Current State Result: {current_state}")

                

            # ---------------------------------------------------------
            # 2. Normal skill response.
            # ---------------------------------------------------------
            new_state, cleaned_response = extract_skill_state(raw_response)
            print(new_state)
            if not new_state:
                    resp=self.provider.generate("You forgot the state block")
                    if current_state and "last_tool_result" in current_state:
                        resp=self.provider.generate(f"You forgot the state block, The last tool result was {current_state['last_tool_result']}")
                    else:
                        resp=self.provider.generate("You forgot the state block")
                    new_state ,_= extract_skill_state(resp)
            print(new_state)
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
        Extract and validate a tool-call dictionary from an LLM response.

        Expected format:

        <call-block>
        {
            "tool_path": "tools/tools.py",
            "function_name": "read",
            "argv": "~",
            "argc": 1
        }
        </call-block>
        """

        if not isinstance(raw_response, str):
            return None

        start_tag = "<call-block>"
        end_tag = "</call-block>"

        start = raw_response.find(start_tag)
        end = raw_response.find(end_tag)

        if start == -1 or end == -1 or end <= start:
            return None

        json_text = raw_response[
            start + len(start_tag):end
        ].strip()

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        required_keys = {
            "op_name",

        }

        if not required_keys.issubset(data):
            return None

        """if not isinstance(data["op_name"], str):
            return None

        if not isinstance(data["cmd"], str):
            return None"""


        return data

    def _execute_tool(self, call:dict):
        print(call)
        name = call.get("op_name")
        args = call.get("args") or ""
        cmd=call.get("cmd") or ""
        print(call)
        print(f"name={name}\n args={args} \n cmd={cmd}")
   
        if name=="exec":
            print(f"executing {cmd}")
           
            return Runner.run(str(cmd))
        if name =="write":
            sep_index=args.find("||")
            return Runner.write(args[:sep_index],args[sep_index+1:])
        if name== "read":
            return Runner.read(args)
            
    

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
