from unittest import result
from urllib import response

from core.agent import Agent
from core.provider import LLMProvider
from core.skills import *
import json
import re
import time
from pathlib import Path
from tools.tools import TOOLS_DEFINITIONS,TOOLS
from agents.skills_prompts import *
from agents.skill_store import *
from agents.skill_execution_loop import *

COMPUTER_SKILL_PATH = Path(__file__).parent.parent / "skills" / "computer_skill"




class SkillRouterAgent(Agent):

    def __init__(self, provider: LLMProvider):
        super().__init__(provider)
        self.state=None
        self.skill_index_json = json.dumps(provider.skill_index)
        self.state_store = StateStore()
        self.role ="SkillRouterAgent"
        self.execution_loop = SkillExecutionLoop(
            provider=provider,
            tools=TOOLS,
            max_iterations=20,
        )
    def handleRequest(self, command:str,prompt: str, session_id: str = "default"):
        result=None
        if command=="/computer":
            result=self.handleComputer(prompt, session_id)
        else:
            result=self.handleRoute(prompt, session_id)




        
        exec_state=result.get("state")
            #print(f"Execution state: {exec_state}")
        cleaned_response = ""
        if exec_state is None:
            cleaned_response = "Skill execution returned no result."
        else:
            cleaned_response = (
                exec_state.get("message") or exec_state.get("last_checkpoint") or ""
            ).strip() or f"Empty response from skill execution. {exec_state}"
            """if skill.get("name") == "skill-creator":
                return self._save_created_skill(
                    cleaned_response
                )"""

        return cleaned_response    
    def handleComputer(self,prompt: str, session_id: str = "default"):
        
        skill=fetch_skill("skills/computer_skill/SKILL.md")
        result=self.handleSkill(skill, prompt, session_id)
        return result
    def handleSkill(self, skill, prompt: str, session_id: str = "default"):
                    if not skill:
                        return f"Router pointed at unknown skill path: {path!r}"
                                    
                    state=self.state
                    action=None
                   
                    resume_state = (
                        state
                        if action == "continue_skill"
                        else None
                    )
                    self.execution_loop.stateUpdated.emit({"last_checkpoint" : f"Starting skill execution for {skill.get('name', 'Unknown')}..."})
                    result = self.execution_loop.execute(
                        skill_name=skill.get("name", "Unknown"),
                        skill_content=skill.get("body", ""),
                        user_prompt=prompt,
                        state=resume_state,
                        tools_definitions=TOOLS_DEFINITIONS,
                    )
        
                    # ---------------------------------------------------------
                    # Persist execution state
                    # ---------------------------------------------------------
                    print("********-************************************")
                    #print(f"Execution result: {result}")
                    new_state = result.get("state")
        
                    if result["status"] == "done":
                        self.state_store.clear(session_id)
        
                    elif new_state:
                        self.state_store.set(
                            session_id,
                            new_state,
                        )
                    return result
        
    def handleRoute(self,prompt: str, session_id: str = "default"):

        self.state = self.state_store.get(session_id)
        state=self.state
        
       

        # -------------------------------------------------------------
        # Router
        # -------------------------------------------------------------
        
        router_prompt = (
            ROUTER_PROMPT
            .replace("{{SKILL_INDEX_JSON}}", self.skill_index_json)
            .replace(
                "{{SKILL_STATE_JSON}}",
                json.dumps(state) if state else "null",
            )
            .replace("{{USER_PROMPT}}", prompt)
            .replace(
                                "{{TOOLS_INDEX}}",str(TOOLS_DEFINITIONS)
                                
            )
        )
        self.execution_loop.stateUpdated.emit({"last_checkpoint" : "Loading router prompt..."})
        raw = self.provider.generate(router_prompt)

        try:
            response = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except json.JSONDecodeError:
            raw = self.provider.generate(f"Router returned invalid JSON: {raw!r}, Return a valid JSON for the execution")


        action = response.get("action")

        # -------------------------------------------------------------
        # Direct response
        # -------------------------------------------------------------

        if action == "respond_directly":
            return self.provider.generate(prompt)

        # -------------------------------------------------------------
        # Load / continue skill
        # -------------------------------------------------------------

        if action in ("load_skill", "continue_skill"):
            path = response.get("path")
            
            skill = fetch_skill(path)
            if not skill:
                return f"Router pointed at unknown skill path: {path!r}"
                            
            result=self.handleSkill(skill, prompt, session_id)
           
            return result

        return f"Unknown router action: {action!r}"

    def _save_created_skill(self, content):

        parent_dir = Path("skills")

        try:
            data = parse_frontmatter_content(content)

            skill_dir = parent_dir / data["name"]
            file_path = skill_dir / "SKILL.md"

            skill_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_path.write_text(
                content,
                encoding="utf-8",
            )

            return (
                f"Successfully created skill file at: "
                f"{file_path.absolute()}"
            )

        except Exception as e:
            return f"Error creating skill file: {e}"