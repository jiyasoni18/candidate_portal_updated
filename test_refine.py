import asyncio
import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/practice/session/00000000-0000-0000-0000-000000000000/refine",
    data=json.dumps({
        "custom_additions": "",
        "gap_selections": {},
        "selected_improvements": []
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
