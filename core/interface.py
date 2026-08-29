from core.context import LLMContext
from providers.chatgpt.chatgpt import ChatGPTProvider
from providers.gemini.gemini import GeminiProvider
from core.skills import SKILL_INSTRUCTION
import time
from agents.skill_router import SkillRouterAgent
def init_interface():
    context = LLMContext("","", {}, [])

    # Automatically:
    # - uses API if OPENAI_API_KEY exists
    # - uses browser if it doesn't
    llm = GeminiProvider(context)

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
llm = GeminiProvider(context)   
print(f"Using provider: {llm.mode}")
def get_response(user_text:str,await_response=True) -> str:
    return llm.generate(user_text,await_response=await_response)

def launch_in_terminal(user_text:str = "Hello! Give me a one-sentence introduction."):
    print("Morning")
    context = LLMContext("","", {}, [])
 
     # Automatically:
     # - uses API if OPENAI_API_KEY exists
     # - uses browser if it doesn't   
    print("Hello")
    print(f"Using provider: {llm.mode}")
    
   

    
    #llm.generate(SKILL_INSTRUCTION+f"\n Available skills {llm.skill_index}",await_response=False)
    skill_router=SkillRouterAgent(llm)
    while True:
        
        prompt=input("user : ")
        try:
            #response = llm.generate(prompt)
            response=skill_router.handleRequest(prompt)
            if response:

                print("\nResponse:")
                print(response)
                

        except Exception as e:
            print(f"\nError: {type(e).__name__}")
            print(e)
        time.sleep(0.016)
    

