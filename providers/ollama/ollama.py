from core.context import LLMContext
from core.provider import LLMProvider
from providers.ollama.ollama_api import OllamaAPIProvider


class OllamaProvider(LLMProvider):

    def __init__(
        self,
        context: LLMContext,
        api_key: str | None = None,
        model: str = "qwen3:8b",
        base_url: str = "http://localhost:11434",
    ):
        super().__init__(context)
        self.name = "Ollama"
        self.provider = OllamaAPIProvider(
            context=context,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        self.mode = "api"

    def generate(self, prompt: str, await_response=True) -> str:
        return self.provider.generate(prompt)
