# providers/browser/chatgpt_page.py

from browser.browser import Browser

from browser.parser import MessageParser
from core.streaming import *


class ChatGPTPage:

    URL = "https://chatgpt.com/"
    USER_INDICATOR = '[class~="corner-superellipse/0.98"]'

    PROMPT_SELECTOR = "#prompt-textarea"
    SUBMIT_SELECTOR = "#composer-submit-button"
    MESSAGE_SELECTOR = "div[data-turn-id-container]"

    def __init__(self):
        self.browser = Browser()

        self.browser.start(headless=False)
        self._open()

    @property
    def page(self):
        return self.browser.page


    def stream_response(self,el):
        return show_streamed_output(el)
    def _open(self):
        try:
            self.browser.goto(
                self.URL,
                timeout=30000
            )
        except ConnectionError:
            raise RuntimeError(
                f"Failed to connect to {self.URL}"
            )

    def send_message(self, prompt: str):
        prompt_input = self.page.locator(self.PROMPT_SELECTOR)

        prompt_input.click()
        prompt_input.fill(prompt)

        self.page.locator(
            self.SUBMIT_SELECTOR
        ).click()

    def get_messages(self):
        return self.page.locator(self.MESSAGE_SELECTOR)

    def get_latest_response(self) -> str:
        messages = self.get_messages()

        wait_for_streaming_output(messages, self.USER_INDICATOR)

        

        if messages.count() == 0:
            return ""
        
        latest = messages.nth(messages.count() - 1)
        lastmsg=self.stream_response(latest)

        return MessageParser.parse_assistant_message(latest,self.USER_INDICATOR)