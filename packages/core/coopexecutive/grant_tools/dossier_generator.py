"""Generador de Dossier Completo de Postulación a Fondos Multilaterales.

Incorpora estándares de Results-Based Management (RBM), investigación de subvenciones
y protocolos de propuestas para donantes internacionales (BID, FundsforNGOs, UE).
"""
from dataclasses import dataclass, field
from typing import List, Optional
from .logical_framework import ProjectLogicalFramework
from .budget_builder import GrantBudget


@dataclass
class ProposalDossier:
    project_name: str
    organization_name: str
    donor_agency: str
    call_title: str
    target_country: str = "[PENDIENTE: ámbito territorial]"
    executive_summary: str = ""
    problem_statement: str = ""
    logical_framework: Optional[ProjectLogicalFramework] = None
    budget: Optional[GrantBudget] = None
    sustainability_plan: str = ""
    cooperative_safeguards: str = ""

    def to_markdown(self) -> str:
        lines = [
            "# DOSSIER DE POSTULACIÓN TÉCNICA Y FINANCIERA",
            f"**Proyecto:** {self.project_name}",
            f"**Organización Postulante:** {self.organization_name}",
            f"**Agencia Cooperante / Donante:** {self.donor_agency}",
            f"**Convocatoria:** {self.call_title}",
            f"**Ámbito Territorial:** {self.target_country}",
            "",
            "---",
            "",
            "## 1. RESUMEN EJECUTIVO Y PERFIL DEL PROPONENTE",
            self.executive_summary or "[PENDIENTE: resumen ejecutivo del proyecto y perfil del proponente]",
            "",
            "## 2. DIAGNÓSTICO DEL PROBLEMA Y LÍNEA BASE",
            self.problem_statement or "[PENDIENTE: diagnóstico del problema y línea base con fuentes verificables]",
            "",
            "## 3. MATRIZ DE MARCO LÓGICO (MML / RBM)",
        ]

        if self.logical_framework:
            lines.append(self.logical_framework.to_markdown())
        else:
            lines.append("*Marco lógico pendiente de formulación.*")

        lines.extend([
            "",
            "## 4. PLAN PRESUPUESTAL Y CONTRAPARTIDA INSTITUCIONAL",
        ])

        if self.budget:
            monto = self.budget.monto
            lines.extend([
                f"* **Fondos Solicitados al Donante:** {monto(self.budget.total_requested)}",
                f"* **Contrapartida Institucional (Especie/Valorizada):** {monto(self.budget.total_matching)}",
                f"* **Presupuesto Total Consolidado:** {monto(self.budget.grand_total)}",
                "",
                "### Desglose de Rubros Presupuestales:",
                "| Categoría | Concepto | Solicitado | Contrapartida | Total |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for item in self.budget.items:
                lines.append(
                    f"| {item.category.upper()} | {item.concept} | "
                    f"{monto(item.requested_amount)} | {monto(item.matching_amount)} | {monto(item.total_cost)} |"
                )
        else:
            lines.append("*Presupuesto pendiente de desglose.*")

        lines.extend([
            "",
            "## 5. SALVAGUARDAS COOPERATIVAS Y ANTICORRUPCIÓN",
            self.cooperative_safeguards or (
                "[PENDIENTE: salvaguardas de la organización (uso de fondos estatutarios, "
                "órgano de vigilancia, periodicidad de la fiscalización y destino de los activos)]"
            ),
            "",
            "## 6. ESTRATEGIA DE SOSTENIBILIDAD Y SALIDA POST-DONANTE",
            self.sustainability_plan or (
                "[PENDIENTE: estrategia de sostenibilidad (fuentes de ingreso posteriores al "
                "financiamiento y plazo estimado, respaldados por datos de la organización)]"
            ),
            "",
            "---",
            "*(Dossier emitido automáticamente conforme a las normas de gobernanza de CoopExecutive)*",
        ])

        return "\n".join(lines)
