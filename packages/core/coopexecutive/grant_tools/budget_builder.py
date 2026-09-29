"""Presupuesto de proyecto: fondos solicitados y contrapartida.

Todos los montos se expresan en la moneda del presupuesto (código ISO 4217);
no se hace ninguna conversión entre monedas. Una partida sin costo queda como
COSTO POR COTIZAR y, mientras haya alguna, el total es MONTO POR DEFINIR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from coopexecutive.guardrails.marcadores import COSTO_POR_COTIZAR, MONTO_POR_DEFINIR
from coopexecutive.utils.moneda import formatear_monto, validar_moneda


@dataclass
class BudgetItem:
    category: str  # Personal, Equipamiento, Operación, Auditoría...
    concept: str
    unit: str
    quantity: float
    unit_cost: float | None = None
    requested_amount: float | None = None
    matching_amount: float = 0.0

    def __post_init__(self) -> None:
        # Con costo unitario y sin monto solicitado, se pide lo que no cubre la contrapartida.
        if self.requested_amount is None and self.unit_cost is not None:
            self.requested_amount = max(self.quantity * self.unit_cost - self.matching_amount, 0.0)

    @property
    def cotizado(self) -> bool:
        return self.requested_amount is not None

    @property
    def total_cost(self) -> float | None:
        return None if self.requested_amount is None else self.requested_amount + self.matching_amount


@dataclass
class GrantBudget:
    project_title: str
    currency: str = "USD"
    items: list[BudgetItem] = field(default_factory=list)
    # Tope de costos indirectos en % de los directos, tal como lo fija la convocatoria.
    indirect_cap_pct: float | None = None

    def __post_init__(self) -> None:
        self.currency = validar_moneda(self.currency)

    @property
    def completo(self) -> bool:
        return all(item.cotizado for item in self.items)

    @property
    def por_cotizar(self) -> list[BudgetItem]:
        return [item for item in self.items if not item.cotizado]

    @property
    def total_requested(self) -> float:
        """Suma de lo solicitado en las partidas cotizadas."""
        return sum(item.requested_amount or 0.0 for item in self.items)

    @property
    def total_matching(self) -> float:
        return sum(item.matching_amount for item in self.items)

    @property
    def grand_total(self) -> float:
        return self.total_requested + self.total_matching

    @property
    def indirectos_maximos(self) -> float | None:
        """Tope de indirectos sobre el total directo, solo si todo está cotizado."""
        if self.indirect_cap_pct is None or not self.completo:
            return None
        return round(self.grand_total * self.indirect_cap_pct / 100, 2)

    def monto(self, valor: float | None) -> str:
        return MONTO_POR_DEFINIR if valor is None else formatear_monto(valor, self.currency)

    def total(self, valor: float) -> str:
        """Un total con partidas por cotizar no se presenta como definitivo."""
        if self.completo:
            return self.monto(valor)
        return f"{MONTO_POR_DEFINIR} (parcial: {self.monto(valor)})"

    def to_markdown(self) -> str:
        lines = [
            f"# Presupuesto: {self.project_title}",
            f"**Moneda:** {self.currency}",
            f"**Solicitado:** {self.total(self.total_requested)} | "
            f"**Contrapartida:** {self.monto(self.total_matching)} | "
            f"**Total del proyecto:** {self.total(self.grand_total)}",
            "\n| Rubro | Concepto | Cantidad | Costo unitario | Solicitado | Contrapartida | Total |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for it in self.items:
            unitario = COSTO_POR_COTIZAR if it.unit_cost is None else self.monto(it.unit_cost)
            solicitado = COSTO_POR_COTIZAR if it.requested_amount is None else self.monto(it.requested_amount)
            lines.append(
                f"| {it.category} | {it.concept} | {it.quantity:g} {it.unit} | {unitario} | "
                f"{solicitado} | {self.monto(it.matching_amount)} | {self.monto(it.total_cost)} |"
            )
        if self.indirect_cap_pct is not None:
            lines.append(
                f"\n**Costos indirectos:** hasta {self.indirect_cap_pct:g} % del total directo, "
                f"según la convocatoria: {self.monto(self.indirectos_maximos)}."
            )
        if self.por_cotizar:
            conceptos = ", ".join(it.concept for it in self.por_cotizar)
            lines.append(f"\n**Partidas por cotizar:** {conceptos}.")
        return "\n".join(lines)


# --- Entrada validada (YAML del usuario) -----------------------------------------


class PartidaEntrada(BaseModel):
    rubro: str
    concepto: str
    unidad: str = "unidad"
    cantidad: float = Field(1, gt=0)
    costo_unitario: float | None = Field(None, ge=0)
    solicitado: float | None = Field(None, ge=0)
    contrapartida: float = Field(0, ge=0)


class PresupuestoEntrada(BaseModel):
    moneda: str = "MXN"
    tope_indirectos: float | None = Field(None, ge=0, le=100)
    partidas: list[PartidaEntrada] = Field(default_factory=list)


def presupuesto_desde_datos(
    titulo: str, datos: PresupuestoEntrada | dict[str, Any] | None, *, moneda: str | None = None,
    tope_indirectos: float | None = None,
) -> GrantBudget:
    entrada = datos if isinstance(datos, PresupuestoEntrada) else PresupuestoEntrada.model_validate(datos or {})
    return GrantBudget(
        project_title=titulo,
        currency=moneda or entrada.moneda,
        indirect_cap_pct=tope_indirectos if tope_indirectos is not None else entrada.tope_indirectos,
        items=[
            BudgetItem(p.rubro, p.concepto, p.unidad, p.cantidad, p.costo_unitario, p.solicitado, p.contrapartida)
            for p in entrada.partidas
        ],
    )


PLANTILLA_YAML = """\
# Presupuesto. Deje costo_unitario vacío si no hay cotización: se marca COSTO POR COTIZAR.
moneda: MXN
tope_indirectos:        # % que fija la convocatoria; vacío si no lo fija
partidas:
  - rubro: Personal
    concepto: ""
    unidad: meses
    cantidad: 1
    costo_unitario:
    contrapartida: 0
"""
