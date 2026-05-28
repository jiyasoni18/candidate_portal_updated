import re

def _strip_markdown_json(text: str) -> str:
    # Find anything between ```json and ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    # Or just return text if no fences found
    return text.strip()

print(_strip_markdown_json("Here is the JSON:\n```json\n{\"foo\": \"bar\"}\n```\nEnjoy!"))
