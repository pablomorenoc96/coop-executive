"""Generador de Matriz de Marco Lógico (MML) y Teoría del Cambio (ToC).

Estructura propuestas técnicas con rigor multilateral (BID, UE, agencias de cooperación)
vinculando el fin superior con el propósito, componentes, actividades e indicadores ODS.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
        lines = [
            f"# Matriz de Marco Lógico: {self.project_title}",
            f"**Alineación ODS:** {', '.join(self.target_ods)}",
            "\n## 1. Planteamiento del Problema Central",
            self.problem_statement,
            "\n## 2. Teoría del Cambio (Theory of Change)",
            self.theory_of_change,
            "\n## 3. Matriz 4x4 de Resultados",
            "| Nivel | Resumen Narrativo | Indicadores Verificables | Medios de Verificación | Supuestos Críticos |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in self.rows:
            ind = "<br>• ".join(r.indicators)
            means = "<br>• ".join(r.verification_means)
            assump = "<br>• ".join(r.assumptions)
            lines.append(f"| **{r.level}** | {r.narrative_summary} | • {ind} | • {means} | • {assump} |")
            
        return "\n".join(lines)
