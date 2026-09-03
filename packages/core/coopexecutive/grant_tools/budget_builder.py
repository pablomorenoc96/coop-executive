"""Constructor de Presupuestos para Subvenciones y Cooperación Internacional.

Estructura desgloses financieros auditables distinguiendo fondos solicitados
al donante de contrapartidas institucionales (en especie o valorizadas).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BudgetItem:
    category: str  # Personal, Equipamiento/CAPEX, Operación/OPEX, Auditoría, Indirectos
    concept: str
    unit: str
    quantity: float
    unit_cost_usd: float
    requested_amount_usd: float
    matching_amount_usd: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self.requested_amount_usd + self.matching_amount_usd


@dataclass
class GrantBudget:
    project_title: str
    currency: str = "USD"
    items: list[BudgetItem] = field(default_factory=list)

    @property
    def total_requested(self) -> float:
        return sum(item.requested_amount_usd for item in self.items)

    @property
    def total_matching(self) -> float:
        return sum(item.matching_amount_usd for item in self.items)

    @property
    def grand_total(self) -> float:
        return self.total_requested + self.total_matching

    def to_markdown(self) -> str:
        lines = [
            f"# Presupuesto Detallado: {self.project_title}",
            f"**Moneda base:** {self.currency}",
            f"**Total Solicitado:** ${self.total_requested:,.2f} | **Contrapartida:** ${self.total_matching:,.2f} | **Total Proyecto:** ${self.grand_total:,.2f}",
            "\n| Categoría | Concepto | Cantidad | Costo Unitario | Solicitado al Donante | Contrapartida | Total |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for it in self.items:
            lines.append(
                f"| {it.category} | {it.concept} | {it.quantity} {it.unit} | ${it.unit_cost_usd:,.2f} | "
                f"${it.requested_amount_usd:,.2f} | ${it.matching_amount_usd:,.2f} | ${it.total_cost_usd:,.2f} |"
            )
        return "\n".join(lines)
