# providers/gemini.py

import os

from core.context import LLMContext
from core.provider import LLMProvider

from providers.gemini.gemini_api import GeminiAPIProvider
from providers.gemini.gemini_browser import GeminiBrowserProvider


class GeminiProvider(LLMProvider):

    def __init__(
        self,
        context: LLMContext,
        api_key: str | None = None,
        model: str = "gpt-5.6",
        use_browser: bool | None = None,
    ):
        super().__init__(context)

        api_key = api_key or os.getenv("OPENAI_API_KEY")

        # Explicit browser mode
        if use_browser is True:
            self.provider = GeminiBrowserProvider(context)
            self.mode = "browser"

        # Explicit API mode
        elif use_browser is False:
            if not api_key:
                raise ValueError(
                    "API mode requested but OPENAI_API_KEY is missing."
                )

            self.provider = GeminiAPIProvider(
                context=context,
                api_key=api_key,
                model=model,
            )

            self.mode = "api"

        # Automatic mode
        elif api_key:
            self.provider = GeminiAPIProvider(
                context=context,
                api_key=api_key,
                model=model,
            )

            self.mode = "api"

        # No API key → browser
        else:
            self.provider = GeminiBrowserProvider(context)
            self.mode = "browser"

    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)