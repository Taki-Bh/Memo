from abc import ABC, abstractmethod
from core.context import LLMContext
from core.skills import build_skill_index
from core.skills import SKILL_INSTRUCTION
class LLMProvider(ABC):

    def __init__(self, context : LLMContext):
        self.context = context
        self.skill_index = build_skill_index()
        #self.generate(SKILL_INSTRUCTION,await_response=False)
    @abstractmethod
    def generate(self,prompt,await_response=True):
        pass
    def append_to_context(self,entry : tuple[str,str]):
        self.context.messages.append((entry))
    def message_exists(self,msg):
        for tup in self.context.messages:
            if (tup[0]=="llm"):
                if (tup[1]==msg):
                    return True
        return False
