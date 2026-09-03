"""Cliente de inferencia universal para OpenRouter y Ollama."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator
import httpx
from coopexecutive.config import get_settings


class AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def base_url(self) -> str:
        if self.settings.local_models_enabled:
            return self.settings.local_base_url.rstrip("/")
        return self.settings.openrouter_base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        hdrs = {"Content-Type": "application/json"}
        if self.settings.local_models_enabled:
            return hdrs
        if self.settings.openrouter_api_key:
            hdrs["Authorization"] = f"Bearer {self.settings.openrouter_api_key}"
            hdrs["HTTP-Referer"] = "https://github.com/pablomorenoc96/coop-executive"
            hdrs["X-Title"] = "CoopExecutive"
        return hdrs

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        target_model = model or self.settings.default_model
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        candidate_models = [target_model]
        if target_model != self.settings.deep_reasoning_model:
            candidate_models.append(self.settings.deep_reasoning_model)

        async with httpx.AsyncClient(timeout=180.0) as client:
            for mod in candidate_models:
                payload["model"] = mod
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    if response.status_code == 429 and mod != candidate_models[-1]:
                        # Fallback silently to backup model
                        continue
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield f"\n[Error {response.status_code}]: {err_text.decode('utf-8', errors='replace')}\n"
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choice = chunk.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue
                    return
