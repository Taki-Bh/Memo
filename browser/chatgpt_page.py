
from core.streaming import *
from browser.llm_page import *
from core.config import *

class ChatGPTPage(LLMPage):
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
    def get_latest_response(self, timeout_ms: int = 60000, await_response : bool = True) -> str:
            
            if not USE_WEB_SCRAPING:
                return self.__super__(timeout_ms,await_response)
            else:
                assistant_msgs = self.page.locator("li[data-message-role='assistant']")
                conversation_box=self.page.locator("ol[aria-label='Conversation']")
                old_msg=""
                msg=""
                idle_counter=0
                t=0
                while True:
                     
                    
                    #print("Assistant messages:", assistant_msgs.count())
                    #print(f"msg = {msg} | old_msg={old_msg}")
                    #if conversation_box.count():
                        #print("Yes COnversation box exists")
                    if assistant_msgs.count():
                        msg=assistant_msgs.last.text_content()
                    if msg.find(':'):
                        msg=msg[msg.find(':')+1:]
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
                        
                    

           


          