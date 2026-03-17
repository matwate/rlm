import lupa.luajit21 as lupa


class LuaRuntimeWrapper:
    def __init__(self):
        print(
            f"Using {lupa.LuaRuntime().lua_implementation} (compiled with {lupa.LUA_VERSION}"
        )
        self.runtime = lupa.LuaRuntime()
        self.captured_output = []

        # Create a Python function to capture print output
        def capture_output(*args):
            # Convert all arguments to strings and join them with spaces
            output = " ".join(str(arg) for arg in args)
            self.captured_output.append(output)
            # Also print to console for debugging
            print(output)

        # Make this function available to Lua
        self.runtime.globals()["_capture_print"] = capture_output

        # Override Lua's print function
        self.runtime.execute("print = function(...) _capture_print(...) end")

    def set_variable(self, name, value):
        if value:
            escaped = value.replace("]]", "\\]]")
            self.runtime.execute(f"{name} = [[{escaped}]]")
        else:
            self.runtime.execute(f"{name} = nil")

    def execute_query(self, query):
        try:
            # Clear previous captured output
            self.captured_output = []

            try:
                result = self.runtime.eval(query)
            except lupa.LuaSyntaxError:
                self.runtime.execute(query)
                result = None

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
