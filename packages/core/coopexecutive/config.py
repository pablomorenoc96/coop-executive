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

    # Proveedores de IA
    openrouter_enabled: bool = Field(True, alias="OPENROUTER_ENABLED")
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    local_models_enabled: bool = Field(False, alias="LOCAL_MODELS_ENABLED")
    local_base_url: str = Field("http://localhost:11434/v1", alias="LOCAL_BASE_URL")
    local_models: str = Field("llama3.1:8b,qwen2.5:3b", alias="LOCAL_MODELS")
    local_timeout_s: float = Field(300.0, alias="LOCAL_TIMEOUT_S")

    # Modelos
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
