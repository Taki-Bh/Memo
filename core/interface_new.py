import time

from core.context import LLMContext
from providers.chatgpt.chatgpt import ChatGPTProvider
from providers.gemini.gemini import GeminiProvider
from agents.skill_router import SkillRouterAgent
from logging import warn


class CommandParser:
    """Parses slash commands entered by the user."""

    AGENT_COMMAND = "/agent"

    @classmethod
    def parse(cls, text: str) -> tuple[str | None, str]:
        text = text.strip()

        if not text:
            return None, ""

        if text.startswith(cls.AGENT_COMMAND):
            prompt = text[len(cls.AGENT_COMMAND):].strip()

            if not prompt:
                raise ValueError(
                    "Usage: /agent <prompt>"
                )

            return cls.AGENT_COMMAND, prompt

        return None, text


class Assistant:
    """
    Main interface between the GUI and the AI system.

    The GUI only needs to call:

        assistant.send("Hello")
        assistant.send("/agent analyze my project")
    """

    def __init__(self):
        self.context = LLMContext("", "", {}, [])

        # Provider automatically chooses its available mode.
        self.llm = ChatGPTProvider(self.context)

        # Agent responsible for routing requests to skills/agents.
        self.agent_router = SkillRouterAgent(self.llm)

        print(f"Using provider: {self.llm.mode}")

    def send(self, user_text: str, await_response: bool = True) -> str:
        """
        Process a message from the user.

        Normal message:
            "Tell me about my project"

        Agent command:
            "/agent analyze my project"
        """

        command, prompt = CommandParser.parse(user_text)

        if command == CommandParser.AGENT_COMMAND:
            resp=self._send_to_agent(
                prompt,
                await_response=await_response
            )
            return resp

        return self._send_to_llm(
            prompt,
            await_response=await_response
        )

    def _send_to_llm(
        self,
        prompt: str,
        await_response: bool = True
    ) -> str:
        """Send a normal conversation message to the LLM."""

        return self.llm.generate(
            prompt,
            await_response=await_response
        )

    def _send_to_agent(
        self,
        prompt: str,
        await_response: bool = True
    ) -> str:
        """Send an explicit agent request to the agent router."""

        return self.agent_router.handleRequest(prompt)


class TerminalInterface:
    """Simple terminal interface for testing the Assistant."""

    def __init__(self, assistant: Assistant):
        self.assistant = assistant

    def run(self):
        print("AI Assistant")
        print(f"Provider: {self.assistant.llm.mode}")
        print()
        print("Commands:")
        print("  /agent <prompt>  → send request to agent router")
        print("  /quit             → exit")
        print()

        while True:
            try:
                prompt = input("user : ").strip()

                if not prompt:
                    continue

                if prompt == "/quit":
                    print("Goodbye!")
                    break

                response = self.assistant.send(prompt)

                if response:
                    print("\nResponse:")
                    print(response)
                    print()

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

            except Exception as e:
                print(f"\nError: {type(e).__name__}")
                print(e)

            time.sleep(0.016)
class GUIInterface:
    """Placeholder for a future GUI interface implementation."""

    def __init__(self, assistant: Assistant = None):
        self.assistant = assistant or Assistant()

    def run(self,prompt):
        print("GUI interface handling")  
        print("AI Assistant")
        print(f"Provider: {self.assistant.llm.mode}")
        print()
        print("Commands:")
        print("  /agent <prompt>  → send request to agent router")
        print("  /quit             → exit")
        print()
       
        prompt = prompt.strip()

        if not prompt:
                    warn("No prompt provided.")
                    return "No prompt provided."

        if prompt == "/quit":
                    print("Goodbye!")
                    return "Goodbye!"
                    

        response = self.assistant.send(prompt)

        if response:
                    print("\nResponse:")
                    print(response)
                    print()
        return response


def start_interface(on_terminal=True):
    assistant = Assistant()
    terminal = TerminalInterface(assistant)
    if on_terminal:
        terminal.run()
    else:
        print("GUI interface handling.")




if __name__ == "__main__":
    start_interface()