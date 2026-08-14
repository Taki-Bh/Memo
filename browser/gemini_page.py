import threading
from core.streaming import *
from browser.llm_page import *
from browser.parser import GeminiStreamParser
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
            response_text = parser.feed_text(text)
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
                show_resp(body_bytes.decode("utf-8", errors="ignore"))
                
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


def extract_llm_response(raw_payload):
    responses = []
    print(raw_payload)
    # Regular expression to target the exact structure where Google's models output text
    # It looks for patterns like: ["rc_...", ["Your response text here"], ...]
    pattern = r'\\*?"rc_[a-zA-Z0-9]+\\*"\\*?,\s*\[\\*"(.*?)\\*"]'   
    # Find all matches, accounting for escaped quotes in raw payloads
    matches = re.findall(pattern, raw_payload)
    print(f"Number of matches found: {len(matches)}")
    for match in matches:
        # Unescape escaped characters (like \\" to ")
        cleaned_text = (
            match.replace('\\"', '"')
            .replace("\\\\", "\\")
            .encode()
            .decode("unicode_escape", errors="ignore")
        )
        # Filter out UI element labels (like "Longer", "Shorter", "Try again")
        ui_noise = ["Longer", "Shorter", "Try again", "expand", "compress"]
        if cleaned_text and cleaned_text not in responses and cleaned_text not in ui_noise:
            responses.append(cleaned_text)

    return responses


# --- Example Usage ---
# Paste your entire raw payload string inside the triple quotes below:

def show_resp(raw_data):

    extracted_messages = extract_llm_response(raw_data)

    print("Extracted LLM Responses:")
    for i, msg in enumerate(extracted_messages, 1):
        print(f"{i}. {msg}")