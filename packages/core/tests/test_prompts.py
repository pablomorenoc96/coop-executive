import pytest

from coopexecutive.orchestrator.coop_executive import CoopExecutive
from coopexecutive.prompts.domain_prompts import (
    COMUNICACION_SOCIAL_PROMPT,
    DESARROLLO_TECNICO_PROMPT,
    FINANZAS_SOLIDARIAS_PROMPT,
    LEGAL_SOCIAL_PROMPT,
    SECRETARIA_ASAMBLEA_PROMPT,
    VIGILANCIA_PROMPT,
)
from coopexecutive.prompts.grant_procurement import GRANT_PROCUREMENT_PROMPT


@pytest.mark.parametrize(
    "rol, prompt",
    [
        ("procurador", GRANT_PROCUREMENT_PROMPT),
        ("vigilancia", VIGILANCIA_PROMPT),
        ("legal", LEGAL_SOCIAL_PROMPT),
        ("finanzas", FINANZAS_SOLIDARIAS_PROMPT),
        ("tecnico", DESARROLLO_TECNICO_PROMPT),
        ("comunicacion", COMUNICACION_SOCIAL_PROMPT),
        ("asamblea", SECRETARIA_ASAMBLEA_PROMPT),
    ],
)
def test_cada_rol_llega_a_su_prompt(entorno_aislado, rol, prompt):
    system = CoopExecutive().build_system_prompt(rol)
    assert prompt in system
    assert "Cooperativa de Prueba" in system


def test_sin_rol_no_agrega_especialista(entorno_aislado):
    assert "Modo Activo" not in CoopExecutive().build_system_prompt(None)


def test_prompt_de_procuracion_cabe_en_8000():
    assert len(GRANT_PROCUREMENT_PROMPT) <= 8000


def test_system_prompt_lleva_fecha_y_zona(entorno_aislado):
    system = CoopExecutive().build_system_prompt("procurador")
    assert "Fecha de hoy" in system
    assert "zona horaria" in system


def test_perfil_no_cooperativo_sin_fondos_estatutarios(entorno_aislado, tmp_path, monkeypatch):
    import coopexecutive.config as config

    perfil = tmp_path / "pf.yaml"
    perfil.write_text(
        "name: Taller de Prueba\ntipo_organizacion: persona_fisica\n"
        "legal_structure: Persona física con actividad empresarial\nmission: Servir.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COMPANY_PROFILE_PATH", str(perfil))
    monkeypatch.setattr(config, "_settings", None)
    system = CoopExecutive().build_system_prompt("procurador")
    assert "Taller de Prueba" in system
    assert "Fondos Estatutarios" not in system
    assert "Asamblea General" not in system
    assert "Fondos Estatutarios" in _sistema_cooperativa(monkeypatch, entorno_aislado)


def _sistema_cooperativa(monkeypatch, carpeta) -> str:
    import coopexecutive.config as config

    monkeypatch.setenv("COMPANY_PROFILE_PATH", str(carpeta / "profile.yaml"))
    monkeypatch.setattr(config, "_settings", None)
    return CoopExecutive().build_system_prompt("procurador")
