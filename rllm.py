from api_client import ZaiClient
from lua_runtime import LuaRuntimeWrapper
from prompts import build_sys_prompt
from utils import remove_thinking_blocks


class RLM:
    def __init__(
        self,
        initial_prompt: str,
        initial_context: str = "",
        max_depth: int = 5,
        current_depth: int = 0,
    ):
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.llm = ZaiClient()
        self.runtime = LuaRuntimeWrapper(recursion_callback=None)
        self.runtime._recursion_callback = self._handle_recursion

        if initial_prompt and not initial_context:
            initial_context = initial_prompt

        self.runtime.set_variable("prompt", initial_prompt)
        self.runtime.set_variable("context", initial_context)
        self.ctx_length = len(initial_context)
        self.runtime.set_depth(current_depth, max_depth)

        self.messages = [
            {
                "role": "developer",
                "content": build_sys_prompt(self.ctx_length, current_depth, max_depth),
            },
            {"role": "user", "content": initial_prompt},
        ]

    def _handle_recursion(self, sub_prompt, sub_context):
        print(
            f"RLM Has called recursively to depth: {self.current_depth + 1}\nSub-Prompt:{sub_prompt}\nSub-Context Length:{len(sub_context)  if sub_context else self.ctx_length}"
        )
        if self.current_depth >= self.max_depth:
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
        )

        sub_rlm.run()
        return sub_rlm.runtime.final_message

    def _run_as_is(self):

        query = self.llm.get_query(self.messages)
        query_sanitized = remove_thinking_blocks(query)
        hmm = self.runtime.execute_query(query_sanitized)
        print(f"Depth {self.current_depth} LM: {query}")
        self.messages.append({"role": "assistant", "content": query})
        self.messages.append({"role": "tool", "content": str(hmm)})

    def _run_n_times(self, n):
        for _ in range(n):
            self._run_as_is()

    def run(self, max_iter=10):
        i = 0
        while not self.runtime.close_recursion and i < max_iter:
            self._run_as_is()
            i += 1

        if i == max_iter:
            print("MAX ITERATIONS REACHED, BREAKING EARLY")
        print(self.runtime.final_message)
