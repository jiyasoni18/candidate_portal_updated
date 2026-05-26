import asyncio
import httpx
from config import settings


async def test():
    print("Key prefix:", settings.OPENROUTER_API_KEY[:15] if settings.OPENROUTER_API_KEY else "EMPTY")
    print("Model:", settings.OPENROUTER_MODEL)
    print("Grading model:", settings.GRADING_MODEL)

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {"role": "user", "content": "Respond with valid JSON only: {\"status\": \"ok\"}"}
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 4096,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        print("Status:", r.status_code)
        print("Body:", r.text[:800])


asyncio.run(test())
