"""Comparación de evaluaciones guardadas: tabla ordenada y cuál atender primero.

Los días restantes se recalculan con la fecha de hoy, no con la de la evaluación.
La prioridad es determinista: primero la decisión de la matriz, luego el orden pedido.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from coopexecutive.grant_tools.matrix import EvaluacionGuardada, ResultadoMatriz, cargar, texto_plazo

Orden = Literal["plazo", "puntaje"]

# Menor es mejor. Las decisiones que descartan no compiten por la prioridad.
_RANGO_DECISION = {
    "APLICAR": 0,
    "EXPLORAR": 1,
    "CONDICIONAL": 2,
    "VERIFICAR_ELEGIBILIDAD": 3,
    "VERIFICAR_VIGENCIA": 3,
    "EVALUACION_INCOMPLETA": 3,
    "ESCALAR_DIRECCION": 4,
}


@dataclass(frozen=True)
class Fila:
    id: int
    expediente: str | None
    resultado: ResultadoMatriz
    dias: int | None
    plazo: str

    @property
    def vencida(self) -> bool:
        return self.dias is not None and self.dias < 0

    @property
    def descartada(self) -> bool:
        return self.vencida or self.resultado.decision not in _RANGO_DECISION


@dataclass(frozen=True)
class Comparacion:
    filas: list[Fila]
    prioridad: Fila | None
    motivo: str


def _fila(ev: EvaluacionGuardada, hoy: date) -> Fila:
    r = ev.resultado
    if r.fecha_cierre is not None:
        dias: int | None = (r.fecha_cierre - hoy).days
    elif r.dias_restantes is not None:
        dias = r.dias_restantes - (hoy - r.fecha_evaluacion).days
    else:
        dias = None
    return Fila(id=ev.id, expediente=ev.expediente_folio, resultado=r, dias=dias, plazo=texto_plazo(dias))


def _clave(fila: Fila, orden: Orden) -> tuple:
    rango = 9 if fila.descartada else _RANGO_DECISION[fila.resultado.decision]
    dias = fila.dias if fila.dias is not None else 10_000
    if orden == "plazo":
        return (fila.descartada, dias, rango, -fila.resultado.puntaje)
    return (fila.descartada, rango, -fila.resultado.puntaje, dias)


def comparar(evaluaciones: list[EvaluacionGuardada], hoy: date, orden: Orden = "plazo") -> Comparacion:
    if len(evaluaciones) < 2:
        raise ValueError("Se necesitan al menos dos evaluaciones para comparar.")
    filas = sorted((_fila(ev, hoy) for ev in evaluaciones), key=lambda f: _clave(f, orden))
    vigentes = [f for f in filas if not f.descartada]
    if not vigentes:
        return Comparacion(filas, None, "Ninguna sigue en competencia: todas están vencidas o descartadas.")
    # La prioridad no depende del orden de la tabla: mejor decisión y, a igual decisión, cierre más próximo.
    prioridad = min(
        vigentes,
        key=lambda f: (
            _RANGO_DECISION[f.resultado.decision],
            f.dias if f.dias is not None else 10_000,
            -f.resultado.puntaje,
        ),
    )
    r = prioridad.resultado
    motivo = f"Decisión {r.decision} con {r.puntaje} puntos; {prioridad.plazo.lower()}."
    urgentes = [f for f in vigentes if f is not prioridad and f.dias is not None and 0 <= f.dias <= 13]
    if urgentes:
        motivo += " También urgente: " + ", ".join(f"#{f.id} {f.resultado.convocatoria}" for f in urgentes) + "."
    return Comparacion(filas, prioridad, motivo)


def cargar_varias(ids: list[int]) -> list[EvaluacionGuardada]:
    return [cargar(i) for i in dict.fromkeys(ids)]


def recientes(limite: int = 10) -> list[int]:
    """Id de las evaluaciones más recientes que guardan el resultado completo."""
    from coopexecutive.memory.episodic import get_db_conn, initialize_db

    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute(
            "SELECT id FROM grant_evaluations WHERE resultado_json IS NOT NULL AND resultado_json != '' "
            "ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [f["id"] for f in filas]


def ultimas_por_expediente(folios: list[str]) -> list[int]:
    """Id de la evaluación más reciente de cada expediente."""
    from coopexecutive.crm import cases

    ids: list[int] = []
    for folio in folios:
        vinculadas = cases.evaluaciones(folio)
        if not vinculadas:
            raise ValueError(f"El expediente {folio.upper()} no tiene evaluaciones.")
        ids.append(vinculadas[-1].id)
    return ids
