import zai

from config import API_KEY, BASE_URL, MODEL
from prompts import build_sys_prompt


class ZaiClient:
    def __init__(self):
        self.client = zai.ZaiClient(api_key=API_KEY, base_url=BASE_URL)

    def _clean_markdown(self, content):
        lines = content.split("\n")
        cleaned = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```") or line.strip().endswith("```"):
                in_code_block = not in_code_block
                continue
            if not in_code_block:
                cleaned.append(line)
        return "\n".join(cleaned).strip()

    def get_query(self, messages):
        response = self.client.chat.completions.create(model=MODEL, messages=messages)
        content = response.choices[0].message.content
        return self._clean_markdown(content)
