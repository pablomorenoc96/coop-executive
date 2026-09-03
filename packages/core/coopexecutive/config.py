"""Configuración central de CoopExecutive."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Proveedor preferido: 'auto', 'openrouter', 'openai', 'anthropic', 'gemini', 'groq', 'mistral', 'deepseek', 'local', 'custom'
    provider: str = Field("auto", alias="PROVIDER")

    # --- 1. OpenRouter (Modelos gratuitos y de pago) ---
    openrouter_enabled: bool = Field(True, alias="OPENROUTER_ENABLED")
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # --- 2. Modelos Locales / Ollama (Gratis y Privado) ---
    local_models_enabled: bool = Field(False, alias="LOCAL_MODELS_ENABLED")
    local_base_url: str = Field("http://localhost:11434/v1", alias="LOCAL_BASE_URL")
    local_models: str = Field("llama3.1:8b,qwen2.5:3b", alias="LOCAL_MODELS")
    local_timeout_s: float = Field(300.0, alias="LOCAL_TIMEOUT_S")

    # --- 3. APIs Comerciales y de Pago (Opcionales) ---
    # OpenAI (gpt-4o, o1, o3-mini, etc.)
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Anthropic (claude-3-7-sonnet, claude-3-5-sonnet, claude-3-5-haiku, etc.)
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field("https://api.anthropic.com/v1", alias="ANTHROPIC_BASE_URL")

    # Google Gemini (gemini-2.0-flash, gemini-1.5-pro, etc.)
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    gemini_base_url: str = Field("https://generativelanguage.googleapis.com/v1beta/openai", alias="GEMINI_BASE_URL")

    # Groq (Inferencia ultra rápida)
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    groq_base_url: str = Field("https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")

    # Mistral AI
    mistral_api_key: str | None = Field(None, alias="MISTRAL_API_KEY")
    mistral_base_url: str = Field("https://api.mistral.ai/v1", alias="MISTRAL_BASE_URL")

    # DeepSeek
    deepseek_api_key: str | None = Field(None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field("https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")

    # Endpoint Genérico / Compatible con OpenAI (Azure, vLLM, etc.)
    custom_api_key: str | None = Field(None, alias="CUSTOM_API_KEY")
    custom_base_url: str | None = Field(None, alias="CUSTOM_BASE_URL")

    # Modelos por defecto
    default_model: str = Field("minimax/minimax-m3:free", alias="DEFAULT_MODEL")
    deep_reasoning_model: str = Field("nvidia/nemotron-3-super-120b-a12b:free", alias="DEEP_REASONING_MODEL")
    routing_model: str = Field("minimax/minimax-m3:free", alias="ROUTING_MODEL")

    # Rutas y memoria
    company_profile_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "company" / "profile.yaml",
        alias="COMPANY_PROFILE_PATH",
    )
    episodic_db_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "packages" / "core" / "coop_memory.db",
        alias="EPISODIC_DB_PATH",
    )
    user_timezone: str = Field("America/Mexico_City", alias="USER_TIMEZONE")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def local_models_list(self) -> list[str]:
        return [m.strip() for m in self.local_models.split(",") if m.strip()]

    @field_validator("user_timezone")
    @classmethod
    def _validate_tz(cls, v: str) -> str:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            return "UTC"
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
