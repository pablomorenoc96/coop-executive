"""Matriz de Marco Lógico (MML) y Teoría del Cambio.

La matriz se arma con datos que da el usuario (YAML) o que propone el modelo y se
validan aquí. Lo que falta se marca como pendiente: nunca se rellena con supuestos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, field_validator

from coopexecutive.guardrails.marcadores import pendiente

NIVELES = ("Fin", "Propósito", "Componentes", "Actividades")


@dataclass
class LogFrameRow:
    level: str  # Fin, Propósito, Componentes, Actividades
    narrative_summary: str
    indicators: list[str]
    verification_means: list[str]
    assumptions: list[str]


@dataclass
class ProjectLogicalFramework:
    project_title: str
    target_ods: list[str]
    problem_statement: str
    theory_of_change: str
    rows: list[LogFrameRow]

    def to_markdown(self) -> str:
        def celda(valores: list[str], dato: str) -> str:
            return "• " + "<br>• ".join(valores) if valores else pendiente(dato)

        lines = [
            f"# Matriz de Marco Lógico: {self.project_title}",
            f"**Alineación ODS:** {', '.join(self.target_ods) or pendiente('ODS vinculados')}",
            "\n## 1. Planteamiento del Problema Central",
            self.problem_statement or pendiente("problema central con su línea base"),
            "\n## 2. Teoría del Cambio",
            self.theory_of_change or pendiente("teoría del cambio"),
            "\n## 3. Matriz de Resultados",
            "| Nivel | Resumen Narrativo | Indicadores Verificables | Medios de Verificación | Supuestos Críticos |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in self.rows:
            lines.append(
                f"| **{r.level}** | {r.narrative_summary or pendiente('resumen narrativo')} | "
                f"{celda(r.indicators, 'indicadores')} | {celda(r.verification_means, 'medios de verificación')} | "
                f"{celda(r.assumptions, 'supuestos')} |"
            )
        return "\n".join(lines)


# --- Entrada validada (YAML del usuario o JSON del modelo) --------------------------


class FilaEntrada(BaseModel):
    nivel: str
    resumen: str = ""
    indicadores: list[str] = Field(default_factory=list)
    medios: list[str] = Field(default_factory=list)
    supuestos: list[str] = Field(default_factory=list)

    @field_validator("nivel")
    @classmethod
    def _nivel(cls, v: str) -> str:
        buscado = v.strip().lower().rstrip("s")
        for nivel in NIVELES:
            if buscado == nivel.lower().rstrip("s"):
                return nivel
        raise ValueError(f"nivel desconocido «{v}»; use {', '.join(NIVELES)}")


class MarcoLogicoEntrada(BaseModel):
    problema: str = ""
    teoria_cambio: str = ""
    ods: list[str] = Field(default_factory=list)
    filas: list[FilaEntrada] = Field(default_factory=list)


def marco_desde_datos(titulo: str, datos: MarcoLogicoEntrada | dict[str, Any] | None) -> ProjectLogicalFramework:
    """Arma la matriz con los cuatro niveles en orden; un nivel ausente queda pendiente."""
    if isinstance(datos, MarcoLogicoEntrada):
        entrada = datos
    else:
        entrada = MarcoLogicoEntrada.model_validate(datos or {})
    filas = []
    for nivel in NIVELES:
        propias = [f for f in entrada.filas if f.nivel == nivel] or [FilaEntrada(nivel=nivel)]
        filas.extend(LogFrameRow(nivel, f.resumen, f.indicadores, f.medios, f.supuestos) for f in propias)
    return ProjectLogicalFramework(titulo, entrada.ods, entrada.problema, entrada.teoria_cambio, filas)


PLANTILLA_YAML = """\
# Marco lógico. Deje vacío lo que no sepa: se marca como pendiente.
problema: ""
teoria_cambio: ""
ods: []            # p. ej. ["ODS 7"], solo si el proyecto o la convocatoria lo sustentan
filas:
  - nivel: Fin
    resumen: ""
    indicadores: []
    medios: []
    supuestos: []
  - nivel: Propósito
    resumen: ""
  - nivel: Componentes
    resumen: ""
  - nivel: Actividades
    resumen: ""
"""
