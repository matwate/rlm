from api_client import ZaiClient
from lua_runtime import LuaRuntimeWrapper
from prompts import build_sys_prompt
from utils import remove_thinking_blocks


class RLM:

    def __init__(self, initial_prompt: str, initial_context: str = ""):
        self.llm = ZaiClient()
        self.runtime = LuaRuntimeWrapper()

        if initial_prompt and not initial_context:
            initial_context = initial_prompt

        self.runtime.set_variable("prompt", initial_prompt)
        self.runtime.set_variable("context", initial_context)
        self.ctx_length = len(initial_context)

        self.messages = [
            {"role": "developer", "content": build_sys_prompt(self.ctx_length)},
            {"role": "user", "content": initial_prompt},
        ]

    def _run_as_is(self):

        query = self.llm.get_query(self.messages)
        query_sanitized = remove_thinking_blocks(query)
        hmm = self.runtime.execute_query(query_sanitized)
        print(query)
        self.messages.append({"role": "assistant", "content": query})
        self.messages.append({"role": "tool", "content": str(hmm)})

    def _run_n_times(self, n):
        for _ in range(n):
            self._run_as_is()

    def run(self, max_depth=1, max_iter=5):
        i = 0
        while not self.runtime.close_recursion or i < max_iter:
            self._run_as_is()
            i += 1
        print(self.runtime.final_message)
