# providers/browser/chatgpt_page.py

import time
from browser.browser import Browser
from core.streaming import *
from browser.parser import ChatGPTStreamParser


def handle_response(response):
    url = response.url
    
    # 1. EARLY EXIT: Filter out static assets immediately
    # Ignore images, CSS, JS, fonts, telemetry, and tracking endpoints
    if any(url.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".woff2", ".svg")):
        return

    content_type = response.headers.get("content-type", "")

    # 2. TARGET CHATGPT API ENDPOINTS
    # ChatGPT streams specifically via backend-api/conversation
    is_chat_api = "backend-api/conversation" in url or "/conversation" in url
    is_sse = "text/event-stream" in content_type
    is_conversation = url== "https://chatgpt.com/backend-anon/f/conversation"
    if is_chat_api or is_sse:
        try:
            # Check response status
            if response.status != 200:
                return

            body = response.body()
            text = body.decode("utf-8", errors="ignore")

            if text.strip():
                print(f"\n🔗 Intercepted Stream: {url}, is_conversation: {is_conversation},\n--- STREAM START ---")
                if is_conversation:
                    parser = ChatGPTStreamParser()
                        
                    for line in text.splitlines():
                            parser.feed_line(line)

                    print("Captured Messages:", parser.messages)
                    print("--- STREAM END ---\n")

        except Exception as err:
            print(f"[Stream Intercept Error]: {err}")


class ChatGPTPage:

    URL = "https://chatgpt.com/"
    USER_INDICATOR = '[class~="corner-superellipse/0.98"]'

    PROMPT_SELECTOR = "#prompt-textarea"
    SUBMIT_SELECTOR = "#composer-submit-button"
    MESSAGE_SELECTOR = "div[data-turn-id-container]"

    def __init__(self):
        self.browser = Browser()
        self.browser.start(headless=False)

        # ✅ REGISTER FIRST before opening the page!
        self.page.on("response", handle_response)

        # Now open page
        self._open()

    @property
    def page(self):
        return self.browser.page

    def stream_response(self, el):
        return show_streamed_output(el)

    def _open(self):
        try:
            self.browser.goto(self.URL, timeout=30000)
        except Exception as err:
            raise RuntimeError(f"Failed to connect to {self.URL}: {err}")

    def send_message(self, prompt: str):
        prompt_input = self.page.locator(self.PROMPT_SELECTOR)
        prompt_input.click()
        prompt_input.fill(prompt)

        self.page.locator(self.SUBMIT_SELECTOR).click()

    def get_messages(self):
        return self.page.locator(self.MESSAGE_SELECTOR)

    def get_latest_response(self) -> str:
        print("Listening for response...")
        # Note: If testing manually in browser, time.sleep gives you time to type/interact
        self.page.wait_for_timeout(300000)
        return None