import os
from pathlib import Path

import pytest

import coopexecutive.config as config
from coopexecutive.orchestrator.coop_executive import CoopExecutive
from coopexecutive.providers.client import AIClient
from coopexecutive.providers.tipos import Fin, TextoDelta

PERFIL_PRUEBA = """name: "Cooperativa de Prueba"
legal_structure: "S.C. de R.L."
regime: "Economía Social"
mission: "Impulsar el bienestar común."
focus_areas:
  - "Energía comunitaria"
"""


@pytest.fixture
def entorno_aislado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base de datos y perfil temporales; nunca toca coop_memory.db ni company/profile.yaml."""
    perfil = tmp_path / "profile.yaml"
    perfil.write_text(PERFIL_PRUEBA, encoding="utf-8")
    monkeypatch.setenv("EPISODIC_DB_PATH", str(tmp_path / "test_memory.db"))
    monkeypatch.setenv("COMPANY_PROFILE_PATH", str(perfil))
    monkeypatch.setenv("USER_TIMEZONE", "America/Mexico_City")
    monkeypatch.setattr(config, "_settings", None)
    return tmp_path


@pytest.fixture(autouse=True)
def _sin_espacio_residual(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    """Ninguna prueba lee el .env real ni la carpeta de usuario; `usar_espacio` se limpia al final."""
    monkeypatch.setenv("COOPEXECUTIVE_ENV_FILE", "")
    monkeypatch.setenv("COOPEXECUTIVE_HOME", str(tmp_path_factory.mktemp("usuario")))
    for variable in ("PROVIDER", "LOCAL_MODELS_ENABLED", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                     "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
                     "DEEPSEEK_API_KEY", "CUSTOM_API_KEY", "CUSTOM_BASE_URL", "DEFAULT_MODEL",
                     "DEEP_REASONING_MODEL", "OPENROUTER_ENABLED"):
        monkeypatch.delenv(variable, raising=False)
    config._settings = None
    yield
    os.environ.pop("COOPEXECUTIVE_WORKSPACE", None)
    config._settings = None


@pytest.fixture
def respuestas_modelo(monkeypatch):
    """Sustituye al modelo: cada llamada devuelve la siguiente respuesta de la cola.

    Un texto es la respuesta completa. Una lista de eventos (`TextoDelta`,
    `LlamadaHerramienta`) es un paso del agente con herramientas.
    """
    cola: list = []

    async def falso(self, mensaje, history=None, specialist_focus=None):
        siguiente = cola.pop(0)
        yield siguiente if isinstance(siguiente, str) else "".join(
            e.texto for e in siguiente if isinstance(e, TextoDelta))

    async def eventos(self, messages, model=None, temperature=0.2, tools=None, max_tokens=4096):
        siguiente = cola.pop(0)
        for evento in [TextoDelta(siguiente)] if isinstance(siguiente, str) else siguiente:
            yield evento
        yield Fin(motivo="stop", modelo="falso", proveedor="prueba")

    monkeypatch.setattr(CoopExecutive, "stream_chat", falso)
    monkeypatch.setattr(AIClient, "eventos", eventos)
    return cola
