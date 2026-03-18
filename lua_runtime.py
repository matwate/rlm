from fileinput import close

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
                result = f"Lua Syntax Error: {e}"

            # Return captured output (from print) or result (from eval)
            if self.captured_output:
                return "\n".join(self.captured_output)
            elif result is not None:
                return str(result)
            else:
                return None
        except lupa.LuaSyntaxError as e:
            print(f"Lua Syntax Error: {e}")
            print(f"\nQuery was: {repr(query)}")
            raise
        except Exception as e:
            print(f"Error: {e}")
            raise
