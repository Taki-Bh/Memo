import queue
import threading
from browser.browser import Browser
from browser.chatgpt_parser import ChatGPTStreamParser
from core.streaming import *


import json
from bs4 import BeautifulSoup



import html
import json
import queue
from bs4 import BeautifulSoup


def _parse_worker(body_bytes: bytes, response_queue: queue.Queue):
    """
    Runs strictly in a background Python thread.
    Extracts the final assistant message from the HTTP response.
    """
    try:
        text = body_bytes.decode("utf-8", errors="ignore")

        if not text.strip():
            return

        soup = BeautifulSoup(text, "html.parser")

        element = soup.select_one(
            '[data-conversation-control="complete"][data-conversation]'
        )

        if not element:
            return

        # HTML attributes are escaped (&quot;, etc.)
        conversation = json.loads(
            html.unescape(element["data-conversation"])
        )

        # Get the final assistant message
        for message in reversed(conversation.get("messages", [])):
            if message.get("role") == "assistant":
                response_text = message.get("content", "").strip()

                if response_text:
                    response_queue.put(response_text)

                return

    except Exception as err:
        print(f"[Thread Parse Error]: {err}")



class LLMPage:

    URL = "https://chatgpt.com/"
    PROMPT_SELECTOR = "#mobile-composer-prompt"
    SUBMIT_SELECTOR = "button[data-composer-submit]"
   

    def __init__(self):
        self.browser = Browser()
        self.browser.start(headless=False)

        # Thread-safe queue to pass results safely from worker thread to main thread
        self.response_queue = queue.Queue()

        # ✅ Register listener BEFORE opening the page
        self.page.on("response", self.handle_response)

        self._open()

    @property
    def page(self):
        return self.browser.page

    def stream_response(self, el):
        return show_streamed_output(el)

    def _open(self):
        try:
            self.browser.goto(self.URL, timeout=60000)
        except Exception as err:
            raise RuntimeError(f"Failed to connect to {self.URL}: {err}")

    def _clear_queue(self):
        """Purges old or orphaned responses to avoid race conditions."""
        with self.response_queue.mutex:
            self.response_queue.queue.clear()

    def send_message(self, prompt: str):
        
        # Clear out any residual responses from prior prompts
        self._clear_queue()

        prompt_input = self.page.locator(self.PROMPT_SELECTOR)
        prompt_input.click()
        prompt_input.fill(prompt)
        time.sleep(1)  # Allow time for the input to register
        #prompt_input_text=prompt_input.text_content()
        self.page.locator(self.SUBMIT_SELECTOR).click()
                    # Return the prompt text for confirmation

   

    def get_latest_response(self, timeout_ms: int = 60000, await_response : bool = True) -> str:
        """
        Polls the queue while keeping Playwright's event loop alive.
        Prints and returns the parsed response string or raises a TimeoutError.
        """
        print("Listening for response...")
        elapsed = 0
        poll_interval = 100  # ms

        while elapsed < timeout_ms:
            try:
                # Retrieve parsed string from background thread
                retrieved_text = self.response_queue.get_nowait()
                
                # 🖨️ PRINT THE RETRIEVED TEXT HERE
                print("\n=== RETRIEVED TEXT START ===")
                print(retrieved_text)
                print("=== RETRIEVED TEXT END ===\n")
                
                return retrieved_text if await_response else None 
            except queue.Empty:
                # Non-blocking wait keeps Playwright listening to network events
                self.page.wait_for_timeout(poll_interval)
                elapsed += poll_interval

        raise TimeoutError("Timed out waiting for ChatGPT stream response.")
    def handle_request_finished(self, request):
        if "/unauth-mweb/conversation/updates" not in request.url:
            return

        print("CONVERSATION REQUEST FINISHED")

        response = request.response()

        if not response:
            return

        try:
            body = response.body()
            print("BODY:", len(body))

            threading.Thread(
                target=_parse_worker,
                args=(body, self.response_queue),
                daemon=True,
            ).start()

        except Exception as e:
            print("BODY ERROR:", e)
    def handle_response2(self, response):
        if "/unauth-mweb/conversation/updates" not in response.url:
            return
        print("IT IS THE API")
        selec=self.page.wait_for_selector(
            '[data-conversation-control="complete"]',
            timeout=30000
        )
        complete = self.page.locator('[data-conversation-control="complete"]')

        print("DONE")
        print(complete.inner_text())
        if response.status != 200:
            return

        try:
            # IMPORTANT: capture immediately.
            time.sleep(5)
            body = response.body()
            print(body)
            threading.Thread(
                target=_parse_worker,
                args=(body, self.response_queue),
                daemon=True
            ).start()

        except Exception as err:
            print(f"[Stream Intercept Error]: {err}")    

    def handle_response(self, response):
        url = response.url

        # 1. EARLY EXIT: Ignore static assets immediately
        if any(
            url.endswith(ext)
            for ext in (".css", ".js", ".png", ".jpg", ".woff2", ".svg")
        ):
            return

        content_type = response.headers.get("content-type", "")

        # 2. TARGET CHATGPT API ENDPOINTS
        is_chat_api = (
            "backend-api/conversation" in url
            or "backend-anon/f/conversation" in url
            or "/conversation" in url

        )
        is_sse = "text/event-stream" in content_type

        if is_chat_api or is_sse:
            print("YES CHAT API")
            try:
                # Filter out OPTIONS preflights and error codes
                if response.status != 200:
                    return

                # ⚠️ MUST read body bytes ON THE MAIN THREAD before spawning a worker
                body_bytes = response.body()

                # Spawn background thread strictly for text parsing/decoding
                worker = threading.Thread(
                    target=_parse_worker,
                    args=(body_bytes, self.response_queue),
                    daemon=True,
                )
                worker.start()

            except Exception as err:
                print(f"[Stream Intercept Error]: {err}")