"""Shared Azure OpenAI chat-completion client.

The configured deployment is a reasoning model that emits a `reasoning_content`
trace before the final answer, which can take several minutes for large
extraction tasks. Callers running inside a request/response cycle should keep
this in mind (e.g. stream the response, or run from a Celery task).
"""

from collections.abc import AsyncIterator

import httpx

from config import settings

DEFAULT_TIMEOUT = 300.0


async def chat_completion(messages: list[dict], *, temperature: float = 0.1, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Run a non-streaming chat completion and return the final answer text."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        response = await client.post(
            f"{settings.azure_openai_endpoint}/chat/completions",
            headers={"api-key": settings.azure_openai_key, "Content-Type": "application/json"},
            json={"model": settings.azure_openai_deployment, "messages": messages, "temperature": temperature},
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def chat_completion_stream(
    messages: list[dict], *, temperature: float = 0.1, timeout: float = DEFAULT_TIMEOUT
) -> AsyncIterator[str]:
    """Run a streaming chat completion, yielding content tokens as they arrive.

    Skips `reasoning_content` deltas (the reasoning model's thinking trace) and
    yields only `content` deltas.
    """
    import json

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        async with client.stream(
            "POST",
            f"{settings.azure_openai_endpoint}/chat/completions",
            headers={"api-key": settings.azure_openai_key, "Content-Type": "application/json"},
            json={
                "model": settings.azure_openai_deployment,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                content = choices[0].get("delta", {}).get("content")
                if content:
                    yield content
