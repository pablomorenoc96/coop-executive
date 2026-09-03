"""Cliente de inferencia universal con soporte para proveedores gratuitos y de pago.

Soporta:
- OpenRouter (Gratis y de Pago)
- Ollama (Local sin internet)
- OpenAI (GPT-4o, o1, o3-mini)
- Anthropic (Claude 3.7 Sonnet, Claude 3.5 Haiku)
- Google Gemini (Gemini 2.0 Flash, Gemini 1.5 Pro)
- Groq, Mistral, DeepSeek y Endpoints Personalizados compatibles con OpenAI.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator
import httpx
from coopexecutive.config import get_settings


class AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def resolve_provider(self, target_model: str) -> tuple[str, str, dict[str, str]]:
        """Determina el proveedor, la URL base y las cabeceras según el modelo y las claves configuradas."""
        prov = self.settings.provider.lower().strip()

        # 1. Modo Local Forzado
        if self.settings.local_models_enabled or prov in ("local", "ollama"):
            return "openai_compat", f"{self.settings.local_base_url.rstrip('/')}/chat/completions", {"Content-Type": "application/json"}

        # 2. Modo Custom Forzado o Detectado
        if prov == "custom" or (self.settings.custom_base_url and not prov):
            base = (self.settings.custom_base_url or "http://localhost:8000/v1").rstrip("/")
            hdrs = {"Content-Type": "application/json"}
            if self.settings.custom_api_key:
                hdrs["Authorization"] = f"Bearer {self.settings.custom_api_key}"
            return "openai_compat", f"{base}/chat/completions", hdrs

        # 3. Detección Automática o Proveedor Específico

        # Anthropic Directo
        if prov == "anthropic" or (prov == "auto" and self.settings.anthropic_api_key and target_model.startswith("claude-")):
            api_key = self.settings.anthropic_api_key or ""
            return "anthropic", f"{self.settings.anthropic_base_url.rstrip('/')}/messages", {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

        # OpenAI Directo
        if prov == "openai" or (prov == "auto" and self.settings.openai_api_key and (target_model.startswith("gpt-") or target_model.startswith("o1") or target_model.startswith("o3-"))):
            api_key = self.settings.openai_api_key or ""
            return "openai_compat", f"{self.settings.openai_base_url.rstrip('/')}/chat/completions", {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

        # Google Gemini Directo (Endpoint compatible OpenAI)
        if prov == "gemini" or (prov == "auto" and self.settings.gemini_api_key and target_model.startswith("gemini-")):
            api_key = self.settings.gemini_api_key or ""
            return "openai_compat", f"{self.settings.gemini_base_url.rstrip('/')}/chat/completions", {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

        # Groq Directo
        if prov == "groq" or (prov == "auto" and self.settings.groq_api_key and ("groq" in target_model or "llama-3" in target_model)):
            api_key = self.settings.groq_api_key or ""
            return "openai_compat", f"{self.settings.groq_base_url.rstrip('/')}/chat/completions", {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

        # DeepSeek Directo
        if prov == "deepseek" or (prov == "auto" and self.settings.deepseek_api_key and "deepseek" in target_model):
            api_key = self.settings.deepseek_api_key or ""
            return "openai_compat", f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions", {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

        # Mistral Directo
        if prov == "mistral" or (prov == "auto" and self.settings.mistral_api_key and "mistral" in target_model):
            api_key = self.settings.mistral_api_key or ""
            return "openai_compat", f"{self.settings.mistral_base_url.rstrip('/')}/chat/completions", {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

        # OpenRouter (Predeterminado para modelos gratuitos y comerciales multi-modelo)
        hdrs = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pablomorenoc96/coop-executive",
            "X-Title": "CoopExecutive",
        }
        if self.settings.openrouter_api_key:
            hdrs["Authorization"] = f"Bearer {self.settings.openrouter_api_key}"
        return "openai_compat", f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions", hdrs

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        target_model = model or self.settings.default_model

        candidate_models = [target_model]
        if target_model != self.settings.deep_reasoning_model:
            candidate_models.append(self.settings.deep_reasoning_model)

        async with httpx.AsyncClient(timeout=180.0) as client:
            for mod in candidate_models:
                flavor, endpoint, headers = self.resolve_provider(mod)

                if flavor == "anthropic":
                    # Formato nativo Anthropic
                    # Extraer system prompt si existe
                    sys_prompt = ""
                    clean_msgs = []
                    for m in messages:
                        if m.get("role") == "system":
                            sys_prompt += m.get("content", "") + "\n"
                        else:
                            clean_msgs.append(m)

                    payload: dict[str, Any] = {
                        "model": mod,
                        "messages": clean_msgs,
                        "max_tokens": 4096,
                        "temperature": temperature,
                        "stream": True,
                    }
                    if sys_prompt:
                        payload["system"] = sys_prompt.strip()

                    async with client.stream(
                        "POST",
                        endpoint,
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code == 429 and mod != candidate_models[-1]:
                            continue
                        if response.status_code != 200:
                            err_text = await response.aread()
                            yield f"\n[Error {response.status_code} Anthropic]: {err_text.decode('utf-8', errors='replace')}\n"
                            return

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[len("data: "):].strip()
                            try:
                                chunk = json.loads(data_str)
                                chunk_type = chunk.get("type")
                                if chunk_type == "content_block_delta":
                                    text = chunk.get("delta", {}).get("text", "")
                                    if text:
                                        yield text
                            except Exception:
                                continue
                        return

                else:
                    # Formato estándar OpenAI / OpenRouter / Ollama / Gemini / Groq / DeepSeek
                    payload = {
                        "model": mod,
                        "messages": messages,
                        "temperature": temperature,
                        "stream": True,
                    }
                    if tools:
                        payload["tools"] = tools

                    async with client.stream(
                        "POST",
                        endpoint,
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code == 429 and mod != candidate_models[-1]:
                            # Fallback silencioso al siguiente modelo configurado
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
