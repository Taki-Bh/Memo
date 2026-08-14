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






































class GeminiStreamParser:
    """Parses chunked Google Gemini / wrb.fr SSE streaming payloads."""

    def __init__(self):
        self.messages: Dict[str, str] = {}
        self.active_message_id: Optional[str] = "default"
        self.messages[self.active_message_id] = ""

    def _clean_chunk(self, chunk: str) -> str:
        """Strips byte-count prefixes, leading )]}' guard strings, and whitespace."""
        chunk = chunk.strip()
        if chunk.startswith(")]}'"):
            chunk = chunk[4:].strip()
        # Remove leading byte counts like '177\n' or '253\n'
        chunk = re.sub(r"^\d+\s*", "", chunk)
        return chunk

    def _extract_text_from_nested(self, obj) -> str:
        """Recursively walks nested JSON data to extract stream text chunks."""
        text_parts = []

        if isinstance(obj, list):
            # Check for candidate array signature: ["rc_...", ["text chunk"], ...]
            if len(obj) >= 2 and isinstance(obj[0], str) and obj[0].startswith("rc_"):
                text_container = obj[1]
                if isinstance(text_container, list) and len(text_container) > 0:
                    first_val = text_container[0]
                    if isinstance(first_val, str):
                        self.active_message_id = obj[0]
                        return first_val

            for item in obj:
                extracted = self._extract_text_from_nested(item)
                if extracted:
                    text_parts.append(extracted)

        elif isinstance(obj, dict):
            for value in obj.values():
                extracted = self._extract_text_from_nested(value)
                if extracted:
                    text_parts.append(extracted)

        return "".join(text_parts)

    def _process_payload(self, payload: list):
        """Processes a valid wrb.fr JSON array and updates the text state."""
        if len(payload) >= 3 and payload[0] == "wrb.fr":
            raw_inner_data = payload[2]

            # The 3rd element is usually a stringified JSON array
            if isinstance(raw_inner_data, str):
                try:
                    inner_structure = json.loads(raw_inner_data)
                    extracted_text = self._extract_text_from_nested(inner_structure)

                    if extracted_text:
                        target_id = self.active_message_id or "default"
                        # Payload provides cumulative snapshots; update to latest text
                        self.messages[target_id] = extracted_text
                except json.JSONDecodeError:
                    pass

    def feed_line(self, line: str):
        """Processes an individual chunk or line from the wrb.fr payload."""
        cleaned_line = self._clean_chunk(line)
        if not cleaned_line:
            return

        # Fast check if it's a valid JSON block
        if not (cleaned_line.startswith("[") and cleaned_line.endswith("]")):
            return

        try:
            payload = json.loads(cleaned_line)
            if isinstance(payload, list) and len(payload) > 0:
                self._process_payload(payload)
        except json.JSONDecodeError:
            pass

    def feed_text(self, raw_body: str) -> str:
        """Processes an entire raw wrb.fr response payload string robustly."""
        raw_body = raw_body.strip()
        if raw_body.startswith(")]}'"):
            raw_body = raw_body[4:].strip()

        # Robust parsing: Instead of fragile regex splits, we use Python's JSONDecoder 
        # to step through the raw string and pluck out valid arrays, ignoring line breaks entirely.
        decoder = json.JSONDecoder()
        idx = 0
        
        while idx < len(raw_body):
            # Find the next array start
            idx = raw_body.find('[', idx)
            if idx == -1:
                break
                
            try:
                # raw_decode parses the JSON object starting at idx
                # It returns the decoded object and the index distance to where the object ended
                obj, end_idx = decoder.raw_decode(raw_body[idx:])
                
                if isinstance(obj, list) and len(obj) > 0 and obj[0] == "wrb.fr":
                    self._process_payload(obj)
                    
                # Move index forward to where this JSON block ended
                idx += end_idx
            except json.JSONDecodeError:
                # If it wasn't a valid JSON start (e.g. a bracket inside a string), nudge forward
                idx += 1

        return self.get_text()

    def get_text(self) -> str:
        """Returns the parsed text response."""
        return "".join(self.messages.values())