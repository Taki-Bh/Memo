# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from navigator.navigator import navigator


class ChatGPTBrowserProvider(LLMProvider):

    def __init__(self, context: LLMContext):
        super().__init__(context)

        self.navigator = navigator

    def generate(self, prompt: str) -> str:
        self.navigator.start(headless=False)

        self.navigator.goto(
            "https://chatgpt.com/"
        )
        prompt_input = navigator.page.locator("#prompt-textarea")
        prompt_input.fill("Sigma Sigma boi")
        submit_btn=navigator.page.locator("#composer-submit-button")
        submit_btn.click()
        elements = navigator.page.locator("[data-turn-id-container]")

        # Your Playwright automation goes here.
        #
        # Example:
        #
        # self.navigator.page
        #     .locator(...)
        #     .fill(prompt)
        #
        # response = ...

        return response