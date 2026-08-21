from pathlib import Path
from agents.skills_prompts import *
from agents.skill_execution_loop import *
import json
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

