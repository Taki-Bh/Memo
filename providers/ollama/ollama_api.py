import core.config as config
from ollama import Client

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import (
    LLMAuthenticationError,
    LLMRequestError,
)


class OllamaAPIProvider(LLMProvider):

    def __init__(
        self,
        context: LLMContext,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "http://localhost:11434",
    ):
        super().__init__(context)

        self.model = model if model else config.OLLAMA_MODEL

        print(f"[Ollama] Model: {self.model}")
        print(f"[Ollama] Base URL: {base_url}")

        self.client = Client(host=base_url)

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                think=False,
            )
            print(response)
            if isinstance(response, dict):
                content = response.get("message", {}).get("content")
            else:
                msg = getattr(response, "message", None)
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)

            if not content:
                raise LLMRequestError(
                    "Ollama returned an empty response."
                )

            return content

        except Exception as e:
            error_msg = str(e).lower()
            if "auth" in error_msg or "401" in error_msg:
                raise LLMAuthenticationError(
                    "Ollama authentication failed."
                ) from e
            if "connection" in error_msg or "connect" in error_msg or "refused" in error_msg:
                raise LLMRequestError(
                    "Could not connect to Ollama. "
                    "Make sure Ollama is running."
                ) from e

            raise LLMRequestError(
                f"Ollama request failed for model "
                f"{self.model}: {e}"
            ) from e
