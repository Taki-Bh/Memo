from abc import ABC, abstractmethod
from core.context import LLMContext
class LLMProvider(ABC):

    def __init__(self, context : LLMContext):
        self.context = context

    @abstractmethod
    def generate(self):
        pass
    def append_to_context(self,entry : tuple[str,str]):
        self.context.messages.append((entry))
    def message_exists(self,msg):
        for tup in self.context.messages:
            if (tup[0]=="llm"):
                if (tup[1]==msg):
                    return True
        return False
