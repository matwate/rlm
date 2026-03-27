import json
import logging
import re

logger = logging.getLogger(__name__)


def lua_escape_string(s: str) -> str:
    """Escape a string for use in Lua code

    Args:
        s: String to escape

    Returns:
        Escaped string safe for Lua
    """
    escaped = json.dumps(s)
    result = escaped[1:-1]
    result = result.replace("'", "\\'")
    return result


def remove_thinking_blocks(s: str) -> str:
    """Remove thinking blocks from model output

    Args:
        s: String possibly containing thinking blocks

    Returns:
        String with thinking blocks removed
    """
    result = s.replace("</think>", "")
    logger.debug(f"Removed thinking blocks, result length: {len(result)}")
    return result


def extract_lua_code_blocks(text: str) -> list[str]:
    """
    Finds all markdown lua code blocks in a string and returns the contents.

    Args:
        text (str): The markdown text to search.

    Returns:
        list: A list of strings, where each string is the content of a lua code block.
    """

    final_match = re.search(r"FINAL\s*(?:\([^)]*\))?\s*\[\[", text)
    if final_match:
        rest = text[final_match.start() :]
        closing = rest.find("]]")
        if closing != -1:
            return [rest[: closing + 2]]

    # Regex pattern breakdown:
    # ```         : Matches the opening three backticks.
    # lua         : Matches the specific language identifier 'lua'.
    # \s*         : Matches optional whitespace (like spaces or the newline after the tag).
    # (.*?)       : Non-greedy capture group for the code content.
    # \s*         : Matches optional whitespace before the closing backticks.
    # ```         : Matches the closing three backticks.
    pattern = r"```lua\s*(.*?)\s*```"

    # re.DOTALL allows the '.' to match newlines, covering multi-line code blocks.
    # re.IGNORECASE ensures it matches 'lua', 'Lua', 'LUA', etc.
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    logger.debug(f"Found {len(matches)} Lua code blocks")

    return list(matches)


def validate_lua_syntax(code: str) -> list[str]:
    """
    Validate basic Lua syntax and return list of common Python-style errors.

    Args:
        code (str): The Lua code to validate.

    Returns:
        list: A list of error messages describing potential syntax issues.
    """
    errors = []

    if "len(" in code:
        errors.append("Found Python len(), use # instead")

    if "for " in code and " in " in code and "for i = " not in code:
        errors.append("Found Python-style 'for x in y', use ipairs() for tables")

    if "if " in code and "{" in code and " then " not in code:
        errors.append("Found Python-style 'if x { ... }', use 'if x then ... end'")

    if "+= " in code or "-= " in code:
        errors.append("Found Python compound operators (+=, -=), not supported in Lua")

    if " != " in code or " !=\n" in code:
        errors.append("Found Python !=, use ~= instead")

    if 'print(f"' in code or "print(f'" in code:
        errors.append(
            "Found Python f-strings, use string concatenation with .. instead"
        )

    if errors:
        logger.debug(f"Lua validation errors: {errors}")

    return errors
