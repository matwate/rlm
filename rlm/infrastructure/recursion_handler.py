import logging
from typing import Callable

logger = logging.getLogger(__name__)


class RecursionHandler:
    """Handles recursion logic and depth management for RLM"""

    def __init__(
        self,
        max_depth: int = 5,
        disable_guards: bool = False,
        ctx_length: int = 0,
    ):
        """Initialize recursion handler

        Args:
            max_depth: Maximum recursion depth (default: 5)
            disable_guards: Disable depth/iteration guards (default: False)
            quiet: Suppress output (default: False)
            ctx_length: Context length for logging (default: 0)
        """
        self.current_depth = 0
        self.disable_guards = disable_guards
        self.ctx_length = ctx_length
        self._sub_rlm_factory: Callable | None = None

    def set_sub_rlm_factory(self, factory: Callable) -> None:
        """Set the factory function for creating sub-RLM instances

        Args:
            factory: Function that creates RLM instances for recursion
        """
        self._sub_rlm_factory = factory

    def handle_recursion(self, sub_prompt: str, sub_context: str | None) -> str:
        """Handle a recursive call to a sub-RLM instance

        Args:
            sub_prompt: Prompt for the sub-RLM
            sub_context: Optional context override for the sub-RLM

        Returns:
            str: Final message from the sub-RLM

        Raises:
            RuntimeError: If max recursion depth is exceeded or factory not set
        """
        logger.info(
            f"Recursion at depth {self.current_depth} -> {self.current_depth + 1}"
        )
        logger.info(f"Sub-Prompt: {sub_prompt}")
        logger.info(
            f"Sub-Context Length: {len(sub_context) if sub_context else self.ctx_length}"
        )

        if not self._sub_rlm_factory:
            error_msg = "Sub-RLM factory not set - cannot create recursive instances"
            raise RuntimeError(error_msg)

        if not self.disable_guards and self.current_depth >= self.max_depth:
            error_msg = f"Max recursion depth ({self.max_depth}) reached. Cannot recurse further."
            raise RuntimeError(error_msg)

        # Create and execute sub-RLM instance
        sub_rlm = self._sub_rlm_factory(
            initial_prompt=sub_prompt,
            initial_context=str(sub_context) if sub_context else "",
            current_depth=self.current_depth + 1,
        )

        sub_rlm.run()
        return sub_rlm.final_message

    def set_depth(self, current: int) -> None:
        """Set the current recursion depth

        Args:
            current: Current recursion depth
        """
        self.current_depth = current
