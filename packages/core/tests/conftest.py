from pathlib import Path

import pytest

import coopexecutive.config as config

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
