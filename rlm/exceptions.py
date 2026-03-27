from datetime import datetime
from typing import Any


class LLMClientError(Exception):
    """Base exception for all LLM client errors"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}
        self.timestamp = datetime.now()


class ModelUnavailableError(LLMClientError):
    """Raised when the requested model is unavailable or invalid"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)


class RateLimitError(LLMClientError):
    """Raised when API rate limits are exceeded"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)


class TimeoutError(LLMClientError):
    """Raised when API request times out"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)


class AuthenticationError(LLMClientError):
    """Raised when API authentication fails"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)


class InvalidRequestError(LLMClientError):
    """Raised when the API request is invalid"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)


class APIServerError(LLMClientError):
    """Raised when the API server returns a server error"""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, context)
