import core.config as config

from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
)

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
        base_url: str = "http://localhost:11434/v1",
    ):
        super().__init__(context)

        # If model is supplied explicitly, use it.
        # Otherwise ALWAYS use config.py.
        self.model = model if model else config.OLLAMA_MODEL

        print(f"[Ollama] Model: {self.model}")
        print(f"[Ollama] Base URL: {base_url}")

        self.client = OpenAI(
            api_key=api_key or "ollama",
            base_url=base_url,
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            content = response.choices[0].message.content

            if not content:
                raise LLMRequestError(
                    "Ollama returned an empty response."
                )

            return content

        except AuthenticationError as e:
            raise LLMAuthenticationError(
                "Ollama authentication failed."
            ) from e

        except APIConnectionError as e:
            raise LLMRequestError(
                "Could not connect to Ollama. "
                "Make sure Ollama is running."
            ) from e

        except APIStatusError as e:
            raise LLMRequestError(
                f"Ollama API request failed ({e.status_code}) "
                f"for model '{self.model}': {e.message}"
            ) from e

        except LLMRequestError:
            raise

        except Exception as e:
            raise LLMRequestError(
                f"Ollama request failed for model "
                f"'{self.model}': {e}"
            ) from e
