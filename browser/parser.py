# providers/browser/message_parser.py
import json
import re
from typing import Any, Dict
from playwright.async_api import async_playwright

# Regex to remove citation tokens like \ue200cite...\ue201 or \u200cite...\u2001
CITATION_PATTERN = re.compile(r'[\ue200\u2001]cite[^\ue201\u2001]*[\ue201\u2001]?')


class ChatGPTStreamParser:
    def __init__(self):
        self.messages: Dict[str, str] = {}
        self.active_message_id = None

    def clean_text(self, text: str) -> str:
        return CITATION_PATTERN.sub('', text)

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
                cleaned = self.clean_text(val)
                print(cleaned, end='', flush=True)
                if self.active_message_id and self.active_message_id in self.messages:
                    self.messages[self.active_message_id] += val

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
            cleaned = self.clean_text(v)
            print(cleaned, end='', flush=True)

        # --- Case 2: Root Append Op -> {"p": "/message/content/parts/0", "o": "append", "v": "text"} ---
        elif payload.get('o') == 'append' and payload.get('p') == '/message/content/parts/0':
            if isinstance(v, str):
                cleaned = self.clean_text(v)
                print(cleaned, end='', flush=True)

        # --- Case 3: Patch Array inside "v" -> {"v": [ { "p": "...", "o": "append", ... } ]} ---
        elif isinstance(v, list):
            for patch in v:
                self.process_patch(patch)

        # --- Case 4: Patch Array under root operation -> {"o": "patch", "v": [...] } ---
        elif payload.get('o') == 'patch' and isinstance(v, list):
            for patch in v:
                self.process_patch(patch)
