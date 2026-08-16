
from core.agent import Agent
from core.provider import LLMProvider
from core.skills import *
import json
import time
from pathlib import Path
ROUTER_PROMPT="""
=== STAGE 1: SKILL ROUTER PROMPT ===

## Role
You are a Skill Router Agent. Your sole purpose is to classify the user's request against a Skill Index and return a routing decision. You do not solve tasks and you do not have skill instructions loaded yet.

## Task
Analyze the user's request and choose exactly ONE of these three outcomes:

1. **MATCH** — the request matches an existing skill's trigger conditions.
2. **DRAFT** — no existing skill matches, but the request represents a repeatable capability worth turning into a new skill.
3. **DIRECT** — no existing skill matches and this is an ordinary one-off request that doesn't warrant a new skill (a question, a simple task, casual conversation).

## Constraints
- Do not attempt to solve the user's task.
- Do not explain your reasoning.
- Output must be a single JSON object and nothing else — no markdown code fences, no prose before or after it.

## Output Format

MATCH:
{"action": "load_skill", "path": "path/to/skill_file.md"}

DRAFT:
{"action": "draft_new_skill", "suggested_name": "kebab-case-name"}

DIRECT:
{"action": "respond_directly"}

## Skill Index
{{SKILL_INDEX_JSON}}

## User Request
{{USER_PROMPT}}
"""





LOAD_PROMPT="""
=== STAGE 2a: SKILL EXECUTION PROMPT ===

## Role
You are now a {{SKILL_NAME}} Specialist, operating strictly under the loaded skill's instructions.

## Loaded Skill Instructions
{{SKILL_MD_CONTENT}}

## Original User Task
{{ORIGINAL_USER_PROMPT}}

## Constraints
- Follow the skill's workflow, constraints, and output format exactly. Do not deviate.
- Only give the user SKILL.md contents as a response nothing more nothing less.
- You have no ability to save, upload, or persist files unless a real tool/function result is explicitly provided to you in this call. Never narrate an attempt, an error, or a failure (e.g. "authentication error," "couldn't save") for an action you were not actually given a tool to perform. If persistence is needed, state once, plainly, that it's outside what you can do here, and output the content instead.
- Do not mention  the router, the skill index, or the loading process. Respond only with the task output the skill defines.

## Output
Provide the final result as defined by the skill instructions.
"""


DRAFT_PROMPT="""
=== STAGE 2b: SKILL DRAFTING PROMPT ===

## Role
You are now operating under the skill-creator process to draft a new skill.

## Skill Creator Instructions
{{SKILL_CREATOR_MD_CONTENT}}

## Original User Task
{{ORIGINAL_USER_PROMPT}}

## Suggested Name
{{SUGGESTED_NAME}}

## Constraints
- Draft a complete SKILL.md per the skill-creator process: frontmatter (name, description) + body (When to trigger, Steps, Output format, Edge cases).
- You have no ability to save the file yourself. Do not claim to have attempted saving it, and do not report an error about saving. State once, plainly, that this draft needs to be persisted to the skill index by the calling system, then output the SKILL.md content.
- Also complete the Original User Task itself using the drafted skill's own logic, if the task calls for an actual output beyond the skill definition.

## Output
1. The complete SKILL.md content, verbatim, in a single block.
2. Then the actual task output, if applicable."""


class SkillRouterAgent(Agent):
    instruction :str =""
    def __init__(self,provider : LLMProvider):
        super().__init__(provider)
        self.instruction=ROUTER_PROMPT.replace("{SKILL_INDEX_JSON}",str(provider.skill_index))
    def handleRequest(self,prompt : str):
        self.instruction=self.instruction.replace("{USER_PROMPT}",prompt)
        response=self.provider.generate(self.instruction)
        response=json.loads(response)
        action=response["action"]
       
        skill=fetch_skill(response["path"])
        load_prompt=LOAD_PROMPT.replace("{{SKILL_NAME}}",skill.get("name")).replace("{SKILL_MD_CONTENT}",skill.get("body")).replace("{USER_PROMPT}",prompt)
        time.sleep(5)
        print("---------------\n------------\n----------")
        response=self.provider.generate(load_prompt)
        
        if skill["name"]=="skill-creator":
            # 1. Define the base parent folder
            parent_dir = Path("skills")
            
            # 2. Construct the full path: skills / skill_name / file_name
            
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", response, re.DOTALL)

            if not match:
                return None
            
            frontmatter_raw = match.group(1)
            data = {}
            current_key = None
            for raw_line in frontmatter_raw.splitlines():
                if not raw_line.strip() or raw_line.strip().startswith("#"):
                    continue
        # Continuation line (indented) -> append to the previous key
                if raw_line[:1] in (" ", "\t") and current_key:
                    data[current_key] = (
                        data[current_key] + " " + raw_line.strip()
                    ).strip()
                    continue
        
                if ":" in raw_line:
                    key, _, value = raw_line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # ">" or "|" alone means "block scalar starts on next line" -> not real content
                    if value in (">", "|", ">-", "|-"):
                        value = ""
                    data[key] = value
                    current_key = key
            
            skill_dir = parent_dir / data["name"]
            file_path = skill_dir / Path("SKILL.md")
            try:
                # 3. Create the directories (parents=True creates 'skills' and the skill folder if missing)
                skill_dir.mkdir(parents=True, exist_ok=True)
                
                # 4. Write the file
                file_path.write_text(response, encoding="utf-8")
                
                return f"Successfully created skill file at: {file_path.absolute()}"
            except Exception as e:
                return f"Error creating skill file: {str(e)}"
                    
        print(response)
    