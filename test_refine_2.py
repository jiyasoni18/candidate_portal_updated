import asyncio
import json
import urllib.request
import traceback

data = {
    "custom_additions": "",
    "gap_selections": {
        "0": "ADD_TO_PROJECT: Smart parking detection (Tech: AWS) — I have used the AWS for the managment and used there EC2 service"
    },
    "selected_improvements": []
}

req = urllib.request.Request(
    "http://127.0.0.1:8000/practice/session/f50403f6-3bc9-49c4-809f-9d4bc29b2e91/refine",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json", "Authorization": "Bearer TEST"}
)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.reason}")
    print(e.read().decode())
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
