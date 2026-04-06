import logging
import re
from typing import Optional

from rlm.exceptions import LLMClientError
from rlm.infrastructure.api_client import LLMClient
from rlm.infrastructure.config import Config, create_config
from rlm.infrastructure.message_manager import MessageManager
from rlm.infrastructure.recursion_handler import RecursionHandler
from rlm.lua.lua_runtime import LuaRuntimeWrapper

logger = logging.getLogger(__name__)


class RLM:
    def __init__(
        self,
        initial_prompt: str,
        initial_context: str = "",
        current_depth: int = 0,
        init_ai: bool = True,
        query_callback=None,
        config: Optional[Config] = None,
    ):
        """Initialize RLM (Recursive Language Model) instance

        Args:
            initial_prompt: The initial prompt for the LLM
            initial_context: Initial context string for analysis
            max_depth: Maximum recursion depth (default: 5)
            current_depth: Current recursion depth (default: 0)
            disable_guards: Disable recursion/iteration guards (default: False)
            init_ai: Initialize AI components (LLM, message manager, recursion) (default: True)
            query_callback: Callback function for tracking Lua queries (query, result, output) -> None
        """
        self.init_ai = init_ai
        self.query_callback = query_callback
        self.config = config or create_config()
        max_depth = self.config.max_depth

        if init_ai:
            self.llm = LLMClient(config=self.config)
            logger.debug("LLM Client Initialized")

            # Initialize recursion handler
            self.recursion_handler = RecursionHandler(
                max_depth, self.config.max_iters == -1, len(initial_context)
            )
            self.recursion_handler.set_depth(current_depth)
            self.recursion_handler.set_sub_rlm_factory(self._create_sub_rlm)

            # Handle prompt/context relationship
            if initial_prompt and not initial_context:
                initial_context = initial_prompt

            # Initialize message manager
            self.message_manager = MessageManager(
                initial_prompt, initial_context, current_depth
            )

            # Initialize Lua runtime with recursion callback
            self.runtime = LuaRuntimeWrapper(
                recursion_callback=self.recursion_handler.handle_recursion,
                enable_ai_features=True,
            )

            logger.debug("Lua Runtime Initialized")
        else:
            # Initialize Lua runtime without AI features
            self.runtime = LuaRuntimeWrapper(
                recursion_callback=None, enable_ai_features=False
            )

        # Set up Lua environment
        self.runtime.set_variable("prompt", initial_prompt)
        self.runtime.set_variable("context", initial_context)
        self.runtime.set_depth(current_depth, max_depth)

        logger.debug("Lua Runtime Initialized")
        # Store final message property reference
        self._final_message = ""

        logger.info(f"Initialized RLM at depth {current_depth}/{max_depth}")

    def _create_sub_rlm(
        self,
        initial_prompt: str,
        initial_context: str,
        current_depth: int,
    ) -> "RLM":
        """Factory method to create sub-RLM instances for recursion

        Args:
            initial_prompt: Prompt for the sub-RLM
            initial_context: Context for the sub-RLM
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth for the sub-RLM

        Returns:
            RLM: New RLM instance configured for the recursion
        """
        return RLM(
            initial_prompt=initial_prompt,
            initial_context=initial_context,
            current_depth=current_depth,
        )

    @property
    def final_message(self) -> str:
        """Get the final message from the RLM run"""
        return self._final_message

    def _run_iteration(self) -> bool:
        """Execute a single iteration of the RLM loop

        Returns:
            bool: True if should stop (FINAL called), False otherwise

        Raises:
            LLMClientError: If LLM API call fails
            Exception: For other unexpected errors
        """
        try:
            logger.debug("Executing LLM query")
            response = self.llm.get_query(self.message_manager.get_messages())
            logger.debug(response)
            queries = re.findall(
                r"```lua\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE
            )
            logger.debug(f"Found {len(queries)} Lua code blocks")

            results = []
            for q in queries:
                try:
                    captured_output_copy = list(self.runtime.captured_output)
                    result = self.runtime.execute_query(q)
                    if self.runtime.captured_output:
                        logger.debug(self.runtime.captured_output)
                    results.append(result)

                    if self.query_callback:
                        self.query_callback(q, result, captured_output_copy)

                    if self.runtime.close_recursion:
                        logger.info(
                            "FINAL() called, stopping execution of remaining code blocks"
                        )
                        return True
                except Exception as e:
                    error_msg = f"Error executing Lua code: {e}"
                    logger.error(error_msg)
                    results.append(error_msg)

                    if self.query_callback:
                        self.query_callback(q, error_msg, [])

            # Check for FINAL in plain text
            if not self.runtime.close_recursion and "FINAL(" in response:
                final_match = re.search(
                    r"FINAL\s*\(\s*\[\[(.*?)\]\]\s*\)", response, re.DOTALL
                )
                if final_match:
                    self.runtime.close_recursion = True
                    self.runtime.final_message = final_match.group(1)
                    logger.info("FINAL() found in plain text, stopping execution")
                    return True

            if self.runtime.close_recursion:
                logger.info("FINAL() called, skipping message processing")
                return True

            # Process results and update message history
            if any(
                r
                and (
                    r.startswith("Error executing Lua code:")
                    or r.startswith("Lua Syntax Error:")
                    or r.startswith("Lua Error:")
                    or r.startswith("Unexpected Error:")
                )
                for r in results
            ):
                # There were errors, ask for fixes
                error_feedback = (
                    "Your code had errors. Please fix them. Errors:\n"
                    + "\n".join(r for r in results if r and "Error" in r)
                )
                self.message_manager.add_user_message(error_feedback)
            else:
                # Success, add assistant message and output
                self.message_manager.add_assistant_message(response)
                output = "\n".join(r for r in results if r is not None)
                self.message_manager.add_user_message(
                    "Here's the output of the code you provided" + output
                )

            return False

        except LLMClientError as e:
            logger.error(f"LLM API error in iteration: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in iteration: {type(e).__name__}: {e}")
            raise

    def run(self) -> None:
        """Run the RLM loop until completion or max iterations

        Args:
            max_iter: Maximum number of iterations (default: 10)

        Raises:
            LLMClientError: If LLM API call fails
            RuntimeError: If max iterations or recursion depth exceeded

        """
        max_iter = self.config.max_iters
        i = 0
        actual_max_iter = float("inf") if max_iter == -1 else max_iter
        logger.info(f"Starting RLM run with max_iter={actual_max_iter}")

        while not self.runtime.close_recursion and i < actual_max_iter:
            should_end = self._run_iteration()
            if should_end:
                logger.debug(self.runtime.captured_output)
                break
            i += 1

        if i == actual_max_iter:
            logger.debug("MAX ITERATIONS REACHED, BREAKING EARLY")
            logger.warning(f"Max iterations ({max_iter}) reached")

        self._final_message = self.runtime.final_message
        logger.info(f"RLM run completed with {i} iterations")
