import json


def lua_escape_string(s: str):
    escaped = json.dumps(s)
    result = escaped[1:-1]
    result = result.replace("'", "\\'")
    return result


def remove_thinking_blocks(s: str):
    return s.replace("</think>", "")
