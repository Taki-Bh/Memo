from abc import ABC, abstractmethod
from context import LLMContext

class LLMProvider(ABC):

    def __init__(self, context : LLMContext):
        self.context = context

    @abstractmethod
    def generate(self):
        pass
