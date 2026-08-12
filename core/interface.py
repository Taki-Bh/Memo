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
def chat():
    context = LLMContext("","", {}, [])
 
     # Automatically:
     # - uses API if OPENAI_API_KEY exists
     # - uses browser if it doesn't
    llm = ChatGPTProvider(context)   
    print(f"Using provider: {llm.mode}")
    while True:
        prompt=input("user : ")
        try:
            response = llm.generate(
                prompt
            )

            print("\nResponse:")
            

        except Exception as e:
            print(f"\nError: {type(e).__name__}")
            print(e)
        
    

