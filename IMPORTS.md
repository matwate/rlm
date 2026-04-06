# Import Reference

## Core RLM Usage

```python
# Import main RLM class
from rlm import RLM

# Or import from specific modules
from rlm.core.rllm import RLM
from rlm.infrastructure.config import create_config
from rlm.infrastructure.api_client import LLMClient
from rlm.infrastructure.message_manager import MessageManager
from rlm.infrastructure.recursion_handler import RecursionHandler

# Lua runtime
from rlm.lua import LuaRuntimeWrapper, LuaRuntimeCore, LuaFunctionRegistry

# Exceptions
from rlm.exceptions import (
    LLMClientError,
    ModelUnavailableError,
    RateLimitError,
    TimeoutError,
    AuthenticationError,
    InvalidRequestError,
    APIServerError,
)

# Retry strategies
from rlm.retry_strategy import RetryStrategy, ExponentialBackoffStrategy
```

## For TUI Implementation

```python
from rlm.core.rllm import RLM
from rlm.infrastructure.config import create_config
from rlm.lua.lua_runtime import LuaRuntimeWrapper
```

## For Web UI Implementation

```python
from rlm.core.rllm import RLM
from rlm.infrastructure.config import Config
from rlm.infrastructure.api_client import LLMClient
```

## CLI Usage

```bash
# Install package
uv pip install -e .

# Run CLI
rlm --help
rlm --prompt "your prompt" --file path/to/file.txt
rlm --repl-only
```
