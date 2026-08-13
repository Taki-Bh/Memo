# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import *
from core.streaming import stream_output,show_streamed_output,wait_for_streaming_output
from browser.browser import Browser
import time
from utilities.utilities import get_sync_llm_msg
from browser.chatgpt_page import ChatGPTPage
class ChatGPTBrowserProvider(LLMProvider):

    def __init__(self, context: LLMContext):
        super().__init__(context)

        self.chat = ChatGPTPage()

    def generate(self, prompt: str) -> str:
        self.append_to_context(("user", prompt))

        self.chat.send_message(prompt)

        response = self.chat.get_latest_response()

        self.append_to_context(("llm", response))
        
        return response

        
