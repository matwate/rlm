import logging

import utils
from api_client import LLMClient
from exceptions import LLMClientError
from lua_runtime import LuaRuntimeWrapper
from prompts import build_sub_sys_prompt, build_sys_prompt

logger = logging.getLogger(__name__)


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
        """Initialize RLM (Recursive Language Model) instance

        Args:
            initial_prompt: The initial prompt for the LLM
            initial_context: Initial context string for analysis
            max_depth: Maximum recursion depth (default: 5)
            current_depth: Current recursion depth (default: 0)
            disable_guards: Disable recursion/iteration guards (default: False)
            quiet: Suppress output (default: False)
        """
        self.max_depth = max_depth
        self.current_depth = current_depth
        self.disable_guards = disable_guards
        self.quiet = quiet
        self.llm = LLMClient()
        self.runtime = LuaRuntimeWrapper(recursion_callback=None)
        self.runtime._recursion_callback = self._handle_recursion
        self.final_message = ""

        if initial_prompt and not initial_context:
            initial_context = initial_prompt

        self.runtime.set_variable("prompt", initial_prompt)
        self.runtime.set_variable("context", initial_context)
        self.ctx_length = len(initial_context)
        self.runtime.set_depth(current_depth, max_depth)

        sys_prompt = build_sub_sys_prompt() if current_depth > 0 else build_sys_prompt()
        self.messages: list[dict[str, str]] = [
            {
                "role": "developer",
                "content": sys_prompt,
            },
            {
                "role": "user",
                "content": f"{initial_prompt}\n\nThe context you need to analyze is available in the `context` variable in the Lua environment. Write Lua code to access and analyze it.",
            },
        ]

        logger.info(f"Initialized RLM at depth {current_depth}/{max_depth}")

    def _handle_recursion(self, sub_prompt: str, sub_context: str | None) -> str:
        """Handle recursive call to sub-RLM instance

        Args:
            sub_prompt: Prompt for the sub-RLM
            sub_context: Optional context override for the sub-RLM

        Returns:
            str: Final message from the sub-RLM

        Raises:
            RuntimeError: If max recursion depth is exceeded
            LLMClientError: If LLM API call fails
        """
        if not self.quiet:
            print(
                f"RLM Has called recursively to depth: {self.current_depth + 1}\nSub-Prompt:{sub_prompt}\nSub-Context Length:{len(sub_context) if sub_context else self.ctx_length}"
            )

        logger.info(
            f"Recursion at depth {self.current_depth} -> {self.current_depth + 1}"
        )

        if not self.disable_guards and self.current_depth >= self.max_depth:
            error_msg = f"Max recursion depth ({self.max_depth}) reached. Cannot recurse further."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

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

    def _run_as_is(self) -> None:
        """Execute a single iteration of the RLM loop

        Raises:
            LLMClientError: If LLM API call fails
            Exception: For other unexpected errors
        """
        try:
            logger.debug("Executing LLM query")
            response = self.llm.get_query(self.messages)

            if not self.quiet:
                print(response)

            queries = utils.extract_lua_code_blocks(response)
            logger.debug(f"Found {len(queries)} Lua code blocks")

            results = []
            for q in queries:
                try:
                    result = self.runtime.execute_query(q)
                    results.append(result)
                except Exception as e:
                    # Capture the error and tell the LLM about it
                    error_msg = f"Error executing Lua code: {e}"
                    logger.error(error_msg)
                    results.append(error_msg)

            # If there were errors, include them in the feedback
            if any(r and "Error" in r for r in results):
                self.messages.append(
                    {
                        "role": "user",
                        "content": "Your code had errors. Please fix them. Errors:\n"
                        + "\n".join(r for r in results if r and "Error" in r),
                    }
                )
            else:
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append(
                    {
                        "role": "user",
                        "content": "Here's the output of the code you provided"
                        + "\n".join(r for r in results if r is not None),
                    }
                )
        except LLMClientError as e:
            logger.error(f"LLM API error in iteration: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in iteration: {type(e).__name__}: {e}")
            raise

    def run(self, max_iter: int = 10) -> None:
        """Run the RLM loop until completion or max iterations

        Args:
            max_iter: Maximum number of iterations (default: 10)

        Raises:
            LLMClientError: If LLM API call fails
            RuntimeError: If max iterations or recursion depth exceeded
        """
        i = 0
        actual_max_iter = float("inf") if self.disable_guards else max_iter
        logger.info(f"Starting RLM run with max_iter={actual_max_iter}")

        while not self.runtime.close_recursion and i < actual_max_iter:
            self._run_as_is()
            print(f"Iteration: {i + 1}")
            i += 1

        if i == actual_max_iter:
            if not self.quiet:
                print("MAX ITERATIONS REACHED, BREAKING EARLY")
            logger.warning(f"Max iterations ({max_iter}) reached")

        print(self.runtime.final_message)
        logger.info(f"RLM run completed with {i} iterations")
