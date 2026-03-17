import json


def lua_escape_string(s):
    escaped = json.dumps(s)
    result = escaped[1:-1]
    result = result.replace("'", "\\'")
    return result
