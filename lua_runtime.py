import logging
import re
from typing import Callable

import lupa.luajit21 as lupa

logger = logging.getLogger(__name__)


class LuaRuntimeWrapper:
    """Wrapper for LuaJIT runtime with Python integration"""

    def __init__(
        self, recursion_callback: Callable[[str, str | None], str] | None = None
    ):
        """Initialize Lua runtime with Python functions exposed to Lua

        Args:
            recursion_callback: Callback function for handling RECURSE() calls from Lua
        """
        self.runtime = lupa.LuaRuntime()
        self.captured_output: list[str] = []
        self.close_recursion: bool = False
        self.final_message: str = ""
        self._recursion_callback = recursion_callback
        self._current_depth: int = 0
        self._max_depth: int = 0

        self._setup_print_capture()
        self._setup_finalization()
        self._setup_recursion()
        self._setup_regex_functions()

        logger.debug("LuaRuntimeWrapper initialized")

    def _setup_print_capture(self) -> None:
        """Setup print() function to capture output in Python"""

        def capture_output(*args) -> None:
            output = " ".join(str(arg) for arg in args)
            if len(output) > 1000:
                output = output[:1000] + "...[First 1000 Characters]"
            self.captured_output.append(output)

        self.runtime.globals()["_capture_print"] = capture_output
        self.runtime.execute("print = function(...) _capture_print(...) end")
        logger.debug("Print capture configured")

    def _setup_finalization(self) -> None:
        """Setup FINAL() function to mark completion of recursion"""

        def close_loop(*args) -> None:
            output = " ".join(str(arg) for arg in args)
            self.close_recursion = True
            self.final_message = output

        self.runtime.globals()["_finalize"] = close_loop
        self.runtime.execute("FINAL =  function(...)  _finalize(...) end")
        logger.debug("Finalization function configured")

    def _setup_recursion(self) -> None:
        """Setup RECURSE() function for recursive LLM calls"""

        def handle_lua_recursion(sub_prompt: str, sub_context: str | None) -> str:
            if self._recursion_callback:
                result = self._recursion_callback(sub_prompt, sub_context)
                return result
            else:
                error_msg = "Recursion callback not set - cannot make recursive calls"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        self.runtime.globals()["_recurse"] = handle_lua_recursion
        self.runtime.execute(
            "RECURSE = function(prompt, context) return _recurse(prompt, context) end"
        )
        logger.debug("Recursion function configured")

    def _setup_regex_functions(self) -> None:
        """Setup REGEX_FIND, REGEX_FIND_ALL, REGEX_COUNT functions for Lua"""

        def regex_find_all(text: str, pattern: str) -> list:
            """Find all matches of regex pattern in text, returns Lua table"""
            try:
                matches = re.findall(pattern, text, re.MULTILINE)
                # Convert directly to Lua table
                lua_table = self.runtime.table()
                for i, match in enumerate(
                    matches, start=1
                ):  # Lua uses 1-based indexing
                    if isinstance(match, tuple):
                        lua_table[i] = "".join(match)
                    else:
                        lua_table[i] = match
                logger.debug(
                    f"REGEX_FIND_ALL: Found {len(matches)} matches for pattern {pattern}"
                )
                return lua_table
            except Exception as e:
                logger.warning(f"REGEX_FIND_ALL error: {e}")
                return self.runtime.table()

        def regex_find(text: str, pattern: str) -> str | None:
            """Find first match of regex pattern in text, returns match or nil"""
            try:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    logger.debug(f"REGEX_FIND: Found match for pattern {pattern}")
                    return match.group()
                return None
            except Exception as e:
                logger.warning(f"REGEX_FIND error: {e}")
                return None

        def regex_count(text: str, pattern: str) -> int:
            """Count all matches of regex pattern in text"""
            try:
                matches = re.findall(pattern, text, re.MULTILINE)
                count = len(matches)
                logger.debug(
                    f"REGEX_COUNT: Found {count} matches for pattern {pattern}"
                )
                return count
            except Exception as e:
                logger.warning(f"REGEX_COUNT error: {e}")
                return 0

        self.runtime.globals()["_regex_find_all"] = regex_find_all
        self.runtime.globals()["_regex_find"] = regex_find
        self.runtime.globals()["_regex_count"] = regex_count

        self.runtime.execute("""
            REGEX_FIND_ALL = function(text, pattern)
                return  _regex_find_all(text, pattern)
            end
            
            REGEX_FIND = function(text, pattern)
                return _regex_find(text, pattern)
            end
            
            REGEX_COUNT = function(text, pattern)
                return _regex_count(text, pattern)
            end        """)

        logger.debug("Regex functions configured")

    def set_variable(self, name: str, value: str | None) -> None:
        """Set a variable in the Lua environment

        Args:
            name: Variable name
            value: Variable value (None sets to nil)
        """
        if value:
            escaped = value.replace("]]", "\\]]")
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
            self.captured_output = []

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
