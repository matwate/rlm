import warnings

from api_client import ZaiClient
from lua_runtime import LuaRuntimeWrapper
from prompts import build_sys_prompt


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
            {"role": "system", "content": build_sys_prompt(self.ctx_length)},
            {"role": "user", "content": initial_prompt},
        ]

    def _run_as_is(self):

        query = self.llm.get_query(self.messages)
        hmm = self.runtime.execute_query(query)
        print(query)
        print(hmm)
        self.messages.append({"role": "assistant", "content": query})
