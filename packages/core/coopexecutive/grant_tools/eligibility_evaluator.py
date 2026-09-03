"""Evaluador de Convocatorias y Subvenciones Internacionales.

Aplica la matriz de evaluación multicriterio de 8 dimensiones y 100 puntos
para dictaminar objetivamente si una cooperativa u organización civil
debe invertir recursos en postular a una convocatoria (FundsforNGOs, BID, UE, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DimensionScore:
    name: str
    weight: int
    score: float
    justification: str


@dataclass
class EvaluationReport:
    call_title: str
    donor_agency: str
    deadline: str
    available_budget: str
    total_score: float
    recommendation: str  # APLICAR, EXPLORAR, CONDICIONAL, NO APLICAR
    color_code: str
    dimension_scores: list[DimensionScore]
    strengths: list[str]
    risks: list[str]
    next_steps: list[str]

    def to_markdown(self) -> str:
        lines = [
            f"# Dictamen de Evaluación de Convocatoria: {self.call_title}",
            f"**Donante/Agencia:** {self.donor_agency} | **Fecha Límite:** {self.deadline}",
            f"**Presupuesto/Monto:** {self.available_budget}",
            f"\n## Calificación Global: {self.total_score:.1f} / 100 — {self.color_code} {self.recommendation}",
            "\n| Dimensión | Puntos Máx | Puntuación | Justificación Técnica |",
            "| :--- | :---: | :---: | :--- |",
        ]
        for d in self.dimension_scores:
            lines.append(f"| {d.name} | {d.weight} | {d.score:.1f} | {d.justification} |")
        
        lines.append("\n### Fortalezas de la Organización para esta Convocatoria:")
        for s in self.strengths:
            lines.append(f"- [x] {s}")
            
        lines.append("\n### Riesgos y Brechas Críticas Identificadas:")
        for r in self.risks:
            lines.append(f"- [!] {r}")
            
        lines.append("\n### Ruta de Acción Recomendada:")
        for i, step in enumerate(self.next_steps, 1):
            lines.append(f"{i}. {step}")
            
        return "\n".join(lines)


def evaluate_grant_opportunity(
    call_title: str,
    donor_agency: str,
    deadline: str,
    available_budget: str,
    mission_alignment: float,
    alignment_notes: str,
    geo_eligibility: float,
    geo_notes: str,
    budget_feasibility: float,
    budget_notes: str,
    timeline_feasibility: float,
    timeline_notes: str,
    capacity_score: float,
    capacity_notes: str,
    impact_score: float,
    impact_notes: str,
    strategic_value: float,
    strategic_notes: str,
    reporting_manageability: float,
    reporting_notes: str,
    strengths: list[str],
    risks: list[str],
    next_steps: list[str],
) -> EvaluationReport:
    """Calcula la matriz ponderada y genera el reporte ejecutivo."""
    dims = [
        DimensionScore("Alineación con la Misión", 20, min(20.0, max(0.0, mission_alignment)), alignment_notes),
        DimensionScore("Elegibilidad Geográfica y Legal", 10, min(10.0, max(0.0, geo_eligibility)), geo_notes),
        DimensionScore("Rango Presupuestal Adecuado", 15, min(15.0, max(0.0, budget_feasibility)), budget_notes),
        DimensionScore("Viabilidad de Tiempos y Entrega", 10, min(10.0, max(0.0, timeline_feasibility)), timeline_notes),
        DimensionScore("Capacidad Técnica y Operativa", 15, min(15.0, max(0.0, capacity_score)), capacity_notes),
        DimensionScore("Potencial de Impacto Medible (ODS)", 15, min(15.0, max(0.0, impact_score)), impact_notes),
        DimensionScore("Valor Estratégico a Largo Plazo", 10, min(10.0, max(0.0, strategic_value)), strategic_notes),
        DimensionScore("Requisitos de Auditoría y Reporte", 5, min(5.0, max(0.0, reporting_manageability)), reporting_notes),
    ]
    total = sum(d.score for d in dims)
    
    if total >= 80.0:
        rec = "APLICAR (Alta Compatibilidad)"
        color = "🟢"
    elif total >= 60.0:
        rec = "EXPLORAR (Requiere Alianzas o Definición)"
        color = "🟡"
    elif total >= 40.0:
        rec = "CONDICIONAL (Solo si existe capacidad ociosa)"
        color = "🟠"
    else:
        rec = "NO APLICAR (Incompatible o Desgaste Operativo)"
        color = "🔴"
        
    return EvaluationReport(
        call_title=call_title,
        donor_agency=donor_agency,
        deadline=deadline,
        available_budget=available_budget,
        total_score=total,
        recommendation=rec,
        color_code=color,
        dimension_scores=dims,
        strengths=strengths,
        risks=risks,
        next_steps=next_steps,
    )
