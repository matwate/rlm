import logging

import lupa.luajit21 as lupa

from rlm.utils import lua_escape_string

logger = logging.getLogger(__name__)


class LuaRuntimeCore:
    """Core runtime operations for Lua execution"""

    def __init__(self, runtime: lupa.LuaRuntime):
        """Initialize the core runtime

        Args:
            runtime: The LuaJIT runtime instance
        """
        self.runtime = runtime
        self.captured_output: list[str] = []
        self.close_recursion: bool = False
        self.final_message: str = ""
        self._current_depth: int = 0
        self._max_depth: int = 0

    @property
    def captured_output(self) -> list[str]:
        """Get captured output from print statements"""
        return self._captured_output

    @captured_output.setter
    def captured_output(self, value: list[str]) -> None:
        """Set captured output"""
        self._captured_output = value

    @property
    def close_recursion(self) -> bool:
        """Get recursion close flag"""
        return self._close_recursion

    @close_recursion.setter
    def close_recursion(self, value: bool) -> None:
        """Set recursion close flag"""
        self._close_recursion = value

    @property
    def final_message(self) -> str:
        """Get final message"""
        return self._final_message

    @final_message.setter
    def final_message(self, value: str) -> None:
        """Set final message"""
        self._final_message = value

    def set_variable(self, name: str, value: str | None) -> None:
        """Set a variable in the Lua environment

        Args:
            name: Variable name
            value: Variable value (None sets to nil)
        """
        if value:
            escaped = lua_escape_string(value)
            self.runtime.execute(f"{name} = [[{escaped}]]")
            logger.debug(f"Set variable '{name}' (length: {len(value)})")
        else:
            self.runtime.execute(f"{name} = nil")
            logger.debug(f"Set variable '{name}' to nil")

    def get_variable(self, name: str) -> str | None:
        """Get a variable from the Lua environment

        Args:
            name: Variable name

        Returns:
            Variable value or None if not found
        """
        try:
            return self.runtime.eval(name)
        except Exception as e:
            logger.warning(f"Failed to get variable '{name}': {e}")
            return None

    def set_depth(self, current: int, max_depth: int) -> None:
        """Set recursion depth information in Lua environment

        Args:
            current: Current recursion depth
            max_depth: Maximum recursion depth
        """
        self._current_depth = current
        self._max_depth = max_depth
        self.runtime.execute(f"_current_depth = {current}")
        self.runtime.execute(f"_max_depth = {max_depth}")
        logger.debug(f"Set recursion depth: {current}/{max_depth}")

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
        try:
            self.captured_output.clear()

            try:
                result = self.runtime.eval(query)
            except lupa.LuaSyntaxError as e:
                self.runtime.execute(query)
                result = (
                    f"The following query presented this Syntax Error {e}:\n{query}"
                )
            except lupa.LuaError as e:
                self.runtime.execute(query)
                result = (
                    f"The following query presented this Runtime Error {e}:\n{query}"
                )

            if self.captured_output:
                output = "\n".join(self.captured_output)
                logger.debug(
                    f"Query executed with captured output (length: {len(output)})"
                )
                return output
            elif result is not None:
                logger.debug(f"Query executed with result (length: {len(str(result))})")
                return str(result)
            else:
                logger.debug("Query executed with no output")
                return None

        except lupa.LuaSyntaxError as e:
            error_msg = f"Lua Syntax Error: {e}"
            logger.error(f"{error_msg}\nQuery was: {repr(query)}")
            raise
        except lupa.LuaError as e:
            error_msg = f"Lua Error: {e}"
            logger.error(f"{error_msg}\nQuery was: {repr(query)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected Error: {type(e).__name__}: {e}"
            logger.error(f"{error_msg}\nQuery was: {repr(query)}")
            raise
