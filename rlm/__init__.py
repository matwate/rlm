"""RLM - Recursive Language Model package."""

__version__ = "0.1.0"

from rlm.core.rllm import RLM
from rlm.infrastructure.config import Config, create_config
from rlm.infrastructure.api_client import LLMClient
from rlm.infrastructure.message_manager import MessageManager
from rlm.infrastructure.recursion_handler import RecursionHandler
from rlm.lua.lua_runtime import LuaRuntimeWrapper
from rlm.lua.lua_runtime_core import LuaRuntimeCore
from rlm.lua.lua_function_registry import LuaFunctionRegistry
from rlm.exceptions import (
    LLMClientError,
    ModelUnavailableError,
    RateLimitError,
    TimeoutError,
    AuthenticationError,
    InvalidRequestError,
    APIServerError,
)
from rlm.retry_strategy import RetryStrategy, ExponentialBackoffStrategy

__all__ = [
    "RLM",
    "Config",
    "create_config",
    "LLMClient",
    "MessageManager",
    "RecursionHandler",
    "LuaRuntimeWrapper",
    "LuaRuntimeCore",
    "LuaFunctionRegistry",
    "LLMClientError",
    "ModelUnavailableError",
    "RateLimitError",
    "TimeoutError",
    "AuthenticationError",
    "InvalidRequestError",
    "APIServerError",
    "RetryStrategy",
    "ExponentialBackoffStrategy",
]
