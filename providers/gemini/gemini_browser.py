# providers/gemini_browser.py

from core.exceptions import *
from browser.gemini_page import GeminiPage
from core.llm_browser_provider import LLMBrowserProvider
class GeminiBrowserProvider(LLMBrowserProvider):
    def __init__(self, context):
        super().__init__(context)
        self.page = GeminiPage()


        
