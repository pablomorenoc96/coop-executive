"""Cargador y formateador del perfil de la organización.

Admite cooperativas, asociaciones civiles, empresas y personas físicas con actividad
empresarial. Los fondos estatutarios y la asamblea de un socio, un voto solo se
exigen a las cooperativas.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from coopexecutive.utils.moneda import formatear_monto, validar_moneda
from coopexecutive.utils.texto import normalizar

TipoOrganizacion = Literal["cooperativa", "asociacion_civil", "empresa", "persona_fisica"]

TIPOS_ORGANIZACION: dict[str, str] = {
    "cooperativa": "Cooperativa",
    "asociacion_civil": "Asociación civil u organización sin fines de lucro",
    "empresa": "Empresa (sociedad mercantil)",
    "persona_fisica": "Persona física con actividad empresarial",
}


def inferir_tipo(figura: str) -> TipoOrganizacion:
    """Deduce el tipo a partir de la figura jurídica escrita libremente."""
    texto = normalizar(figura)
    if "cooperativa" in texto or re.search(r"\bsc de rl\b|\bscl\b", texto):
        return "cooperativa"
    if re.search(r"asociacion civil|\bac\b|\biap\b|\bibp\b|\babp\b|asistencia privada|beneficencia privada", texto):
        return "asociacion_civil"
    if "persona fisica" in texto:
        return "persona_fisica"
    if re.search(r"\b(sa|sas|sapi|sab|s de rl)\b|sociedad anonima|sociedad por acciones|responsabilidad limitada", texto):
        return "empresa"
    return "cooperativa"


class StatutoryFunds(BaseModel):
    reserve_fund_pct: float = 15.0
    social_welfare_fund_pct: float = 10.0
    education_fund_pct: float = 10.0


class Governance(BaseModel):
    supreme_organ: str = "Asamblea General de Socios (Un socio, un voto)"
    executive_body: str = "Consejo de Administración"
    supervisory_body: str = "Consejo de Vigilancia"
    committees: list[str] = Field(default_factory=list)
    # Regla para aprobar en asamblea, sobre los votos válidos (a favor + en contra).
    mayoria: Literal["simple", "dos_tercios"] = "simple"


class RangoPresupuesto(BaseModel):
    """Montos que la organización puede solicitar o ejecutar. Vacío significa por definir."""

    minimo: float | None = None
    maximo: float | None = None
    moneda: str = "MXN"

    @field_validator("moneda")
    @classmethod
    def _moneda(cls, v: str) -> str:
        return validar_moneda(v)

    @model_validator(mode="after")
    def _orden(self) -> RangoPresupuesto:
        for valor in (self.minimo, self.maximo):
            if valor is not None and valor < 0:
                raise ValueError("El rango de presupuesto no admite montos negativos.")
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise ValueError("El mínimo del rango de presupuesto es mayor que el máximo.")
        return self

    @property
    def definido(self) -> bool:
        return self.minimo is not None and self.maximo is not None

    def texto(self) -> str:
        if not self.definido:
            return "MONTO POR DEFINIR"
        return f"{formatear_monto(self.minimo, self.moneda)} a {formatear_monto(self.maximo, self.moneda)}"  # type: ignore[arg-type]


class Membrete(BaseModel):
    """Identidad gráfica para documentos Word: imagen de encabezado, pie, fuente y tamaño.

    La imagen es relativa a la carpeta del perfil. La fuente debe estar instalada en el
    equipo que abra el documento; si no, el procesador de textos usa una similar.
    """

    imagen: str = ""
    pie: str = ""
    fuente: str = "Arial"
    tamano: float = Field(11, ge=8, le=16)


class Identidad(BaseModel):
    """Identidad visual de la intro. Las rutas son relativas a la carpeta del perfil."""

    nombre_corto: str = ""
    lema: str = ""
    logo: str = ""
    fuente: str = ""
    color_logo: str = ""
    color_texto: str = ""

    @field_validator("color_logo", "color_texto")
    @classmethod
    def _color(cls, v: str) -> str:
        v = v.strip()
        if v and not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise ValueError(f"«{v}» no es un color hexadecimal como #7C3AED.")
        return v.upper()


class Procuracion(BaseModel):
    """Datos que usa el procurador de fondos. Lo que falte se marca como pendiente."""

    siglas: str = ""
    estatus_legal: str = ""
    estatus_fiscal: str = ""
    territorio: str = ""
    metricas_impacto: list[str] = Field(default_factory=list)
    programas: list[str] = Field(default_factory=list)
    alianzas: list[str] = Field(default_factory=list)
    financiadores_historicos: list[str] = Field(default_factory=list)
    rango_presupuesto: RangoPresupuesto | None = None
    moneda_base: str = "MXN"
    mecanismos_cobro: list[str] = Field(default_factory=list)
    aprobadores: list[str] = Field(default_factory=list)
    membrete: Membrete = Field(default_factory=Membrete)
    # Campo de onboarding -> fuente (URL o «Dato del usuario»).
    origenes: dict[str, str] = Field(default_factory=dict)

    @field_validator("moneda_base")
    @classmethod
    def _moneda(cls, v: str) -> str:
        return validar_moneda(v)

    @property
    def rango_definido(self) -> bool:
        return self.rango_presupuesto is not None and self.rango_presupuesto.definido


class CoopProfile(BaseModel):
    name: str = "Organización de Economía Social"
    tipo_organizacion: TipoOrganizacion | None = None
    legal_structure: str = "Sociedad Cooperativa"
    regime: str = "Economía Social y Solidaria"
    country: str = "México"
    mission: str = ""
    vision: str = ""
    governance: Governance = Field(default_factory=Governance)
    statutory_funds: StatutoryFunds = Field(default_factory=StatutoryFunds)
    values: list[str] = Field(default_factory=list)
    strategic_priorities: list[str] = Field(default_factory=list)
    target_communities: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)
    funding_sources: list[str] = Field(default_factory=list)
    procuracion: Procuracion | None = None
    identidad: Identidad = Field(default_factory=Identidad)

    @model_validator(mode="after")
    def _tipo(self) -> CoopProfile:
        if self.tipo_organizacion is None:
            self.tipo_organizacion = inferir_tipo(self.legal_structure)
        if self.tipo_organizacion != "cooperativa" and "regime" not in self.model_fields_set:
            # El régimen por omisión describe a una cooperativa; para otras figuras no se supone.
            fiscal = self.procuracion.estatus_fiscal.strip() if self.procuracion else ""
            self.regime = fiscal or "[PENDIENTE: régimen]"
        return self

    @property
    def es_cooperativa(self) -> bool:
        return self.tipo_organizacion == "cooperativa"

    @property
    def tiene_asamblea(self) -> bool:
        """Hay un órgano colegiado de decisión: siempre en cooperativas, o si el perfil lo declara."""
        return self.es_cooperativa or "governance" in self.model_fields_set

    @property
    def rango_presupuesto_definido(self) -> bool:
        return self.procuracion is not None and self.procuracion.rango_definido

    @classmethod
    def load_from_yaml(cls, path: Path) -> CoopProfile:
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_prompt_block(self) -> str:
        tipo = TIPOS_ORGANIZACION[self.tipo_organizacion or "cooperativa"]
        lines = [
            f"## Perfil de la Organización: {self.name}",
            f"**Tipo:** {tipo} | **Figura Jurídica:** {self.legal_structure} | "
            f"**Régimen:** {self.regime} | **País:** {self.country}",
            f"**Misión:** {self.mission.strip() or '[PENDIENTE: misión]'}",
        ]
        if self.vision.strip():
            lines.append(f"**Visión:** {self.vision.strip()}")
        if self.tiene_asamblea:
            lines += [
                "\n### Estructura de Gobernanza Democrática:",
                f"- Órgano Supremo: {self.governance.supreme_organ}",
                f"- Órgano Ejecutivo: {self.governance.executive_body}",
                f"- Órgano de Control: {self.governance.supervisory_body}",
            ]
        if self.es_cooperativa:
            lines += [
                "\n### Fondos Estatutarios Blindados (LGSC):",
                f"- Fondo de Reserva: {self.statutory_funds.reserve_fund_pct}%",
                f"- Fondo de Previsión Social (Salud/Retiro): {self.statutory_funds.social_welfare_fund_pct}%",
                f"- Fondo de Educación Cooperativa (Formación/Posgrados): {self.statutory_funds.education_fund_pct}%",
            ]
        if self.values:
            lines.append("\n### Principios y Valores:")
            lines.extend(f"- {val}" for val in self.values)
        if self.strategic_priorities:
            lines.append("\n### Prioridades Estratégicas:")
            lines.extend(f"- {prio}" for prio in self.strategic_priorities)
        opcionales = [
            ("Poblaciones y Comunidades Atendidas", self.target_communities),
            ("Ejes de Trabajo", self.focus_areas),
            ("Fuentes de Financiamiento", self.funding_sources),
        ]
        for titulo, elementos in opcionales:
            if elementos:
                lines.append(f"\n### {titulo}:")
                lines.extend(f"- {e}" for e in elementos)
        if self.procuracion is not None:
            lines.append(self._bloque_procuracion(self.procuracion))
        return "\n".join(lines)

    @staticmethod
    def _bloque_procuracion(p: Procuracion) -> str:
        def texto(valor: str, dato: str) -> str:
            return valor.strip() or f"[PENDIENTE: {dato}]"

        def lista(valores: list[str], dato: str) -> str:
            return "; ".join(valores) if valores else f"[PENDIENTE: {dato}]"

        rango = p.rango_presupuesto.texto() if p.rango_presupuesto else "MONTO POR DEFINIR"
        lines = [
            "\n### Datos para Procuración de Fondos:",
            f"- Siglas o nombre corto: {texto(p.siglas, 'siglas')}",
            f"- Estatus legal: {texto(p.estatus_legal, 'estatus legal')}",
            f"- Estatus fiscal: {texto(p.estatus_fiscal, 'estatus fiscal')}",
            f"- Territorio: {texto(p.territorio, 'territorio de trabajo')}",
            f"- Programas: {lista(p.programas, 'programas')}",
            f"- Métricas de impacto: {lista(p.metricas_impacto, 'métricas de impacto verificables')}",
            f"- Alianzas: {lista(p.alianzas, 'alianzas vigentes')}",
            f"- Financiadores históricos: {lista(p.financiadores_historicos, 'financiadores históricos')}",
            f"- Rango de presupuesto: {rango}",
            f"- Moneda base: {p.moneda_base}",
            f"- Mecanismos de donación o cobro: {lista(p.mecanismos_cobro, 'mecanismos de donación o cobro')}",
            f"- Aprobadores: {lista(p.aprobadores, 'quién aprueba las solicitudes')}",
        ]
        return "\n".join(lines)
