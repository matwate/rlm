import logging
import os
from dataclasses import dataclass

import dotenv

dotenv.load_dotenv()


@dataclass
class Config:
    """Configuration for RLM system"""

    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    max_retries: int = 3
    request_timeout: int = 60
    log_level: str = "INFO"
    max_iters: int = 10
    max_depth: int = 5

    def __post_init__(self):
        """Load configuration from environment variables and validate"""
        self.api_key = self.api_key or os.getenv("API_KEY")
        self.base_url = self.base_url or os.getenv("BASE_URL")
        self.model = self.model or os.getenv("MODEL")

        if os.getenv("MAX_RETRIES"):
            self.max_retries = int(os.getenv("MAX_RETRIES", "3"))

        if os.getenv("REQUEST_TIMEOUT"):
            self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))

        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.max_iters = int(os.getenv("MAX_ITERS", 10))
        self.max_depth = int(os.getenv("MAX_DEPTH", 5))

        self._validate()
        self._setup_logging()

    def _validate(self):
        """Validate required configuration"""
        if not self.api_key:
            raise ValueError(
                "API_KEY environment variable is required. "
                "Set it in your .env file or environment."
            )

        if not self.model:
            raise ValueError(
                "MODEL environment variable is required. "
                "Set it in your .env file or environment."
            )

        if self.max_retries < 0:
            raise ValueError("MAX_RETRIES must be non-negative")

        if self.max_iters < -1 or self.max_iters == 0:
            raise ValueError("MAX_ITERS must be positive or -1 for indefinite")

        if self.max_depth <= 0:
            raise ValueError("MAX_DEPTh must be positive")

        if self.request_timeout <= 0:
            raise ValueError("REQUEST_TIMEOUT must be positive")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_log_levels}, got {self.log_level}"
            )

    def _setup_logging(self):
        """Configure logging based on LOG_LEVEL"""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def log_config(self, logger: logging.Logger):
        """Log current configuration (without sensitive data)"""
        logger.info(f"Using model: {self.model}")
        logger.info(f"Base URL: {self.base_url or 'default (provider-specific)'}")
        logger.info(f"Max retries: {self.max_retries}")
        logger.info(f"Request timeout: {self.request_timeout}s")
        logger.info(f"Log level: {self.log_level}")


def create_config() -> Config:
    """Factory function to create and return a Config instance"""
    return Config()
