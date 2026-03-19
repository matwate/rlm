import json
import re


def lua_escape_string(s: str):
    escaped = json.dumps(s)
    result = escaped[1:-1]
    result = result.replace("'", "\\'")
    return result


def remove_thinking_blocks(s: str):
    return s.replace("</think>", "")


def extract_lua_code_blocks(text):
    """
    Finds all markdown lua code blocks in a string and returns the contents.

    Args:
        text (str): The markdown text to search.

    Returns:
        list: A list of strings, where each string is the content of a lua code block.
    """
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

    return matches
