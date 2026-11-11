import json
import re
from typing import Any, Dict, Optional















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

    def extract_llm_response(self,raw_payload):
        responses = []
        print(raw_payload)
        # Regular expression to target the exact structure where Google's models output text
        # It looks for patterns like: ["rc_...", ["Your response text here"], ...]
        pattern = r'\\*?"rc_[a-zA-Z0-9]+\\*"\\*?,\s*\[\\*"(.*?)\\*"]'   
        # Find all matches, accounting for escaped quotes in raw payloads
        matches = re.findall(pattern, raw_payload)
        print(f"Number of matches found: {len(matches)}")
        for match in matches:
            # Unescape escaped characters (like \\" to ")
            cleaned_text = (
                match.replace('\\"', '"')
                .replace("\\\\", "\\")
                .encode()
                .decode("unicode_escape", errors="ignore")
            )
            # Filter out UI element labels (like "Longer", "Shorter", "Try again")
            ui_noise = ["Longer", "Shorter", "Try again", "expand", "compress"]
            if cleaned_text and cleaned_text not in responses and cleaned_text not in ui_noise:
                responses.append(cleaned_text)

        return responses[len(responses) - 1] if responses else ""
   

    def get_text(self) -> str:
        """Returns the parsed text response."""
        return "".join(self.messages.values())