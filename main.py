# main.py

from core.context import LLMContext
from providers.chatgpt import ChatGPTProvider
from core.interface import chat

def main():
    chat()
if __name__ == "__main__":
    main()