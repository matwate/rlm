from rlm.prompts import build_sub_sys_prompt, build_sys_prompt


class MessageManager:
    """Manages message history for LLM interactions"""

    def __init__(self, initial_prompt: str, initial_context: str, depth: int = 0):
        """Initialize message manager with initial context

        Args:
            initial_prompt: The initial prompt for the LLM
            initial_context: Initial context string for analysis
            depth: Current recursion depth (default: 0)
        """
        self.messages: list[dict[str, str]] = []
        self.ctx_length = len(initial_context)
        self.depth = depth

        # Select appropriate system prompt based on depth
        sys_prompt = build_sub_sys_prompt() if depth > 0 else build_sys_prompt()

        # Add developer message with system prompt
        self.messages.append({"role": "developer", "content": sys_prompt})

        # Add user message with prompt and context instructions
        user_content = f"""{initial_prompt}

The context you need to analyze is available in the `context` variable in the Lua environment. Write Lua code to access and analyze it."""
        self.messages.append({"role": "user", "content": user_content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history

        Args:
            content: The assistant's response content
        """
        self.messages.append({"role": "assistant", "content": content})

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history

        Args:
            content: The user's message content
        """
        self.messages.append({"role": "user", "content": content})

    def get_messages(self) -> list[dict[str, str]]:
        """Get the current message history

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        return self.messages
