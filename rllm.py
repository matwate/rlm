import utils
from api_client import ZaiClient
from lua_runtime import LuaRuntimeWrapper
from prompts import build_sub_sys_prompt, build_sys_prompt
from utils import remove_thinking_blocks


class RLM:
    def __init__(
        self,
        initial_prompt: str,
        initial_context: str = "",
        max_depth: int = 5,
        current_depth: int = 0,
        disable_guards: bool = False,
        quiet: bool = False,
    ):
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.disable_guards = disable_guards
        self.quiet = quiet
        self.llm = ZaiClient()
        self.runtime = LuaRuntimeWrapper(recursion_callback=None)
        self.runtime._recursion_callback = self._handle_recursion

        if initial_prompt and not initial_context:
            initial_context = initial_prompt

        self.runtime.set_variable("prompt", initial_prompt)
        self.runtime.set_variable("context", initial_context)
        self.ctx_length = len(initial_context)
        self.runtime.set_depth(current_depth, max_depth)

        sys_prompt = build_sub_sys_prompt() if current_depth > 0 else build_sys_prompt()
        self.messages = [
            {
                "role": "developer",
                "content": sys_prompt,
            },
            {
                "role": "user",
                "content": f"{initial_prompt}\n\nThe context you need to analyze is available in the `context` variable in the Lua environment. Write Lua code to access and analyze it.",
            },
        ]

    def _handle_recursion(self, sub_prompt, sub_context):
        if not self.quiet:
            print(
                f"RLM Has called recursively to depth: {self.current_depth + 1}\nSub-Prompt:{sub_prompt}\nSub-Context Length:{len(sub_context) if sub_context else self.ctx_length}"
            )
        if not self.disable_guards and self.current_depth >= self.max_depth:
            raise RuntimeError(
                f"Max recursion depth ({self.max_depth}) reached. Cannot recurse further."
            )

        context_to_use = (
            sub_context if sub_context else self.runtime.get_variable("context") or ""
        )

        sub_rlm = RLM(
            initial_prompt=sub_prompt,
            initial_context=str(context_to_use),
            max_depth=self.max_depth,
            current_depth=self.current_depth + 1,
            disable_guards=self.disable_guards,
            quiet=self.quiet,
        )

        sub_rlm.run()
        return sub_rlm.runtime.final_message

    def _run_as_is(self):
        try:
            response = self.llm.get_query(self.messages)
            if not self.quiet:
                print(response)

            queries = utils.extract_lua_code_blocks(response)

            results = [self.runtime.execute_query(q) for q in queries]

            if len(results) == 0:
                self.runtime.close_recursion = True
                self.final_message = response

            cleaned_response = self.llm._clean_markdown(response)
            self.messages.append({"role": "assistant", "content": response})
            self.messages.append(
                {
                    "role": "user",
                    "content": "Here's the output of the code you provided"
                    + "\n".join(r for r in results if r is not None),
                }
            )
        except Exception as e:
            raise

    def run(self, max_iter=10):
        i = 0
        actual_max_iter = float("inf") if self.disable_guards else max_iter
        while not self.runtime.close_recursion and i < actual_max_iter:
            self._run_as_is()
            print(f"We're going into iteration: {i +  1 }")
            i += 1

        if i == actual_max_iter:
            if not self.quiet:
                print("MAX ITERATIONS REACHED, BREAKING EARLY")
        print(self.runtime.final_message)
