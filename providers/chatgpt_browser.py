# providers/chatgpt_browser.py

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import *
from navigator.navigator import navigator
import time
from utilities.utilities import get_sync_llm_msg
class ChatGPTBrowserProvider(LLMProvider):

    def __init__(self, context: LLMContext):
        super().__init__(context)

        self.navigator = navigator
        self.navigator.start(headless=False)
        try:
            self.navigator.goto(
                        "https://chatgpt.com/",timeout=30000
            )
        except ConnectionError as e:
            print("Failed to connect to 'https://chatgpt.com', please verify your connection to the internet. ")
            exit(-1)

    def generate(self, prompt: str) -> str:
        print(f"Generating response for prompt: {prompt}")
        
        prompt_input = navigator.page.locator("#prompt-textarea")
        print(prompt_input.count())
        prompt_input.click()
        prompt_input.fill(prompt)
        submit_btn=navigator.page.locator("#composer-submit-button")
        submit_btn.click()
        
        elements = navigator.page.locator("div[data-turn-id-container]")
        
        self.append_to_context(("user",prompt))
        time.sleep(2)
        count=elements.count()
        print(f"count={count}")
        
        for i in range(0,count):
            """print(f"    i={i}")
            print(f"    count={count}")"""
            
            element = elements.nth(i)
            msg=element.inner_text()
            
            user_msg_indicator = element.locator('[class~="corner-superellipse/0.98"]')
            
            clean_msg=msg[msg.find(':')+1:].strip()
            

            if "ChatGPT" in msg or not user_msg_indicator.count()>0:
                self.message_exists(clean_msg)
                context_entry=("llm",clean_msg)
                self.append_to_context(context_entry)
                if count-1==i:
                   
                    response=get_sync_llm_msg(element)
                #break

            else:
                context_entry=("user",clean_msg)
                self.append_to_context(context_entry)
                if "You" not in msg:
                    print(msg)
                    #raise UnrecognizedMessageFormat("Unexpected message format in DOM")

       
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