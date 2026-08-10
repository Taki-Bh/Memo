from dataclasses import dataclass
from typing import Any

@dataclass
class LLMContext:
    instruction:str
    goal: str
    variables: dict[str, Any] 
    messages: list[dict[str, str]] 