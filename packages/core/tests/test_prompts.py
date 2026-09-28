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
