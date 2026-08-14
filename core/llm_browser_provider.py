# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import *
from browser.chatgpt_page import ChatGPTPage
class LLMBrowserProvider(LLMProvider):

    def __init__(self, context: LLMContext):
        super().__init__(context)
        self.page=None


    def generate(self, prompt: str) -> str:
        self.append_to_context(("user", prompt))

        self.page.send_message(prompt)

        response = self.page.get_latest_response()

        self.append_to_context(("llm", response))
        
        return response

        
