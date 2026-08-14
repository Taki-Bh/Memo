# providers/chatgpt_api.py

from openai import OpenAI
from openai import AuthenticationError

from core.context import LLMContext
from core.provider import LLMProvider
from core.exceptions import (
    LLMAuthenticationError,
    LLMRequestError,
)


class ChatGPTAPIProvider(LLMProvider):

    def __init__(
        self,
        context: LLMContext,
        api_key: str,
        model: str = "gpt-5.6",
    ):
        super().__init__(context)

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )

            return response.output_text

        except AuthenticationError as e:
            raise LLMAuthenticationError(
                "OpenAI API authentication failed."
            ) from e

        except Exception as e:
            raise LLMRequestError(
                "OpenAI API request failed."
            ) from e