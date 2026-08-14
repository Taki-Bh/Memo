import json
import re
from typing import Any, Dict, Optional

# Regex to remove citation tokens like \ue200cite...\ue201 or \u200cite...\u2001
CITATION_PATTERN = re.compile(r'[\ue200\u2001]cite[^\ue201\u2001]*[\ue201\u2001]?')


class ChatGPTStreamParser:
    def __init__(self):
        self.messages: Dict[str, str] = {}
        self.active_message_id: Optional[str] = "default"
        # Ensure default key exists in case stream lacks an explicit message ID
        self.messages[self.active_message_id] = ""

    def clean_text(self, text: str) -> str:
        return CITATION_PATTERN.sub('', text)

    def _append_text(self, text: str):
        """Appends cleaned text to the currently active message buffer."""
        cleaned = self.clean_text(text)
        target_id = self.active_message_id or "default"
        if target_id not in self.messages:
            self.messages[target_id] = ""
        self.messages[target_id] += cleaned

    def process_patch(self, patch: Dict[str, Any]):
        """Handles JSON Patch operations (append, replace, patch, remove)."""
        if not isinstance(patch, dict):
            return

        op = patch.get('o')
        path = patch.get('p', '')
        val = patch.get('v')

        # Target message text content parts
        if path == '/message/content/parts/0':
            if op == 'append' and isinstance(val, str):
                self._append_text(val)

    def feed_line(self, line: str):
        """Processes an individual SSE frame line cleanly."""
        line = line.strip()
        if not line or not line.startswith('data:'):
            return

        raw_data = line[5:].strip()

        # Ignore standard SSE control tags
        if raw_data in ('"v1"', '[DONE]'):
            return

        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            return

        if not isinstance(payload, dict):
            return

        v = payload.get('v')

        # --- Message Meta / ID Tracking ---
        if isinstance(v, dict):
            msg_obj = v.get('message')
            if isinstance(msg_obj, dict) and 'id' in msg_obj:
                self.active_message_id = msg_obj['id']
                if self.active_message_id not in self.messages:
                    self.messages[self.active_message_id] = ""

        # --- Case 1: Direct String Chunk -> {"v": "chunk"} ---
        if isinstance(v, str):
            self._append_text(v)

        # --- Case 2: Root Append Op -> {"p": "/message/content/parts/0", "o": "append", "v": "text"} ---
        elif payload.get('o') == 'append' and payload.get('p') == '/message/content/parts/0':
            if isinstance(v, str):
                self._append_text(v)

        # --- Case 3: Patch Array inside "v" -> {"v": [ { "p": "...", "o": "append", ... } ]} ---
        elif isinstance(v, list):
            for patch in v:
                self.process_patch(patch)

        # --- Case 4: Patch Array under root operation -> {"o": "patch", "v": [...] } ---
        elif payload.get('o') == 'patch' and isinstance(v, list):
            for patch in v:
                self.process_patch(patch)

    def get_text(self) -> str:
        """Returns the full parsed text response."""
        return "".join(self.messages.values())

    def feed_text(self, raw_body: str) -> str:
        """Processes an entire raw SSE body string and returns the final response."""
        for line in raw_body.splitlines():
            self.feed_line(line)
        
        return self.get_text()