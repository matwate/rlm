import logging
from typing import Callable

import lupa.luajit21 as lupa

from rlm.lua.lua_function_registry import LuaFunctionRegistry
from rlm.lua.lua_runtime_core import LuaRuntimeCore

logger = logging.getLogger(__name__)


class LuaRuntimeWrapper:
    """Wrapper for LuaJIT runtime with Python integration"""

    def __init__(
        self,
        recursion_callback: Callable[[str, str | None], str] | None = None,
        enable_ai_features: bool = True,
    ):
        """Initialize Lua runtime with Python functions exposed to Lua

        Args:
            recursion_callback: Callback function for handling RECURSE() calls from Lua
            enable_ai_features: Enable FINAL() and RECURSE() functions (default: True)
        """
        runtime = lupa.LuaRuntime()
        self.core = LuaRuntimeCore(runtime)
        self.registry = LuaFunctionRegistry(runtime)

        # Setup functions with mutable lists for closure access
        close_flag = [False]
        final_msg = [""]
        recursion_callback_holder = [recursion_callback]

        # Configure Lua functions (always available)
        self.registry.setup_print_capture(self.core.captured_output)
        self.registry.setup_regex_functions()

        # Configure AI-specific functions (FINAL, RECURSE)
        if enable_ai_features:
            self.registry.setup_finalization(close_flag, final_msg)
            self.registry.setup_recursion(recursion_callback_holder)

        # Setup properties to sync with closure variables
        self._close_flag = close_flag
        self._final_msg = final_msg
        self._recursion_callback_holder = recursion_callback_holder
        self._enable_ai_features = enable_ai_features

        logger.debug("LuaRuntimeWrapper initialized")

    def set_recursion_callback(
        self, callback: Callable[[str, str | None], str] | None
    ) -> None:
        """Set or update the recursion callback

        Args:
            callback: Callback function for handling RECURSE() calls from Lua
        """
        self._recursion_callback_holder[0] = callback
        logger.debug("Recursion callback updated")

    @property
    def captured_output(self) -> list[str]:
        """Get captured output from print statements"""
        return self.core.captured_output

    @property
    def close_recursion(self) -> bool:
        """Get recursion close flag"""
        return self._close_flag[0]

    @close_recursion.setter
    def close_recursion(self, value: bool) -> None:
        """Set recursion close flag"""
        self._close_flag[0] = value

    @property
    def final_message(self) -> str:
        """Get final message"""
        return self._final_msg[0]

    @final_message.setter
    def final_message(self, value: str) -> None:
        """Set final message"""
        self._final_msg[0] = value

    def execute_query(self, query: str) -> str | None:
        """Execute a Lua query and return captured output

        Args:
            query: Lua code to execute

        Returns:
            Captured output or result, or None if no output

        Raises:
            lupa.LuaSyntaxError: If Lua syntax is invalid
            lupa.LuaError: If Lua runtime error occurs
        """
        return self.core.execute_query(query)

    def set_variable(self, name: str, value: str | None) -> None:
        """Set a variable in the Lua environment

        Args:
            name: Variable name
            value: Variable value (None sets to nil)
        """
        self.core.set_variable(name, value)

    def get_variable(self, name: str) -> str | None:
        """Get a variable from the Lua environment

        Args:
            name: Variable name

        Returns:
            Variable value or None if not found
        """
        return self.core.get_variable(name)

    def set_depth(self, current: int, max_depth: int) -> None:
        """Set recursion depth information in Lua environment

        Args:
            current: Current recursion depth
            max_depth: Maximum recursion depth
        """
        self.core.set_depth(current, max_depth)
