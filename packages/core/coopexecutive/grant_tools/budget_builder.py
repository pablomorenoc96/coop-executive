"""Constructor de Presupuestos para Subvenciones y Cooperación Internacional.

Estructura desgloses financieros auditables distinguiendo fondos solicitados
al donante de contrapartidas institucionales (en especie o valorizadas).

Todos los montos se expresan en la moneda del presupuesto (código ISO 4217);
no se hace ninguna conversión entre monedas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from coopexecutive.utils.moneda import formatear_monto, validar_moneda


@dataclass
class BudgetItem:
    category: str  # Personal, Equipamiento/CAPEX, Operación/OPEX, Auditoría, Indirectos
    concept: str
    unit: str
    quantity: float
    unit_cost: float
    requested_amount: float
    matching_amount: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.requested_amount + self.matching_amount


@dataclass
class GrantBudget:
    project_title: str
    currency: str = "USD"
    items: list[BudgetItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.currency = validar_moneda(self.currency)

    @property
    def total_requested(self) -> float:
        return sum(item.requested_amount for item in self.items)

    @property
    def total_matching(self) -> float:
        return sum(item.matching_amount for item in self.items)

    @property
    def grand_total(self) -> float:
        return self.total_requested + self.total_matching

    def monto(self, valor: float) -> str:
        return formatear_monto(valor, self.currency)

    def to_markdown(self) -> str:
        lines = [
            f"# Presupuesto Detallado: {self.project_title}",
            f"**Moneda base:** {self.currency}",
            f"**Total Solicitado:** {self.monto(self.total_requested)} | "
            f"**Contrapartida:** {self.monto(self.total_matching)} | "
            f"**Total Proyecto:** {self.monto(self.grand_total)}",
            "\n| Categoría | Concepto | Cantidad | Costo Unitario | Solicitado al Donante | Contrapartida | Total |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for it in self.items:
            lines.append(
                f"| {it.category} | {it.concept} | {it.quantity} {it.unit} | {self.monto(it.unit_cost)} | "
                f"{self.monto(it.requested_amount)} | {self.monto(it.matching_amount)} | {self.monto(it.total_cost)} |"
            )
        return "\n".join(lines)
