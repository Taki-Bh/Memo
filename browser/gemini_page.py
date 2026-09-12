import threading
from core.streaming import *
from browser.llm_page import *
from browser.gemini_parser import GeminiStreamParser
from core.config import *
import re
def _parse_worker(body_bytes: bytes, response_queue: queue.Queue):
    """
    Runs strictly in a background Python thread.
    Parses and cleans the SSE stream text without touching Playwright objects.
    """
    try:
        text = body_bytes.decode("utf-8", errors="ignore")
        
        if text.strip():
            parser = GeminiStreamParser()
            response_text = parser.extract_llm_response(text)
            if response_text.strip():
                # Put cleaned result into the thread-safe queue
                response_queue.put(response_text)
    except Exception as err:
        print(f"[Thread Parse Error]: {err}")
class GeminiPage(LLMPage):
    URL = "https://gemini.google.com/"
    # Updated selectors based on your UI breakdown
    PROMPT_SELECTOR = '.ql-editor'
    SUBMIT_SELECTOR = 'gem-icon-button.send-button'
    def __init__(self):
                self.browser = Browser()
                self.browser.start(headless=False)
        
                # Thread-safe queue to pass results safely from worker thread to main thread
                self.response_queue = queue.Queue()
        
                # ✅ Register listener BEFORE opening the page
                if not USE_WEB_SCRAPING:
                    self.page.on("response", self.handle_response)
                else:
                    print("USING WEB SCRAPING")
                self._open()
    def send_message(self, prompt: str):
        
        # Clear out any residual responses from prior prompts
        self._clear_queue()

        prompt_input = self.page.locator(self.PROMPT_SELECTOR)
        prompt_input.click()
        prompt_input.fill(prompt)
        prompt_input_text=prompt_input.text_content()
        i=0
        if len(prompt_input_text)!=len(prompt):
            print(f"Prompt length mismatch: {len(prompt_input_text)} vs {len(prompt)}")
            print(f"Prompt input text: {prompt_input_text}")
            print(f"Original prompt: {prompt}")
            while True:
                
                text_header=f"You are recieving a file in batches (Refrain from return a call/state block until the batches are done/ any call/state block will be ignored) : [batch {i}]:\n"
                text_batch_size=len(prompt_input_text)-len(text_header)
                text_batch=text_header+prompt[i*text_batch_size:min((i+1)*text_batch_size,len(prompt))]
                
                prompt_input.fill(text_batch)
                time.sleep(0.5)
                
                self.page.locator(self.SUBMIT_SELECTOR).click()
                if (i+1)*text_batch_size>=len(prompt):
                    break
                self.get_latest_response(timeout_ms=1000, await_response=False)
                
                i+=1
          # Allow time for the input to register
        else:
            time.sleep(0.5)
            self.page.locator(self.SUBMIT_SELECTOR).click()
                    # Return the prompt text for confirmation

    def handle_response(self, response):
        url = response.url
        #print(response.url)
        # 1. Early exit on non-200 or static extensions
        if response.status != 200:
            return

        if any(url.endswith(ext) for ext in (".css", ".js", ".png", ".jpg", ".woff2", ".svg", ".ico")):
            return

        # 2. Filter strictly for Gemini batchexecute / chat endpoints
        #or "batchexecute"
        if "https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate" in url  in url:
            #print("YES IT IS")
            try:
                body_bytes = response.body()
                with open("response_body.txt", "wb") as f:
                   f.write(body_bytes)
                   print("Response body written to response_body.txt")
                
                
                # Spawn worker thread to parse body_bytes
                worker = threading.Thread(
                    target=_parse_worker,
                    args=(body_bytes, self.response_queue),
                    daemon=True,
                )
                worker.start()
            except Exception as err:
                # Playwright API errors when body is missing/cancelled
                pass
            except Exception as err:
                print(f"[Stream Intercept Error]: {err}")
    def get_latest_response(self, timeout_ms: int = 60000, await_response : bool = True) -> str:
                
                if not USE_WEB_SCRAPING:
                    return self.__super__(timeout_ms,await_response)
                else:
                    assistant_msgs = self.page.locator("response-container")
                    conversation_box=self.page.locator("ol[aria-label='Conversation']")
                    old_msg=""
                    msg=""
                    idle_counter=0
                    t=0
                    while True:
                        
                        
                        #print("Assistant messages:", assistant_msgs.count())
                        #if assistant_msgs:
                            # print("Assistant message:", assistant_msgs.last.text_content())
                             
                        #print(f"msg = {msg} | old_msg={old_msg}")
                        #if conversation_box.count():
                            #print("Yes COnversation box exists")
                        if assistant_msgs.count():
                            msg=assistant_msgs.last.text_content()
                    
                        if msg.find('said') > -1:

                           # print(f"Parsed message:{msg[msg.find('said')+5:]}")
                            
                            msg=msg[msg.find('said')+5:]
                            if msg.lower().find("searching the web")!=-1:
                                time.sleep(1)
                                continue
                            if msg==old_msg:
                                idle_counter+=1
                            else:
                                old_msg=msg
                                idle_counter=0
                            if idle_counter>MSG_TIMEOUT*60 and msg=="" :
                                return None
                            if msg !="" and idle_counter>MSG_CHECK_DUR*60:
                                #print(f"Assistant said: {msg}")
                                #input()
                                return msg                            



                        time.sleep(0.016)
                        t+=0.016
                        #print(f"elapsed time={t}")



# --- Example Usage ---
# Paste your entire raw payload string inside the triple quotes below:

"""def show_resp(raw_data):

    extracted_messages = extract_llm_response(raw_data)

    print("Extracted LLM Responses:")
    for i, msg in enumerate(extracted_messages, 1):
        print(f"{i}. {msg}")"""