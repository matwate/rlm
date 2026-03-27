import logging
import re
from typing import Callable

import lupa.luajit21 as lupa

logger = logging.getLogger(__name__)


MAX_OUTPUT_LENGTH = 1000


class LuaFunctionRegistry:
    """Registry for Lua functions exposed from Python"""

    def __init__(self, runtime: lupa.LuaRuntime):
        """Initialize the function registry with a Lua runtime

        Args:
            runtime: The LuaJIT runtime instance
        """
        self.runtime = runtime

    def setup_print_capture(self, captured_output: list[str]) -> None:
        """Setup print() function to capture output in Python

        Args:
            captured_output: List to store captured print output
        """

        def capture_output(*args) -> str:
            output = " ".join(str(arg) for arg in args)
            logger.debug(output)
            if len(output) > MAX_OUTPUT_LENGTH:
                output = (
                    output[:MAX_OUTPUT_LENGTH]
                    + f"...[First {MAX_OUTPUT_LENGTH} Characters]"
                )
            captured_output.append(output)
            return output

        self.runtime.globals()["_capture_print"] = capture_output
        self.runtime.execute("print = function(...) return  _capture_print(...) end")
        logger.debug("Print capture configured")

    def setup_finalization(
        self, close_recursion_flag: list[bool], final_message_holder: list[str]
    ) -> None:
        """Setup FINAL() function to mark completion of recursion

        Args:
            close_recursion_flag: List containing a boolean flag (mutable from closure)
            final_message_holder: List containing the final message (mutable from closure)
        """

        def close_loop(*args) -> None:
            output = "\n".join(str(arg) for arg in args)
            close_recursion_flag[0] = True
            final_message_holder[0] = output

        self.runtime.globals()["_finalize"] = close_loop

        self.runtime.execute("""
            function TEXT(...)
                local parts = {}
                for i = 1, select('#', ...) do
                    parts[i] = tostring(select(i, ...))
                end
                return table.concat(parts, "\\n")
            end

            FINAL = function(...) _finalize(...) end
        """)
        logger.debug("Finalization function configured")

    def setup_recursion(
        self, recursion_callback_holder: list[Callable[[str, str | None], str] | None]
    ) -> None:
        """Setup RECURSE() function for recursive LLM calls

        Args:
            recursion_callback_holder: List containing the callback function (mutable for updates)
        """

        def handle_lua_recursion(sub_prompt: str, sub_context: str | None) -> str:
            callback = recursion_callback_holder[0]
            if callback:
                result = callback(sub_prompt, sub_context)
                return result
            else:
                return ""

        self.runtime.globals()["_recurse"] = handle_lua_recursion
        self.runtime.execute(
            "RECURSE = function(prompt, context) return _recurse(prompt, context) end"
        )
        logger.debug("Recursion function configured")

    def setup_regex_functions(self) -> None:
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
            end
        """)

        logger.debug("Regex functions configured")
