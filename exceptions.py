class LLMClientError(Exception):
    """Base exception for all LLM client errors"""

    pass


class ModelUnavailableError(LLMClientError):
    """Raised when the requested model is unavailable or invalid"""

    pass


class RateLimitError(LLMClientError):
    """Raised when API rate limits are exceeded"""

    pass


class TimeoutError(LLMClientError):
    """Raised when API request times out"""

    pass


class AuthenticationError(LLMClientError):
    """Raised when API authentication fails"""

    pass


class InvalidRequestError(LLMClientError):
    """Raised when the API request is invalid"""

    pass


class APIServerError(LLMClientError):
    """Raised when the API server returns a server error"""

    pass
