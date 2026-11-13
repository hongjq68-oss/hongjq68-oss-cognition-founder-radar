"""Optional LLM provider (OpenAI or Anthropic) for research summarisation. Keys come from the environment only."""
import json
import os
import re

import httpx


def provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    return json.loads(text[text.find("{"):])


async def complete_json(system: str, user: str, max_tokens: int = 1500) -> dict:
    p = provider()
    async with httpx.AsyncClient(timeout=90) as c:
        if p == "openai":
            r = await c.post("https://api.openai.com/v1/chat/completions",
                             headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                             json={"model": os.environ.get("OPENAI_MODEL", "gpt-4o"), "response_format": {"type": "json_object"},
                                   "temperature": 0.2, "max_tokens": max_tokens,
                                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            r.raise_for_status()
            return _extract_json(r.json()["choices"][0]["message"]["content"])
        if p == "anthropic":
            r = await c.post("https://api.anthropic.com/v1/messages",
                             headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                             json={"model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"), "max_tokens": max_tokens, "temperature": 0.2,
                                   "system": system + "\nRespond with one valid JSON object only.",
                                   "messages": [{"role": "user", "content": user}]})
            r.raise_for_status()
            return _extract_json("".join(b.get("text", "") for b in r.json()["content"]))
    raise RuntimeError("No LLM provider configured")
