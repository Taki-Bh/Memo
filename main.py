# main.py

from core.context import LLMContext
from providers.chatgpt import ChatGPTProvider


def main():
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
    input()

if __name__ == "__main__":
    main()