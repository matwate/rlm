import lupa.luajit21 as lupa


class LuaRuntimeWrapper:
    def __init__(self, recursion_callback=None):
        self.runtime = lupa.LuaRuntime()
        self.captured_output = []
        self.close_recursion = False
        self.final_message = ""
        self._recursion_callback = recursion_callback
        self._current_depth = 0
        self._max_depth = 0

        # Create a Python function to capture print output
        def capture_output(*args):
            output = " ".join(str(arg) for arg in args)
            self.captured_output.append(output)

        self.runtime.globals()["_capture_print"] = capture_output
        self.runtime.execute("print = function(...) _capture_print(...) end")

        def close_loop(*args):
            output = " ".join(str(arg) for arg in args)
            self.close_recursion = True
            self.final_message = output

        self.runtime.globals()["_finalize"] = close_loop
        self.runtime.execute("FINAL =  function(...)  _finalize(...) end")

        def handle_lua_recursion(sub_prompt, sub_context):
            if self._recursion_callback:
                result = self._recursion_callback(sub_prompt, sub_context)
                return result
            else:
                raise RuntimeError(
                    "Recursion callback not set - cannot make recursive calls"
                )

        self.runtime.globals()["_recurse"] = handle_lua_recursion
        self.runtime.execute(
            "RECURSE = function(prompt, context) return _recurse(prompt, context) end"
        )

        import re

        def regex_find_all(text, pattern):
            """Find all matches of regex pattern in text, returns Lua table"""
            try:
                matches = re.findall(pattern, text, re.MULTILINE)
                # Convert to Lua table
                lua_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        # For grouped matches, return as string
                        lua_matches.append("".join(match))
                    else:
                        lua_matches.append(match)
                return lua_matches
            except Exception as e:
                return []

        def regex_find(text, pattern):
            """Find first match of regex pattern in text, returns match or nil"""
            try:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    return match.group()
                return None
            except Exception as e:
                return None

        def regex_count(text, pattern):
            """Count all matches of regex pattern in text"""
            try:
                matches = re.findall(pattern, text, re.MULTILINE)
                return len(matches)
            except Exception as e:
                return 0

        self.runtime.globals()["_regex_find_all"] = regex_find_all
        self.runtime.globals()["_regex_find"] = regex_find
        self.runtime.globals()["_regex_count"] = regex_count

        # Register Lua-friendly functions
        self.runtime.execute("""
            REGEX_FIND_ALL = function(text, pattern)
                local py_list = _regex_find_all(text, pattern)
                local lua_table = {}
                
                -- Convert Python list to Lua table
                -- Python lists in Lua bridges are usually 0-indexed.
                -- We iterate and insert into a new table to ensure it is 1-indexed.
                for i = 0, #py_list - 1 do
                    table.insert(lua_table, py_list[i])
                end
                
                return lua_table
            end
            
            REGEX_FIND = function(text, pattern)
                return _regex_find(text, pattern)
            end
            
            REGEX_COUNT = function(text, pattern)
                return _regex_count(text, pattern)
            end        """)

    def set_variable(self, name, value):
        if value:
            escaped = value.replace("]]", "\\]]")
            self.runtime.execute(f"{name} = [[{escaped}]]")
        else:
            self.runtime.execute(f"{name} = nil")

    def get_variable(self, name):
        try:
            return self.runtime.eval(name)
        except:
            return None

    def set_depth(self, current, max_depth):
        self._current_depth = current
        self._max_depth = max_depth
        self.runtime.execute(f"_current_depth = {current}")
        self.runtime.execute(f"_max_depth = {max_depth}")

    def execute_query(self, query):
        try:
            # Clear previous captured output
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

            # Return captured output (from print) or result (from eval)
            if self.captured_output:
                return "\n".join(self.captured_output)
            elif result is not None:
                return str(result)
            else:
                return None
        except lupa.LuaSyntaxError as e:
            error_msg = f"Lua Syntax Error: {e}"
            print(f"{error_msg}")
            print(f"\nQuery was: {repr(query)}")
            raise
        except lupa.LuaError as e:
            # Handle all Lua-specific errors
            error_msg = f"Lua Error: {e}"
            print(f"{error_msg}")
            print(f"\nQuery was: {repr(query)}")
            raise

        except Exception as e:
            # Handle any other unexpected errors
            error_msg = f"Unexpected Error: {type(e).__name__}: {e}"
            print(f"{error_msg}")
            print(f"\nQuery was: {repr(query)}")
            raise
