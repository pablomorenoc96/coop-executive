"""Orquestador Ejecutivo Colegiado de CoopExecutive."""
from __future__ import annotations

from typing import AsyncIterator
from coopexecutive.config import get_settings
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.memory.episodic import initialize_db
from coopexecutive.prompts.cooperative_persona import COOPERATIVE_PERSONA_PROMPT
from coopexecutive.prompts.domain_prompts import (
    VIGILANCIA_PROMPT,
    LEGAL_SOCIAL_PROMPT,
    FINANZAS_SOLIDARIAS_PROMPT,
    DESARROLLO_TECNICO_PROMPT,
    COMUNICACION_SOCIAL_PROMPT,
    SECRETARIA_ASAMBLEA_PROMPT,
)
from coopexecutive.prompts.grant_procurement import GRANT_PROCUREMENT_PROMPT
from coopexecutive.providers.client import AIClient


class CoopExecutive:
    def __init__(self) -> None:
        initialize_db()
        self.settings = get_settings()
        self.profile = CoopProfile.load_from_yaml(self.settings.company_profile_path)
        self.client = AIClient()

    def build_system_prompt(self, specialist_focus: str | None = None) -> str:
        base = COOPERATIVE_PERSONA_PROMPT.replace("{VOICE_PERSONA}", "")
        profile_block = self.profile.to_prompt_block()
        
        specialist_text = ""
        if specialist_focus == "procurador":
            specialist_text = f"\n\n### Modo Activo: Agente Procurador de Fondos\n{GRANT_PROCUREMENT_PROMPT}"
        elif specialist_focus == "vigilancia":
            specialist_text = f"\n\n### Modo Activo: Consejo de Vigilancia\n{VIGILANCIA_PROMPT}"
        elif specialist_focus == "legal":
            specialist_text = f"\n\n### Modo Activo: Asesoría Jurídica en Economía Social\n{LEGAL_SOCIAL_PROMPT}"
        elif specialist_focus == "finanzas":
            specialist_text = f"\n\n### Modo Activo: Finanzas Solidarias y Fondos Estatutarios\n{FINANZAS_SOLIDARIAS_PROMPT}"
        elif specialist_focus == "tecnico":
            specialist_text = f"\n\n### Modo Activo: Soberanía Técnica y Tecnológica\n{DESARROLLO_TECNICO_PROMPT}"
        elif specialist_focus == "asamblea":
            specialist_text = f"\n\n### Modo Activo: Secretaría de Actas y Gobernanza\n{SECRETARIA_ASAMBLEA_PROMPT}"

        return f"{base}\n\n{profile_block}{specialist_text}"

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
