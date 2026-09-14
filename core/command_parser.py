class CommandParser:
    """Parses slash commands entered by the user."""

    AGENT_COMMAND = "/agent"
    SWAP_COMMAND = "/swap"
    SAVE_COMMAND = "/save"
    TITLE_COMMAND = "/title"
    COMPUTER_COMMAND = "/computer"
    PDF_COMMAND = "/pdf"
    

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
        if text.startswith(cls.COMPUTER_COMMAND):
            filename=text[len(cls.COMPUTER_COMMAND):].strip()
            return cls.COMPUTER_COMMAND, filename

        return None, text
