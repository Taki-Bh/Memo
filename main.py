# main.py

from core.context import LLMContext
from providers.chatgpt import ChatGPTProvider
from core.interface import chat
from core.streaming import stream_output
def main():
    chat()
if __name__ == "__main__":
    main()