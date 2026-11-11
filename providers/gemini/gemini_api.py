# providers/gemini_api.py

from google import genai
from google.genai.errors import APIError

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import (
    LLMAuthenticationError,
    LLMRequestError,
)


class GeminiAPIProvider(LLMProvider):

    def __init__(
        self,
        context: LLMContext,
        api_key: str,
        model: str = "gemini-2.5-flash",
    ):
        super().__init__(context)

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            return response.text

        except APIError as e:
            # Check for standard 401 Unauthorized / Authentication failure status codes
            if e.code == 401:
                raise LLMAuthenticationError(
                    "Gemini API authentication failed."
                ) from e
            
            raise LLMRequestError(
                f"Gemini API request failed: {e.message}"
            ) from e

        except Exception as e:
            raise LLMRequestError(
                "Gemini API request failed."
            ) from e