"""Expedientes de procuración: una oportunidad o relación con su historial de avances.

Cada expediente lleva folio `EXP-AAAA-NNNN`. Solo puede haber uno abierto por
entidad y tipo; cada avance registra de dónde viene el dato.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from pydantic import BaseModel

from coopexecutive.crm._comun import elegir, monto_valido, siguiente_folio
from coopexecutive.guardrails.marcadores import MONTO_POR_DEFINIR, ORIGENES
from coopexecutive.memory.episodic import get_db_conn, initialize_db
from coopexecutive.utils.moneda import formatear_monto, validar_moneda
from coopexecutive.utils.texto import normalizar

TIPOS: tuple[str, ...] = ("Convocatoria", "Financiador", "Propuesta", "Reunión", "Crédito", "Beca", "Otro")
LARGO_TITULO = 250


class ExpedienteDuplicado(ValueError):
    def __init__(self, folio: str, titulo: str) -> None:
        super().__init__(f"Ya hay un expediente abierto para «{titulo}»: {folio}.")
        self.folio = folio


class Expediente(BaseModel):
    folio: str
    tipo: str
    entidad: str
    titulo: str
    objetivo: str = ""
    responsable: str = ""
    fecha_limite: date | None = None
    monto: float | None = None
    moneda: str | None = None
    abierto: bool = True
    creado_en: str = ""
    actualizado_en: str = ""

    @property
    def monto_texto(self) -> str:
        if self.monto is None or self.moneda is None:
            return MONTO_POR_DEFINIR
        return formatear_monto(self.monto, self.moneda)


class Avance(BaseModel):
    estado: str
    pendientes: str = ""
    siguiente_accion: str = ""
    origen: str
    registrado_en: str = ""


class EvaluacionVinculada(BaseModel):
    id: int
    decision: str
    puntaje: float
    hash: str | None = None
    evaluado_en: str = ""


def _expediente(fila: sqlite3.Row) -> Expediente:
    datos = {k: fila[k] for k in fila.keys() if k in Expediente.model_fields}
    datos["abierto"] = bool(datos["abierto"])
    return Expediente(**datos)


def _hoy() -> date:
    from coopexecutive.utils.fechas import hoy_local

    return hoy_local()


def abrir(
    tipo: str,
    entidad: str,
    *,
    objetivo: str = "",
    responsable: str = "",
    fecha_limite: date | None = None,
    monto: float | None = None,
    moneda: str = "MXN",
    hoy: date | None = None,
) -> Expediente:
    """Abre un expediente. Sin monto, se muestra como MONTO POR DEFINIR."""
    tipo = elegir(tipo, TIPOS, "Tipo")
    entidad = entidad.strip()
    if not entidad:
        raise ValueError("La entidad es obligatoria.")
    monto = monto_valido(monto, "Monto")
    moneda_final = validar_moneda(moneda) if monto is not None else None
    titulo = f"{tipo} - {entidad}"[:LARGO_TITULO]
    clave = normalizar(entidad)
    anio = (hoy or _hoy()).year

    initialize_db()
    with get_db_conn() as conn:
        previo = conn.execute(
            "SELECT folio, titulo FROM expedientes WHERE entidad_normalizada = ? AND tipo = ? AND abierto = 1",
            (clave, tipo),
        ).fetchone()
        if previo:
            raise ExpedienteDuplicado(previo["folio"], previo["titulo"])
        folio = siguiente_folio(conn, "expedientes", "EXP", anio)
        conn.execute(
            """
            INSERT INTO expedientes
                (folio, tipo, entidad, entidad_normalizada, titulo, objetivo, responsable,
                 fecha_limite, monto, moneda)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (folio, tipo, entidad, clave, titulo, objetivo.strip(), responsable.strip(),
             fecha_limite.isoformat() if fecha_limite else None, monto, moneda_final),
        )
        conn.commit()
    return obtener(folio)  # type: ignore[return-value]


def obtener(folio: str) -> Expediente | None:
    initialize_db()
    with get_db_conn() as conn:
        fila = conn.execute("SELECT * FROM expedientes WHERE folio = ?", (folio.strip().upper(),)).fetchone()
    return _expediente(fila) if fila else None


def registrar_avance(
    folio: str,
    estado: str,
    *,
    pendientes: str = "",
    siguiente_accion: str = "",
    origen: str = "Dato del usuario",
    cerrar: bool = False,
) -> Avance:
    expediente = obtener(folio)
    if expediente is None:
        raise ValueError(f"No existe el expediente {folio}.")
    if not expediente.abierto:
        raise ValueError(f"El expediente {expediente.folio} está cerrado.")
    estado = estado.strip()
    if not estado:
        raise ValueError("El estado del avance es obligatorio.")
    origen = elegir(origen, ORIGENES, "Origen")
    with get_db_conn() as conn:
        fila = conn.execute("SELECT id FROM expedientes WHERE folio = ?", (expediente.folio,)).fetchone()
        conn.execute(
            """
            INSERT INTO avances (expediente_id, estado, pendientes, siguiente_accion, origen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fila["id"], estado, pendientes.strip(), siguiente_accion.strip(), origen),
        )
        conn.execute(
            "UPDATE expedientes SET abierto = ?, actualizado_en = CURRENT_TIMESTAMP WHERE id = ?",
            (0 if cerrar else 1, fila["id"]),
        )
        conn.commit()
    return avances(expediente.folio)[-1]


def avances(folio: str) -> list[Avance]:
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute(
            """
            SELECT a.estado, a.pendientes, a.siguiente_accion, a.origen, a.registrado_en
            FROM avances a JOIN expedientes e ON e.id = a.expediente_id
            WHERE e.folio = ? ORDER BY a.id
            """,
            (folio.strip().upper(),),
        ).fetchall()
    return [Avance(**dict(f)) for f in filas]


def evaluaciones(folio: str) -> list[EvaluacionVinculada]:
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute(
            """
            SELECT id, recommendation AS decision, total_score AS puntaje, hash, evaluated_at AS evaluado_en
            FROM grant_evaluations WHERE expediente_folio = ? ORDER BY id
            """,
            (folio.strip().upper(),),
        ).fetchall()
    return [EvaluacionVinculada(**dict(f)) for f in filas]


def listar(responsable: str | None = None, estado: str = "abiertos", limite: int = 50) -> list[Expediente]:
    """`estado`: abiertos, cerrados o todos."""
    estado = elegir(estado, ("abiertos", "cerrados", "todos"), "Estado")
    condiciones, parametros = [], []
    if estado != "todos":
        condiciones.append("abierto = ?")
        parametros.append(1 if estado == "abiertos" else 0)
    if responsable:
        condiciones.append("lower(responsable) LIKE ?")
        parametros.append(f"%{responsable.strip().lower()}%")
    donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute(
            f"SELECT * FROM expedientes {donde} ORDER BY id DESC LIMIT ?", (*parametros, limite)
        ).fetchall()
    return [_expediente(f) for f in filas]
