# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import *
from providers.chatgpt.chatgpt_page import ChatGPTPage
class LLMBrowserProvider(LLMProvider):

    def __init__(self, context: LLMContext):
        super().__init__(context)
        self.page=None


    def generate(self, prompt: str,await_response=True) -> str:
        self.append_to_context(("user", prompt))
        try:
            self.page.send_message(prompt)
        except Exception as e:
            raise LLMRequestError(f"Failed to send msg : {e} ")
        
        response = self.page.get_latest_response(await_response=await_response)
       
            
        self.append_to_context(("llm", response))
        
        return response

        
