import logging
import time

import litellm

from config import API_KEY, BASE_URL, MAX_RETRIES, MODEL, REQUEST_TIMEOUT
from exceptions import (
    APIServerError,
    AuthenticationError,
    InvalidRequestError,
    LLMClientError,
    ModelUnavailableError,
    RateLimitError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, model: str | None = None):
        """Initialize LLM client with optional model override"""
        self.model = model or MODEL
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self.max_retries = MAX_RETRIES
        self.timeout = REQUEST_TIMEOUT

        logger.info(f"Initialized LLMClient with model: {self.model}")
        if self.base_url:
            logger.info(f"Using custom base URL: {self.base_url}")

    def _clean_markdown(self, content: str) -> str:
        """Remove markdown code block markers from content"""
        lines = content.split("\n")
        cleaned = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```") or line.strip().endswith("```"):
                in_code_block = not in_code_block
                continue
            if not in_code_block:
                cleaned.append(line)
        return "\n".join(cleaned).strip()

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error is retryable and if we should attempt retry"""
        if attempt >= self.max_retries:
            return False

        if isinstance(error, RateLimitError):
            return True

        if isinstance(error, (APIServerError, TimeoutError)):
            return True

        return False

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time in seconds"""
        return min(2**attempt, 60)

    def _map_litellm_error(self, error: Exception, attempt: int) -> LLMClientError:
        """Map litellm exceptions to custom exceptions"""
        error_message = str(error).lower()

        if "rate limit" in error_message or "429" in error_message:
            return RateLimitError(f"Rate limit exceeded: {error}")

        if "timeout" in error_message or "timed out" in error_message:
            return TimeoutError(f"Request timeout after {self.timeout}s: {error}")

        if (
            "authentication" in error_message
            or "unauthorized" in error_message
            or "401" in error_message
        ):
            return AuthenticationError(f"Authentication failed: {error}")

        if "invalid request" in error_message or "400" in error_message:
            return InvalidRequestError(f"Invalid request: {error}")

        if "model" in error_message and (
            "not found" in error_message or "unavailable" in error_message
        ):
            return ModelUnavailableError(f"Model {self.model} unavailable: {error}")

        if "500" in error_message or "502" in error_message or "503" in error_message:
            return APIServerError(f"API server error: {error}")

        return LLMClientError(
            f"LLM API error (attempt {attempt + 1}/{self.max_retries}): {error}"
        )

    def get_query(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> str:
        """
        Execute a query to the LLM with retry logic and error handling

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Optional model override

        Returns:
            str: The model's response content

        Raises:
            LLMClientError: If all retry attempts fail
        """
        model_to_use = model or self.model

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} for model {model_to_use}"
                )

                kwargs = {
                    "model": model_to_use,
                    "messages": messages,
                    "timeout": self.timeout,
                    "max_tokens": 3000,
                }

                if self.base_url != "":
                    kwargs["api_base"] = self.base_url

                if self.api_key:
                    kwargs["api_key"] = self.api_key

                response = litellm.completion(**kwargs)

                content = response.choices[0].message.content

                if not content:
                    raise LLMClientError("Model returned empty response")

                logger.info(f"Successfully received response from {model_to_use}")
                return content

            except Exception as e:
                mapped_error = self._map_litellm_error(e, attempt)
                logger.warning(f"Request failed: {mapped_error}")

                if not self._should_retry(mapped_error, attempt):
                    raise mapped_error

                backoff = self._calculate_backoff(attempt)
                logger.info(f"Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        raise LLMClientError(f"All {self.max_retries + 1} attempts failed")
