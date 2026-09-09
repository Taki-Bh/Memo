import time
from datetime import datetime

from core.context import LLMContext
from providers.chatgpt.chatgpt import ChatGPTProvider
from providers.gemini.gemini import GeminiProvider
from agents.skill_router import SkillRouterAgent
from logging import warn
from PyQt6.QtCore import QObject, pyqtSignal


class CommandParser:
    """Parses slash commands entered by the user."""

    AGENT_COMMAND = "/agent"
    SWAP_COMMAND = "/swap"
    SAVE_COMMAND = "/save"
    TITLE_COMMAND = "/title"

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

        if text.startswith(cls.SWAP_COMMAND):
            provider_name = text[len(cls.SWAP_COMMAND):].strip().lower()
            return cls.SWAP_COMMAND, provider_name

        if text.startswith(cls.SAVE_COMMAND):
            filename = text[len(cls.SAVE_COMMAND):].strip()
            return cls.SAVE_COMMAND, filename

        return None, text


class Assistant():
    """
    Main interface between the GUI and the AI system.

    The GUI only needs to call:

        assistant.send("Hello")
        assistant.send("/agent analyze my project")
    """

    def __init__(self):
        self.context = LLMContext("", "", {}, [])
        self.conversation_name = "Untitled Entity"
        self.conversation_date = datetime.now().isoformat()

        # Provider automatically chooses its available mode.
        self.llm = GeminiProvider(self.context)
        providerChanged = pyqtSignal(str)
        # Agent responsible for routing requests to skills/agents.
        self.agent_router = SkillRouterAgent(self.llm)

        print(f"Using provider: {self.llm.name}")

    def swap_provider(self, provider_name: str) -> str:
        """Swap the LLM provider between chatgpt and gemini."""
        provider_name = provider_name.strip().lower()
        if provider_name in ["chatgpt", "gpt", "openai"]:
            self.llm = ChatGPTProvider(self.context)
            self.agent_router = SkillRouterAgent(self.llm)
            
        elif provider_name in ["gemini", "google"]:
            self.llm = GeminiProvider(self.context)
            self.agent_router = SkillRouterAgent(self.llm)
        else:
            return f"Unknown provider '{provider_name}'. Available providers: chatgpt, gemini"
        
        # Update the router's llm reference
        self.agent_router.llm = self.llm
        return f"Successfully switched provider to: {self.llm.name}"

    def suggest_and_set_title(self) -> str:
        """Ask the LLM to suggest a short entity name for the current conversation."""
        if not self.context.messages:
            return "No conversation history to name yet."
        
        prompt = (
            "Based on the conversation so far, suggest a short, descriptive, concise entity name/title "
            "(maximum 5 words, no quotes, no punctuation at the end). Return ONLY the name."
        )
        try:
            suggested = self.llm.generate(prompt, await_response=True)
            if suggested:
                self.conversation_name = suggested.strip()
                return f"Conversation entity name set to: '{self.conversation_name}'"
        except Exception as e:
            return f"Error generating name: {e}"
        return "Could not generate a name."

    def save_conversation(self, filename: str = "") -> str:
        """Save the conversation entity (name, date, messages) to memory/conversations.json or specified file."""
        import json
        from pathlib import Path

        target = Path(filename) if filename else Path("memory/conversations.json")

        new_entity = {
            "name": self.conversation_name,
            "date": self.conversation_date,
            "messages": [{"role": role, "content": content} for role, content in self.context.messages]
        }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)

            # Load existing data if the file already exists and is valid
            if target.exists():
                try:
                    with open(target, "rt") as f:
                        data = json.load(f)
                    if not isinstance(data, dict) or "entities" not in data:
                        data = {"entities": []}
                except (json.JSONDecodeError, OSError):
                    data = {"entities": []}
            else:
                data = {"entities": []}

            data["entities"].append(new_entity)

            with open(target, "wt") as f:
                json.dump(data, f, indent=2)

            return f"Successfully saved conversation entity '{self.conversation_name}' to {target}"
        except Exception as e:
            return f"Error saving conversation: {e}"

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
            resp = self._send_to_agent(
                prompt,
                await_response=await_response
            )
            return resp

        if command == CommandParser.SWAP_COMMAND:
            return self.swap_provider(prompt)

        if command == CommandParser.SAVE_COMMAND:
            # Automatically suggest a name if not explicitly set or on save
            if self.conversation_name == "Untitled Entity" and self.context.messages:
                self.suggest_and_set_title()
            return self.save_conversation(prompt)

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
        print("  /swap <provider> → swap provider (chatgpt/gemini)")
        print("  /save [path]     → save conversation entity to json")
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

            time.sleep(0.016)


class GUIInterface:
    """Placeholder for a future GUI interface implementation."""

    def __init__(self, assistant: Assistant = None):
        self.assistant = assistant or Assistant()

    def run(self, prompt):
        print("GUI interface handling")
        print("AI Assistant")
        print(f"Provider: {self.assistant.llm.mode}")
        print()
        print("Commands:")
        print("  /agent <prompt>  → send request to agent router")
        print(
            "  /swap <provider> → swap provider (chatgpt/gemini)"
        )
        print("  /save [path]     → save conversation entity to json")
        print("  /quit             → exit")
        print()

        prompt = prompt.strip()

        if not prompt:
            warn(
                "No prompt provided."
            )
            return "No prompt provided."

        response = self.assistant.send(prompt)
        return response
