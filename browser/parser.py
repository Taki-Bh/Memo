# providers/browser/message_parser.py

class MessageParser:


    @classmethod
    def parse(cls, element,indice):
        raw_text = element.inner_text()

        if cls.is_user_message(element,indice):
            return "user", cls.clean_text(raw_text)

        return "llm", cls.clean_text(raw_text)

    @classmethod
    def is_user_message(cls, element, indice) -> bool:
        indicator = element.locator(indice)

        return indicator.count() > 0

    @staticmethod
    def clean_text(text: str) -> str:
        if ":" in text:
            return text.split(":", 1)[1].strip()

        return text.strip()

    @classmethod
    def parse_assistant_message(cls, element,indice) -> str:
        role, text = cls.parse(element,indice)

        if role != "llm":
            raise ValueError(
                "Latest message is not an assistant message"
            )

        return text