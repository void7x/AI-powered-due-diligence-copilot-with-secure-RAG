"""LLM abstraction. OpenAI when configured; a deterministic offline fallback keeps
the entire product runnable without API keys (dev/demo/CI)."""
from __future__ import annotations

import json
import re

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger("app.llm")


class LLMUnavailable(Exception):
    pass


class LLMService:
    provider = "offline"
    available = False

    def complete_json(self, system: str, user: str, *, max_tokens: int = 1400) -> dict:
        raise LLMUnavailable("LLM provider is not configured")


class OpenAILLMService(LLMService):
    provider = "openai"
    available = True

    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        self.model = settings.openai_chat_model
        self.temperature = settings.llm_temperature

    def complete_json(self, system: str, user: str, *, max_tokens: int = 1400) -> dict:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = resp.choices[0].message.content or "{}"
        return _parse_json_loose(content)


def _parse_json_loose(content: str) -> dict:
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                pass
    log.warning("LLM returned non-JSON content (%d chars)", len(content))
    return {}


def get_llm_service(settings: Settings) -> LLMService:
    if settings.ai_provider == "offline":
        return LLMService()
    if settings.ai_provider == "openai" or (settings.ai_provider == "auto" and settings.openai_api_key):
        try:
            return OpenAILLMService(settings)
        except Exception as exc:  # noqa: BLE001
            log.warning("OpenAI LLM unavailable (%s); using offline provider", exc)
    return LLMService()
