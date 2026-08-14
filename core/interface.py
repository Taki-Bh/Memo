from core.context import LLMContext
from providers.chatgpt import ChatGPTProvider
import time
def init_interface():
    context = LLMContext("","", {}, [])

    # Automatically:
    # - uses API if OPENAI_API_KEY exists
    # - uses browser if it doesn't
    llm = ChatGPTProvider(context)

    print(f"Using provider: {llm.mode}")

    try:
        response = llm.generate(
            "Hello! Give me a one-sentence introduction."
        )

        print("\nResponse:")
        print(response)

    except Exception as e:
        print(f"\nError: {type(e).__name__}")
        print(e)
context = LLMContext("","", {}, [])
 
     # Automatically:
     # - uses API if OPENAI_API_KEY exists
     # - uses browser if it doesn't
llm = ChatGPTProvider(context)   
print(f"Using provider: {llm.mode}")
def get_response(user_text:str):
    return llm.generate(user_text)

def launch_in_terminal(user_text:str = "Hello! Give me a one-sentence introduction."):
    print("Morning")
    context = LLMContext("","", {}, [])
 
     # Automatically:
     # - uses API if OPENAI_API_KEY exists
     # - uses browser if it doesn't   
    print("Hello")
    print(f"Using provider: {llm.mode}")
    
   

        
    while True:
        
        prompt=input("user : ")
        try:
            response = llm.generate(
                prompt
            )

            print("\nResponse:")
            print(response)
            

        except Exception as e:
            print(f"\nError: {type(e).__name__}")
            print(e)
        time.sleep(0.016)
    

