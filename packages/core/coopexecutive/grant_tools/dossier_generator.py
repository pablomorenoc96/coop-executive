"""Dossier de postulación técnica y financiera.

Reúne el marco lógico y el presupuesto con las secciones narrativas. Cada sección
sin datos queda como pendiente; los fondos estatutarios solo se citan en cooperativas.
"""
from __future__ import annotations

from dataclasses import dataclass

from coopexecutive.guardrails.marcadores import pendiente

from .budget_builder import GrantBudget
from .logical_framework import ProjectLogicalFramework


@dataclass
class ProposalDossier:
    project_name: str
    organization_name: str
    donor_agency: str = ""
    call_title: str = ""
    target_country: str = ""
    executive_summary: str = ""
    problem_statement: str = ""
    logical_framework: ProjectLogicalFramework | None = None
    budget: GrantBudget | None = None
    sustainability_plan: str = ""
    cooperative_safeguards: str = ""
    es_cooperativa: bool = True

    def to_markdown(self) -> str:
        salvaguardas = "SALVAGUARDAS COOPERATIVAS Y ANTICORRUPCIÓN" if self.es_cooperativa else \
            "SALVAGUARDAS Y CONTROL INTERNO"
        detalle_salvaguardas = (
            "uso de fondos estatutarios, órgano de vigilancia, periodicidad de la fiscalización "
            "y destino de los activos" if self.es_cooperativa else
            "órgano de control, políticas de transparencia, periodicidad de la auditoría y destino de los activos"
        )
        lines = [
            "# DOSSIER DE POSTULACIÓN TÉCNICA Y FINANCIERA",
            f"**Proyecto:** {self.project_name}",
            f"**Organización Postulante:** {self.organization_name}",
            f"**Agencia Cooperante / Donante:** {self.donor_agency or pendiente('financiador')}",
            f"**Convocatoria:** {self.call_title or pendiente('convocatoria')}",
            f"**Ámbito Territorial:** {self.target_country or pendiente('ámbito territorial')}",
            "",
            "---",
            "",
            "## 1. RESUMEN EJECUTIVO Y PERFIL DEL PROPONENTE",
            self.executive_summary or pendiente("resumen ejecutivo del proyecto y perfil del proponente"),
            "",
            "## 2. DIAGNÓSTICO DEL PROBLEMA Y LÍNEA BASE",
            self.problem_statement or pendiente("diagnóstico del problema y línea base con fuentes verificables"),
            "",
            "## 3. MATRIZ DE MARCO LÓGICO",
        ]

        if self.logical_framework:
            lines.append(self.logical_framework.to_markdown())
        else:
            lines.append(pendiente("marco lógico (coopexecutive marco-logico)"))

        lines.extend(["", "## 4. PLAN PRESUPUESTAL Y CONTRAPARTIDA INSTITUCIONAL"])

        if self.budget:
            b = self.budget
            lines.extend([
                f"* **Fondos Solicitados al Donante:** {b.total(b.total_requested)}",
                f"* **Contrapartida Institucional (Especie/Valorizada):** {b.monto(b.total_matching)}",
                f"* **Presupuesto Total Consolidado:** {b.total(b.grand_total)}",
                "",
                "### Desglose de Rubros Presupuestales:",
                "| Categoría | Concepto | Solicitado | Contrapartida | Total |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for item in b.items:
                lines.append(
                    f"| {item.category.upper()} | {item.concept} | "
                    f"{b.monto(item.requested_amount)} | {b.monto(item.matching_amount)} | {b.monto(item.total_cost)} |"
                )
        else:
            lines.append(pendiente("presupuesto (coopexecutive presupuesto)"))

        lines.extend([
            "",
            f"## 5. {salvaguardas}",
            self.cooperative_safeguards or pendiente(f"salvaguardas de la organización ({detalle_salvaguardas})"),
            "",
            "## 6. ESTRATEGIA DE SOSTENIBILIDAD Y SALIDA POST-DONANTE",
            self.sustainability_plan or pendiente(
                "estrategia de sostenibilidad (fuentes de ingreso posteriores al "
                "financiamiento y plazo estimado, respaldados por datos de la organización)"
            ),
        ])
        return "\n".join(lines)
