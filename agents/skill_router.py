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





class SkillRouterAgent(Agent):

    def __init__(self, provider: LLMProvider):
        super().__init__(provider)

        self.skill_index_json = json.dumps(provider.skill_index)
        self.state_store = StateStore()

        self.execution_loop = SkillExecutionLoop(
            provider=provider,
            tools=TOOLS,
            max_iterations=20,
        )

    def handleRequest(self, prompt: str, session_id: str = "default"):

        state = self.state_store.get(session_id)

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

        raw = self.provider.generate(router_prompt)

        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            return f"Router returned invalid JSON: {raw!r}"

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

            resume_state = (
                state
                if action == "continue_skill"
                else None
            )

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

            new_state = result.get("state")

            if result["status"] == "done":
                self.state_store.clear(session_id)

            elif new_state:
                self.state_store.set(
                    session_id,
                    new_state,
                )

            # ---------------------------------------------------------
            # Skill creator special handling
            # ---------------------------------------------------------

            cleaned_response = result["response"]

            if skill.get("name") == "skill-creator":
                return self._save_created_skill(
                    cleaned_response
                )

            return cleaned_response

        # -------------------------------------------------------------
        # Draft a new skill
        # -------------------------------------------------------------

        if action == "draft_new_skill":

            creator = fetch_skill(
                "skills/skill-creator/SKILL.md"
            )

            draft_prompt = (
                DRAFT_PROMPT
                .replace(
                    "{{SKILL_CREATOR_MD_CONTENT}}",
                    creator.get("body", ""),
                )
                .replace(
                    "{{ORIGINAL_USER_PROMPT}}",
                    prompt,
                )
                .replace(
                    "{{SUGGESTED_NAME}}",
                    response.get("suggested_name", ""),
                )
            )

            return self.provider.generate(draft_prompt)

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