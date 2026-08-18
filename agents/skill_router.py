from core.agent import Agent
from core.provider import LLMProvider
from core.skills import *
import json
import re
import time
from pathlib import Path

ROUTER_PROMPT = """
=== STAGE 1: SKILL ROUTER PROMPT ===

## Role
You are a Skill Router Agent. Your sole purpose is to classify the user's request against a Skill Index (and any in-progress skill execution) and return a routing decision. You do not solve tasks and you do not have skill instructions loaded yet.

## Task
Analyze the user's request and choose exactly ONE of these four outcomes:

1. **MATCH** — the request matches an existing skill's trigger conditions and there is no in-progress execution to resume.
2. **CONTINUE** — there is an in-progress skill execution (see State below) and the user's message is a continuation of it (e.g. "continue", "next", an answer to a question it asked) rather than a new unrelated request.
3. **DRAFT** — no existing skill matches, but the request represents a repeatable capability worth turning into a new skill.
4. **DIRECT** — no existing skill matches and this is an ordinary one-off request that doesn't warrant a new skill.

## Constraints
- Do not attempt to solve the user's task.
- Do not explain your reasoning.
- Output must be a single JSON object and nothing else — no markdown code fences, no prose before or after it.

## Output Format

MATCH:
{"action": "load_skill", "path": "path/to/skill_file.md"}

CONTINUE:
{"action": "continue_skill", "path": "path/to/skill_file.md"}

DRAFT:
{"action": "draft_new_skill", "suggested_name": "kebab-case-name"}

DIRECT:
{"action": "respond_directly"}

## Skill Index
{{SKILL_INDEX_JSON}}

## In-Progress Skill State (null if none)
{{SKILL_STATE_JSON}}

## User Request
{{USER_PROMPT}}

## External Runner Invocation

The `workspace.*` functions are not directly exposed as native assistant tools. They are invoked through an executable `<call-block>` handoff.

When a skill requires a workspace operation, you MUST emit the corresponding `<call-block>` instead of saying the operation is unavailable.

The runner will execute the call-block and return the result in a subsequent turn.

Valid format:

<call-block>
{
  "tool_path": "workspace.write_file",
  "function_name": "write_file",
  "argv": ["path", "content"],
  "argc": 2
}
</call-block>

For `read_file`:

<call-block>
{
  "tool_path": "workspace.read_file",
  "function_name": "read_file",
  "argv": ["path"],
  "argc": 1
}
</call-block>

For `file_exists`:

<call-block>
{
  "tool_path": "workspace.file_exists",
  "function_name": "file_exists",
  "argv": ["path"],
  "argc": 1
}
</call-block>

For `run_python`:

<call-block>
{
  "tool_path": "workspace.run_python",
  "function_name": "run_python",
  "argv": ["script_path", "arg1", "arg2"],
  "argc": 3
}
</call-block>

Treat the emitted call-block as an actual request to the external runner, not as ordinary text or an example.

After emitting a call-block, do not claim that the operation succeeded until the runner returns its result.
"""

"""Do not claim that an operation was performed until the external runner
returns its result.
The external runner will execute the call-block and provide the result
in the next turn. After receiving the result, continue the loaded skill
from the returned result.

If a required operation cannot be performed by an available tool, state
that persistence/execution is unavailable and mark the skill state as
blocked.

For security, only permit operations inside the configured workspace."""
LOAD_PROMPT = """
=== STAGE 2a: SKILL EXECUTION PROMPT ===

## Role
You are now a {{SKILL_NAME}} Specialist, operating strictly under the loaded skill's instructions.

## Loaded Skill Instructions
{{SKILL_MD_CONTENT}}

## Resume State (null if this is a fresh start)
{{SKILL_STATE_JSON}}

## Original User Task
{{ORIGINAL_USER_PROMPT}}

## Constraints
- If the skill contains steps, execute one step a time, skipping one brings failure (And you may proceed to the next step by recieving "continue" at the next user prompt).
- Follow the skill's workflow, constraints, and output format exactly. Do not deviate.
- If Resume State is present, pick up from where it left off rather than restarting the skill.
- You have no  ability to save, upload, or persist files unless a real tool/function result is explicitly provided to you in this call. Never narrate an attempt, an error, or a failure for an action you were not actually given a tool to perform. If persistence is needed, state once, plainly, that it's outside what you can do here, and output the content instead.
- Do not mention the router, the skill index, or the loading process. Respond only with the task output the skill defines.
- If this skill spans multiple turns (it will pause and ask the user something, or clearly isn't finished after this turn), you MUST end your response with a state block in exactly this form:
-- The <call-block> is an executable handoff to my external skill runner: whenever the loaded skill requires running a script or module, emit the required <call-block> with the exact tool_path, function_name, argv, and argc so my runner can execute it and return the result; do not treat the absence of a native tool as a reason to skip the call.
<skill_state>
{"skill_path": "path/to/skill.md", "last_checkpoint": "short_label", "status": "in_progress|awaiting_user_input|blocked|done", "last_question_to_user": "... or null", "context": {}}
</skill_state>
<call-block>
{tool_path: "path/to/module.py", "function_name": "name of the function as provided by the skill" ,"argv":"argv" ,"argc" :"argc"}
</call-block>
  Use "done" once the skill's task is fully complete — this clears the state so it won't be resumed next turn. If the skill completes fully in this single turn, you may omit the block entirely.

## Output
Provide the final result as defined by the skill instructions, followed by the state block and the call block if applicable.
"""


DRAFT_PROMPT = """
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
2. Then the actual task output, if applicable.
"""


REQUIRED_STATE_KEYS = {"skill_path", "last_checkpoint", "status"}
VALID_STATUSES = {"in_progress", "awaiting_user_input", "blocked", "done"}


class StateStore:
    """Minimal per-session state persistence. Swap for redis/db as needed."""

    def __init__(self, path: Path = Path(".skill_state")):
        self.path = path
        self.path.mkdir(exist_ok=True)

    def _file(self, session_id: str) -> Path:
        return self.path / f"{session_id}.json"

    def get(self, session_id: str):
        f = self._file(session_id)
        if not f.exists():
            return None
        try:
            state = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not REQUIRED_STATE_KEYS.issubset(state) or state.get("status") not in VALID_STATUSES:
            return None
        return state

    def set(self, session_id: str, state: dict):
        self._file(session_id).write_text(json.dumps(state), encoding="utf-8")

    def clear(self, session_id: str):
        f = self._file(session_id)
        if f.exists():
            f.unlink()


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


class SkillRouterAgent(Agent):
    def __init__(self, provider: LLMProvider):
        super().__init__(provider)
        self.skill_index_json = json.dumps(provider.skill_index)
        self.state_store = StateStore()

    def handleRequest(self, prompt: str, session_id: str = "default"):
        state = self.state_store.get(session_id)

        # Build the router prompt fresh every call — never mutate a shared template.
        router_prompt = (
            ROUTER_PROMPT
            .replace("{{SKILL_INDEX_JSON}}", self.skill_index_json)
            .replace("{{SKILL_STATE_JSON}}", json.dumps(state) if state else "null")
            .replace("{{USER_PROMPT}}", prompt)
        )

        raw = self.provider.generate(router_prompt)
        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            return f"Router returned invalid JSON: {raw!r}"

        action = response.get("action")

        if action == "respond_directly":
            return self.provider.generate(prompt)

        if action == "load_skill" or action == "continue_skill":
            path = response.get("path")
            skill = fetch_skill(path)
            if not skill:
                return f"Router pointed at unknown skill path: {path!r}"

            resume_state = state if action == "continue_skill" else None
            load_prompt = (
                LOAD_PROMPT
                .replace("{{SKILL_NAME}}", skill.get("name", "Unknown"))
                .replace("{{SKILL_MD_CONTENT}}", skill.get("body", ""))
                .replace("{{SKILL_STATE_JSON}}", json.dumps(resume_state) if resume_state else "null")
                .replace("{{ORIGINAL_USER_PROMPT}}", prompt)
            )

            time.sleep(5)
            raw_response = self.provider.generate(load_prompt)
            new_state, cleaned_response = extract_skill_state(raw_response)

            if new_state and new_state["status"] == "done":
                self.state_store.clear(session_id)
            elif new_state:
                self.state_store.set(session_id, new_state)
            else:
                # No state block — treat as a single-turn completion.
                self.state_store.clear(session_id)

            if skill.get("name") == "skill-creator":
                parent_dir = Path("skills")
                data = parse_frontmatter_content(cleaned_response)
                skill_dir = parent_dir / data["name"]
                file_path = skill_dir / "SKILL.md"
                try:
                    skill_dir.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(cleaned_response, encoding="utf-8")
                    return f"Successfully created skill file at: {file_path.absolute()}"
                except Exception as e:
                    return f"Error creating skill file: {str(e)}"

            return cleaned_response

        if action == "draft_new_skill":
            draft_prompt = (
                DRAFT_PROMPT
                .replace("{{SKILL_CREATOR_MD_CONTENT}}", fetch_skill("skills/skill-creator/SKILL.md").get("body", ""))
                .replace("{{ORIGINAL_USER_PROMPT}}", prompt)
                .replace("{{SUGGESTED_NAME}}", response.get("suggested_name", ""))
            )
            raw_response = self.provider.generate(draft_prompt)
            return raw_response

        return f"Unknown router action: {action!r}"