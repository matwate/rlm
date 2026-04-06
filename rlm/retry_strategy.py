from rlm.exceptions import APIServerError, RateLimitError, TimeoutError


class RetryStrategy:
    """Base class for retry strategies"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error is retryable and if we should attempt retry
        Args:
            error: The error that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            bool: True if should retry, False otherwise
        """
        raise NotImplementedError

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff time in seconds

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            float: Backoff time in seconds
        """
        raise NotImplementedError


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff strategy with configurable parameters"""

    def __init__(self, max_retries: int = 3, max_backoff: float = 60):
        """Initialize exponential backoff strategy

        Args:
            max_retries: Maximum number of retries (default: 3)
            max_backoff: Maximum backoff time in seconds (default: 60)
        """
        self.max_retries = max_retries
        self.max_backoff = max_backoff

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error is retryable and if we should attempt retry

        Args:
            error: The error that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            bool: True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        if isinstance(error, RateLimitError):
            return True

        if isinstance(error, (APIServerError, TimeoutError)):
            return True

        return False

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time in seconds

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            float: Backoff time in seconds
        """
        return min(2**attempt, self.max_backoff)
