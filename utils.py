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

    return [fix_lua_loops(m) for m in matches]


def fix_lua_loops(code_string):
    """
    Converts Python-style for loops into Lua ipairs syntax.
    Fixes the issue where method colons (e.g. :gmatch) were confused for loop terminators.
    """

    def replacer(match):
        var_name = match.group(1)
        iterator = match.group(2)

        # If variable is 'i', use '_' to avoid 'for i, i in ...'
        index_name = "i"
        if var_name == "i":
            index_name = "_"

        return f"for {index_name}, {var_name} in ipairs({iterator}) do"

    # Regex Breakdown:
    # for\s+(\w+)\s+in\s+(.*?)   -> Standard "for x in y" capture
    # \s*                         -> Optional whitespace
    # (?:                         -> Start non-capturing group for terminators
    #   do                        -> Match "do"
    #   |                         -> OR
    #   :(?!\w)                   -> Match ":" ONLY if NOT followed by a letter/number/underscore
    # )                           -> This prevents matching the ":" in "obj:method()"
    pattern = r"for\s+(\w+)\s+in\s+(.*?)\s*(?:do|:(?!\w))"

    return re.sub(pattern, replacer, code_string, flags=re.DOTALL)
