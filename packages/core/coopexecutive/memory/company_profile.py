"""Cargador y formateador de perfil de organización cooperativa o civil."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class StatutoryFunds(BaseModel):
    reserve_fund_pct: float = 15.0
    social_welfare_fund_pct: float = 10.0
    education_fund_pct: float = 10.0


class Governance(BaseModel):
    supreme_organ: str = "Asamblea General de Socios (Un socio, un voto)"
    executive_body: str = "Consejo de Administración"
    supervisory_body: str = "Consejo de Vigilancia"
    committees: list[str] = Field(default_factory=list)


class CoopProfile(BaseModel):
    name: str = "Organización de Economía Social"
    legal_structure: str = "Sociedad Cooperativa"
    regime: str = "Economía Social y Solidaria"
    country: str = "México"
    mission: str = ""
    vision: str = ""
    governance: Governance = Field(default_factory=Governance)
    statutory_funds: StatutoryFunds = Field(default_factory=StatutoryFunds)
    values: list[str] = Field(default_factory=list)
    strategic_priorities: list[str] = Field(default_factory=list)

    @classmethod
    def load_from_yaml(cls, path: Path) -> CoopProfile:
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_prompt_block(self) -> str:
        lines = [
            f"## Perfil de la Organización: {self.name}",
            f"**Figura Jurídica:** {self.legal_structure} | **Régimen:** {self.regime} | **País:** {self.country}",
            f"**Misión:** {self.mission.strip()}",
            f"**Visión:** {self.vision.strip()}",
            "\n### Estructura de Gobernanza Democrática:",
            f"- Órgano Supremo: {self.governance.supreme_organ}",
            f"- Órgano Ejecutivo: {self.governance.executive_body}",
            f"- Órgano de Control: {self.governance.supervisory_body}",
            "\n### Fondos Estatutarios Blindados (LGSC):",
            f"- Fondo de Reserva: {self.statutory_funds.reserve_fund_pct}%",
            f"- Fondo de Previsión Social (Salud/Retiro): {self.statutory_funds.social_welfare_fund_pct}%",
            f"- Fondo de Educación Cooperativa (Formación/Posgrados): {self.statutory_funds.education_fund_pct}%",
            "\n### Principios y Valores:",
        ]
        for val in self.values:
            lines.append(f"- {val}")
        lines.append("\n### Prioridades Estratégicas:")
        for prio in self.strategic_priorities:
            lines.append(f"- {prio}")
        return "\n".join(lines)
