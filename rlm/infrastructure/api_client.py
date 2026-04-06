import logging
import time
from typing import Optional

import litellm

from rlm.exceptions import (
    APIServerError,
    AuthenticationError,
    InvalidRequestError,
    LLMClientError,
    ModelUnavailableError,
    RateLimitError,
    TimeoutError,
)
from rlm.infrastructure.config import Config, create_config
from rlm.retry_strategy import ExponentialBackoffStrategy, RetryStrategy

logger = logging.getLogger(__name__)


DEFAULT_MAX_TOKENS = 3000


class LLMClient:
    def __init__(
        self,
        model: str | None = None,
        config: Optional[Config] = None,
        retry_strategy: Optional[RetryStrategy] = None,
    ):
        """Initialize LLM client with optional model override and config

        Args:
            model: Optional model override
            config: Optional configuration object (creates default if None)
            retry_strategy: Optional retry strategy (creates default if None)
        """
        self.config = config or create_config()
        self.model = model or self.config.model
        self.api_key = self.config.api_key
        self.base_url = self.config.base_url
        self.timeout = self.config.request_timeout
        self.retry_strategy = retry_strategy or ExponentialBackoffStrategy(
            max_retries=self.config.max_retries
        )

        logger.info(f"Initialized LLMClient with model: {self.model}")
        if self.base_url:
            logger.info(f"Using custom base URL: {self.base_url}")

    def _map_litellm_error(self, error: Exception, attempt: int) -> LLMClientError:
        """Map litellm exceptions to custom exceptions

        Args:
            error: The exception that occurred
            attempt: Current attempt number

        Returns:
            LLMClientError: Mapped exception
        """
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
            f"LLM API error (attempt {attempt + 1}/{self.retry_strategy.max_retries + 1}): {error}"
        )

    def get_query(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> str:
        """
        Execute a query to LLM with retry logic and error handling

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Optional model override

        Returns:
            str: The model's response content

        Raises:
            LLMClientError: If all retry attempts fail
        """
        model_to_use = model or self.model
        max_attempts = self.retry_strategy.max_retries + 1

        for attempt in range(max_attempts):
            try:
                logger.debug(
                    f"Attempt {attempt + 1}/{max_attempts} for model {model_to_use}"
                )

                kwargs = {
                    "model": model_to_use,
                    "messages": messages,
                    "timeout": self.timeout,
                    "max_tokens": DEFAULT_MAX_TOKENS,
                }

                if self.base_url:
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

                if not self.retry_strategy.should_retry(mapped_error, attempt):
                    raise mapped_error

                backoff = self.retry_strategy.calculate_backoff(attempt)
                logger.info(f"Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        raise LLMClientError(f"All {max_attempts} attempts failed")
