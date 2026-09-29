"""Orquestador Ejecutivo Colegiado de CoopExecutive."""
from __future__ import annotations

from collections.abc import AsyncIterator

from coopexecutive.config import get_settings
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.memory.episodic import initialize_db
from coopexecutive.prompts.cooperative_persona import COOPERATIVE_PERSONA_PROMPT, ORGANIZATION_PERSONA_PROMPT
from coopexecutive.prompts.domain_prompts import (
    COMUNICACION_SOCIAL_PROMPT,
    DESARROLLO_TECNICO_PROMPT,
    FINANZAS_SOLIDARIAS_PROMPT,
    LEGAL_SOCIAL_PROMPT,
    SECRETARIA_ASAMBLEA_PROMPT,
    VIGILANCIA_PROMPT,
)
from coopexecutive.prompts.grant_procurement import GRANT_PROCUREMENT_PROMPT
from coopexecutive.providers.client import AIClient
from coopexecutive.utils.fechas import fecha_larga, hoy_local

# Especialistas que se pueden enfocar con --rol: nombre -> (título del modo, instrucciones).
ROLES: dict[str, tuple[str, str]] = {
    "procurador": ("Agente Procurador de Fondos", GRANT_PROCUREMENT_PROMPT),
    "vigilancia": ("Consejo de Vigilancia", VIGILANCIA_PROMPT),
    "legal": ("Asesoría Jurídica en Economía Social", LEGAL_SOCIAL_PROMPT),
    "finanzas": ("Finanzas Solidarias y Fondos Estatutarios", FINANZAS_SOLIDARIAS_PROMPT),
    "tecnico": ("Soberanía Técnica y Tecnológica", DESARROLLO_TECNICO_PROMPT),
    "comunicacion": ("Comunicación Social y Rendición de Cuentas", COMUNICACION_SOCIAL_PROMPT),
    "asamblea": ("Secretaría de Actas y Gobernanza", SECRETARIA_ASAMBLEA_PROMPT),
}


class CoopExecutive:
    def __init__(self) -> None:
        initialize_db()
        self.settings = get_settings()
        self.profile = CoopProfile.load_from_yaml(self.settings.company_profile_path)
        self.client = AIClient()

    def build_system_prompt(self, specialist_focus: str | None = None) -> str:
        if self.profile.es_cooperativa:
            base = COOPERATIVE_PERSONA_PROMPT.replace("{VOICE_PERSONA}", "")
        else:
            base = ORGANIZATION_PERSONA_PROMPT
        profile_block = self.profile.to_prompt_block()

        specialist_text = ""
        if specialist_focus in ROLES:
            titulo, prompt = ROLES[specialist_focus]
            specialist_text = f"\n\n### Modo Activo: {titulo}\n{prompt}"

        zona = self.settings.user_timezone
        fecha = f"**Fecha de hoy:** {fecha_larga(hoy_local(zona))} (zona horaria {zona})."
        return f"{base}\n\n{fecha}\n\n{profile_block}{specialist_text}"

    async def stream_chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
        specialist_focus: str | None = None,
    ) -> AsyncIterator[str]:
        system_prompt = self.build_system_prompt(specialist_focus)
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        async for chunk in self.client.stream_chat(messages):
            yield chunk
