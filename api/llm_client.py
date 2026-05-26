import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


async def call_openrouter(system_prompt: str, user_content: str, model: str | None = None) -> str:
    """
    Send a chat completion request to OpenRouter and return the response content string.

    Raises:
        httpx.HTTPStatusError: on non-200 responses (after logging status + body).
        httpx.RequestError: on network-level failures.
    """
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OPENROUTER_BASE_URL, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(
                "OpenRouter returned status %s: %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        content: str = response.json()["choices"][0]["message"]["content"]
        # Strip markdown code fences some models wrap around JSON despite json_object mode
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            # drop opening fence (```json or ```) and closing fence (```)
            inner = lines[1:] if lines[0].startswith("```") else lines
            if inner and inner[-1].strip() == "```":
                inner = inner[:-1]
            content = "\n".join(inner)
        return content
