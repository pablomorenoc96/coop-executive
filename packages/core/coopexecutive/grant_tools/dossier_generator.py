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
    target_country: str = "México / Latinoamérica"
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
            self.executive_summary or (
                f"El presente proyecto propone una solución territorial basada en transferencia tecnológica "
                f"y gobernanza democrática. Presentado por {self.organization_name}, operando bajo el principio "
                f"de 'un socio, un voto' y con fondos patrimoniales inalienables protegidos por ley."
            ),
            "",
            "## 2. DIAGNÓSTICO DEL PROBLEMA Y LÍNEA BASE",
            self.problem_statement or (
                "Se identifica una brecha crítica en el acceso a tecnologías de producción sostenibles "
                "y altos costos de suministro energético en el sector productivo social y comunitario. "
                "La intervención resuelve esta asimetría mediante capacitación técnica e infraestructura colectiva."
            ),
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
            lines.extend([
                f"* **Fondos Solicitados al Donante:** ${self.budget.total_requested:,.2f} {self.budget.currency}",
                f"* **Contrapartida Institucional (Especie/Valorizada):** ${self.budget.total_matching:,.2f} {self.budget.currency}",
                f"* **Presupuesto Total Consolidado:** ${self.budget.grand_total:,.2f} {self.budget.currency}",
                "",
                "### Desglose de Rubros Presupuestales:",
                "| Categoría | Concepto | Solicitado | Contrapartida | Total |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for item in self.budget.items:
                tot = item.requested_amount_usd + item.matching_amount_usd
                lines.append(
                    f"| {item.category.upper()} | {item.concept} | "
                    f"${item.requested_amount_usd:,.2f} | ${item.matching_amount_usd:,.2f} | ${tot:,.2f} |"
                )
        else:
            lines.append("*Presupuesto pendiente de desglose.*")

        lines.extend([
            "",
            "## 5. SALVAGUARDAS COOPERATIVAS Y ANTICORRUPCIÓN",
            self.cooperative_safeguards or (
                "- **Blindaje de Fondos Estatutarios:** Ningún fondo donado ni excedente operativo se distribuirá de forma individual; "
                "se integran a los Fondos Inalienables de Reserva (15%), Previsión Social (10%) y Educación (10%).\n"
                "- **Fiscalización Colegiada:** El Consejo de Vigilancia interno audita trimestralmente la ejecución del convenio.\n"
                "- **Propiedad Colectiva de Activos:** Todos los activos adquiridos con fondos de la subvención son patrimonio social inalienable."
            ),
            "",
            "## 6. ESTRATEGIA DE SOSTENIBILIDAD Y SALIDA POST-DONANTE",
            self.sustainability_plan or (
                "El modelo de financiamiento garantiza la autosuficiencia operativa a partir del mes 18, "
                "mediante los ahorros generados en la cooperativa y la prestación de servicios técnicos mutuos, "
                "sin depender de subvenciones recurrentes para su mantenimiento regular."
            ),
            "",
            "---",
            "*(Dossier emitido automáticamente conforme a las normas de gobernanza de CoopExecutive)*",
        ])

        return "\n".join(lines)
