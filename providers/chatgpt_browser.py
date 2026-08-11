# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import UnrecognizedMessageFormat
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
        input("Give Order")
        elements = navigator.page.locator("div[data-turn-id-container]")
        count=elements.count()
        self.append_to_context(("user",prompt))
        for i in range(1,count):
            print(f"    i={i}")
            print(f"    count={count}")

            element = elements.nth(i)
            msg=element.inner_text()
            
            user_msg_indicator = element.locator('[class~="corner-superellipse/0.98"]')

        
            if "ChatGPT" in msg or not user_msg_indicator.count()>0:
                clean_msg=msg[msg.find(':')+1:].strip()
                self.message_exists(clean_msg)
                context_entry=("llm",clean_msg)
                self.append_to_context(context_entry)
                #break

            else:
                if "You" not in msg:
                    print(msg)
                    #raise UnrecognizedMessageFormat("Unexpected message format in DOM")

        print(self.context.messages)
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