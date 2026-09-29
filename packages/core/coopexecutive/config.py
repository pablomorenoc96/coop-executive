"""Configuración central de CoopExecutive.

El archivo `.env` se busca en este orden, y el último que exista gana:

1. la carpeta de usuario (`%APPDATA%/CoopExecutive` o `~/.config/coopexecutive`);
2. la raíz del repositorio, solo si se ejecuta desde un checkout;
3. el directorio actual.

`COOPEXECUTIVE_ENV_FILE` sustituye la búsqueda por un archivo concreto; vacío la desactiva.
Las variables de entorno del sistema siempre tienen prioridad sobre cualquier `.env`.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from coopexecutive.utils.rutas import carpeta_usuario, raiz_repositorio

ARCHIVO_PERFIL = "profile.yaml"
ARCHIVO_BASE = "coop_memory.db"

# Nombres vigentes al 29/09/2026. Cambian seguido: cualquier modelo compatible sirve.
MODELO_GRATUITO = "google/gemma-4-31b-it:free"
MODELO_RESPALDO = "nvidia/nemotron-3-super-120b-a12b:free"
MODELO_RAPIDO = "google/gemma-4-26b-a4b-it:free"
MODELOS_LOCALES = "granite4.1:8b,qwen3.8:27b"

# Claves de ejemplo que se tratan como vacías.
CLAVES_DE_EJEMPLO = {"sk-or-v1-tu-clave-aqui", "tu-clave-aqui", "changeme"}


def archivos_env() -> list[Path]:
    """Archivos `.env` que existen, en orden de prioridad creciente."""
    propio = os.environ.get("COOPEXECUTIVE_ENV_FILE")
    if propio is not None:
        ruta = Path(propio).expanduser() if propio.strip() else None
        return [ruta] if ruta is not None and ruta.is_file() else []
    candidatos = [carpeta_usuario() / ".env"]
    raiz = raiz_repositorio()
    if raiz is not None:
        candidatos.append(raiz / ".env")
    candidatos.append(Path.cwd() / ".env")
    vistos: list[Path] = []
    for ruta in candidatos:
        try:
            resuelta = ruta.resolve()
        except OSError:
            continue
        if resuelta.is_file() and resuelta not in vistos:
            vistos.append(resuelta)
    return vistos


def _perfil_por_omision() -> Path:
    raiz = raiz_repositorio()
    return raiz / "company" / ARCHIVO_PERFIL if raiz is not None else carpeta_usuario() / ARCHIVO_PERFIL


def _base_por_omision() -> Path:
    raiz = raiz_repositorio()
    return raiz / "packages" / "core" / ARCHIVO_BASE if raiz is not None else carpeta_usuario() / ARCHIVO_BASE


class Settings(BaseSettings):
    # Sin env_file aquí: get_settings() pasa la lista resuelta por archivos_env().
    model_config = SettingsConfigDict(env_file=None, env_file_encoding="utf-8", extra="ignore")

    # 'auto', 'openrouter', 'openai', 'anthropic', 'gemini', 'groq', 'mistral', 'deepseek', 'local', 'custom'
    provider: str = Field("auto", alias="PROVIDER")

    # --- 1. OpenRouter: modelos gratuitos y de pago con una sola clave ---
    openrouter_enabled: bool = Field(True, alias="OPENROUTER_ENABLED")
    openrouter_api_key: str | None = Field(None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # --- 2. Modelos locales con Ollama: gratis y sin salir del equipo ---
    local_models_enabled: bool = Field(False, alias="LOCAL_MODELS_ENABLED")
    local_base_url: str = Field("http://localhost:11434/v1", alias="LOCAL_BASE_URL")
    local_models: str = Field(MODELOS_LOCALES, alias="LOCAL_MODELS")
    local_timeout_s: float = Field(300.0, alias="LOCAL_TIMEOUT_S")

    # --- 3. APIs de pago (opcionales) ---
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field("https://api.anthropic.com/v1", alias="ANTHROPIC_BASE_URL")
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    gemini_base_url: str = Field("https://generativelanguage.googleapis.com/v1beta/openai", alias="GEMINI_BASE_URL")
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    groq_base_url: str = Field("https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    mistral_api_key: str | None = Field(None, alias="MISTRAL_API_KEY")
    mistral_base_url: str = Field("https://api.mistral.ai/v1", alias="MISTRAL_BASE_URL")
    deepseek_api_key: str | None = Field(None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field("https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")

    # Endpoint compatible con OpenAI (Azure, vLLM, LiteLLM, LM Studio...)
    custom_api_key: str | None = Field(None, alias="CUSTOM_API_KEY")
    custom_base_url: str | None = Field(None, alias="CUSTOM_BASE_URL")

    # Modelos
    default_model: str = Field(MODELO_GRATUITO, alias="DEFAULT_MODEL")
    deep_reasoning_model: str = Field(MODELO_RESPALDO, alias="DEEP_REASONING_MODEL")
    routing_model: str = Field(MODELO_RAPIDO, alias="ROUTING_MODEL")
    request_timeout_s: float = Field(180.0, alias="REQUEST_TIMEOUT_S")
    max_reintentos: int = Field(3, ge=0, le=6, alias="MAX_REINTENTOS")

    # Rutas y memoria
    company_profile_path: Path = Field(default_factory=_perfil_por_omision, alias="COMPANY_PROFILE_PATH")
    episodic_db_path: Path = Field(default_factory=_base_por_omision, alias="EPISODIC_DB_PATH")
    user_timezone: str = Field("America/Mexico_City", alias="USER_TIMEZONE")
    log_level: str = Field("WARNING", alias="LOG_LEVEL")

    # Espacio de trabajo por organización: carpeta con profile.yaml, base de datos y salidas/.
    workspace: Path | None = Field(None, alias="COOPEXECUTIVE_WORKSPACE")

    @model_validator(mode="after")
    def _aplicar_espacio(self) -> Settings:
        """Con un espacio activo, el perfil y la base salen de él.

        Las variables de entorno explícitas COMPANY_PROFILE_PATH y EPISODIC_DB_PATH
        conservan la prioridad (así se aíslan las pruebas).
        """
        if self.workspace is None:
            return self
        self.workspace = Path(self.workspace).expanduser().resolve()
        if not os.environ.get("COMPANY_PROFILE_PATH"):
            self.company_profile_path = self.workspace / ARCHIVO_PERFIL
        if not os.environ.get("EPISODIC_DB_PATH"):
            self.episodic_db_path = self.workspace / ARCHIVO_BASE
        return self

    @field_validator(
        "openrouter_api_key", "openai_api_key", "anthropic_api_key", "gemini_api_key",
        "groq_api_key", "mistral_api_key", "deepseek_api_key", "custom_api_key",
    )
    @classmethod
    def _clave(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return None if not v or v in CLAVES_DE_EJEMPLO else v

    @field_validator("log_level")
    @classmethod
    def _nivel(cls, v: str) -> str:
        v = v.strip().upper()
        return v if v in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") else "WARNING"

    @property
    def carpeta_base(self) -> Path:
        """Carpeta del espacio o, sin espacio, la del perfil."""
        return self.workspace if self.workspace is not None else self.company_profile_path.parent

    @property
    def salidas_dir(self) -> Path:
        """Carpeta de documentos generados."""
        return self.carpeta_base / "salidas"

    @property
    def cache_dir(self) -> Path:
        """Copias locales de lo descargado (monitoreo)."""
        return self.carpeta_base / ".cache"

    @property
    def usa_local(self) -> bool:
        return self.local_models_enabled or self.provider.lower().strip() in ("local", "ollama")

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
_env_cargados: list[Path] = []


def get_settings() -> Settings:
    global _settings, _env_cargados
    if _settings is None:
        _env_cargados = archivos_env()
        _settings = Settings(_env_file=tuple(_env_cargados) or None)  # type: ignore[call-arg]
    return _settings


def env_cargados() -> list[Path]:
    """Archivos `.env` leídos por la configuración activa."""
    get_settings()
    return list(_env_cargados)


def usar_espacio(ruta: str | Path | None) -> None:
    """Activa un espacio de trabajo para el resto del proceso (opción `--espacio` de la CLI)."""
    global _settings
    if ruta is not None:
        os.environ["COOPEXECUTIVE_WORKSPACE"] = str(Path(ruta).expanduser().resolve())
    _settings = None
