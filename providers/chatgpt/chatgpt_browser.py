# providers/chatgpt_browser.py

from core.exceptions import *
from browser.chatgpt_page import ChatGPTPage
from core.llm_browser_provider import LLMBrowserProvider
class ChatGPTBrowserProvider(LLMBrowserProvider):
    def __init__(self, context):
        super().__init__(context)
        self.page = ChatGPTPage()


        
