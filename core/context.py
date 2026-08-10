from dataclasses import dataclass
from typing import Any,field

@dataclass
class LLMContext:
    instruction:str
    goal: str
    variables: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)