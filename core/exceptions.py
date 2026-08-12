# core/exceptions.py


class AppException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ConnectionError(AppException):
    """Raised when connection to AI fails"""

    pass


class LLMException(AppException):
    """Base exception for LLM-related errors."""

    pass


class LLMConfigurationError(LLMException):
    """Raised when an LLM provider is incorrectly configured."""

    pass


class LLMAuthenticationError(LLMException):
    """Raised when authentication with an LLM provider fails."""

    pass


class LLMRequestError(LLMException):
    """Raised when an LLM request fails."""

    pass


class LLMResponseError(LLMException):
    """Raised when an LLM returns an invalid or unexpected response."""

    pass

class APIKeyMissingError(LLMException):
    """Raised when an API key is missing for an LLM provider."""

    pass
class UnrecognizedMessageFormat(LLMException):
    """Raised when a message anomaly appears in the DOM"""

    pass