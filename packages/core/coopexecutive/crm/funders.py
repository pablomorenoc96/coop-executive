"""Base de financiadores: donantes, fundaciones, gobierno, agencias y financieras.

Cada registro lleva folio `FIN-AAAA-NNNN`. Los duplicados se detectan por nombre
normalizado (sin acentos, mayúsculas ni puntuación).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date
from typing import Any

from pydantic import BaseModel

from coopexecutive.crm._comun import elegir, es_folio, monto_valido, siguiente_folio
from coopexecutive.guardrails.marcadores import MONTO_POR_DEFINIR
from coopexecutive.memory.episodic import get_db_conn, initialize_db
from coopexecutive.utils.fechas import MESES
from coopexecutive.utils.moneda import formatear_monto, validar_moneda
from coopexecutive.utils.texto import normalizar

TIPOS: tuple[str, ...] = (
    "Empresa",
    "Fundación",
    "Persona física",
    "Agencia internacional",
    "Gobierno",
    "Institución financiera",
)
CANALES: tuple[str, ...] = (
    "Correo",
    "Teléfono",
    "Reunión",
    "Evento",
    "Referencia",
    "Convocatoria pública",
    "Sitio web",
    "Redes sociales",
    "Otro",
)
ESTATUS: tuple[str, ...] = (
    "Prospecto",
    "Contactado",
    "En negociación",
    "Propuesta enviada",
    "Comprometido",
    "Recibido",
    "Declinado",
    "Inactivo",
)

# El proyecto describe la iniciativa; montos y fechas tienen sus propios campos.
_MONTO_O_FECHA = re.compile(
    r"\$|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s*(?:mil|millones|MXN|USD|EUR|pesos|d[oó]lares)\b"
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"
    rf"|\b\d{{1,2}} de (?:{'|'.join(MESES)})\b",
    re.IGNORECASE,
)


class FinanciadorDuplicado(ValueError):
    def __init__(self, folio: str, organizacion: str) -> None:
        super().__init__(f"«{organizacion}» ya está registrado con el folio {folio}.")
        self.folio = folio


class Financiador(BaseModel):
    folio: str
    organizacion: str
    proyecto: str
    tipo: str
    canal: str
    contacto: str = ""
    moneda: str
    monto_solicitado: float | None = None
    monto_comprometido: float | None = None
    monto_recibido: float | None = None
    estatus: str = "Prospecto"
    seguimiento: date | None = None
    notas: str = ""
    creado_en: str = ""
    actualizado_en: str = ""

    def monto(self, valor: float | None) -> str:
        return MONTO_POR_DEFINIR if valor is None else formatear_monto(valor, self.moneda)


def _desde_fila(fila: sqlite3.Row) -> Financiador:
    datos = {k: fila[k] for k in fila.keys() if k in Financiador.model_fields}
    return Financiador(**datos)


def _validar_proyecto(proyecto: str) -> str:
    proyecto = proyecto.strip()
    if not proyecto:
        raise ValueError("El proyecto es obligatorio.")
    if _MONTO_O_FECHA.search(proyecto):
        raise ValueError(
            "El proyecto describe la iniciativa; los montos y las fechas se registran en sus propios campos."
        )
    return proyecto


def _validar_seguimiento(seguimiento: date | None, hoy: date | None) -> date | None:
    if seguimiento is None:
        return None
    if hoy is None:
        from coopexecutive.utils.fechas import hoy_local

        hoy = hoy_local()
    if seguimiento < hoy:
        raise ValueError(f"El seguimiento ({seguimiento.isoformat()}) no puede ser anterior a hoy.")
    return seguimiento


def registrar(
    organizacion: str,
    proyecto: str,
    tipo: str,
    canal: str,
    *,
    moneda: str = "MXN",
    monto_solicitado: float | None = None,
    contacto: str = "",
    seguimiento: date | None = None,
    notas: str = "",
    hoy: date | None = None,
) -> Financiador:
    organizacion = organizacion.strip()
    if not organizacion:
        raise ValueError("La organización es obligatoria.")
    proyecto = _validar_proyecto(proyecto)
    tipo = elegir(tipo, TIPOS, "Tipo")
    canal = elegir(canal, CANALES, "Canal")
    moneda = validar_moneda(moneda)
    monto_solicitado = monto_valido(monto_solicitado, "Monto solicitado")
    seguimiento = _validar_seguimiento(seguimiento, hoy)
    anio = (hoy or _hoy()).year
    clave = normalizar(organizacion)

    initialize_db()
    with get_db_conn() as conn:
        previo = conn.execute(
            "SELECT folio FROM financiadores WHERE organizacion_normalizada = ?", (clave,)
        ).fetchone()
        if previo:
            raise FinanciadorDuplicado(previo["folio"], organizacion)
        folio = siguiente_folio(conn, "financiadores", "FIN", anio)
        conn.execute(
            """
            INSERT INTO financiadores
                (folio, organizacion, organizacion_normalizada, proyecto, tipo, canal, contacto,
                 moneda, monto_solicitado, estatus, seguimiento, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Prospecto', ?, ?)
            """,
            (folio, organizacion, clave, proyecto, tipo, canal, contacto.strip(), moneda,
             monto_solicitado, seguimiento.isoformat() if seguimiento else None, notas.strip()),
        )
        conn.commit()
    return ver(folio)  # type: ignore[return-value]


def _hoy() -> date:
    from coopexecutive.utils.fechas import hoy_local

    return hoy_local()


def ver(folio: str) -> Financiador | None:
    initialize_db()
    with get_db_conn() as conn:
        fila = conn.execute(
            "SELECT * FROM financiadores WHERE folio = ?", (folio.strip().upper(),)
        ).fetchone()
    return _desde_fila(fila) if fila else None


def buscar(texto: str = "", limite: int = 20) -> list[Financiador]:
    """Por folio exacto o por texto parcial en la organización o el proyecto.

    Sin texto, devuelve los registros más recientes.
    """
    initialize_db()
    texto = texto.strip()
    with get_db_conn() as conn:
        if es_folio(texto, "FIN"):
            filas = conn.execute(
                "SELECT * FROM financiadores WHERE folio = ?", (texto.upper(),)
            ).fetchall()
        elif texto:
            patron = f"%{normalizar(texto)}%"
            filas = conn.execute(
                """
                SELECT * FROM financiadores
                WHERE organizacion_normalizada LIKE ? OR lower(proyecto) LIKE ?
                ORDER BY id DESC LIMIT ?
                """,
                (patron, f"%{texto.lower()}%", limite),
            ).fetchall()
        else:
            filas = conn.execute(
                "SELECT * FROM financiadores ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
    return [_desde_fila(f) for f in filas]


def actualizar(
    folio: str,
    *,
    estatus: str | None = None,
    canal: str | None = None,
    contacto: str | None = None,
    proyecto: str | None = None,
    moneda: str | None = None,
    monto_solicitado: float | None = None,
    monto_comprometido: float | None = None,
    monto_recibido: float | None = None,
    seguimiento: date | None = None,
    notas: str | None = None,
    hoy: date | None = None,
) -> Financiador:
    actual = ver(folio)
    if actual is None:
        raise ValueError(f"No existe el financiador {folio}.")
    cambios: dict[str, Any] = {}
    if estatus is not None:
        cambios["estatus"] = elegir(estatus, ESTATUS, "Estatus")
    if canal is not None:
        cambios["canal"] = elegir(canal, CANALES, "Canal")
    if contacto is not None:
        cambios["contacto"] = contacto.strip()
    if proyecto is not None:
        cambios["proyecto"] = _validar_proyecto(proyecto)
    if moneda is not None:
        cambios["moneda"] = validar_moneda(moneda)
    for campo, valor, etiqueta in (
        ("monto_solicitado", monto_solicitado, "Monto solicitado"),
        ("monto_comprometido", monto_comprometido, "Monto comprometido"),
        ("monto_recibido", monto_recibido, "Monto recibido"),
    ):
        if valor is not None:
            cambios[campo] = monto_valido(valor, etiqueta)
    if seguimiento is not None:
        cambios["seguimiento"] = _validar_seguimiento(seguimiento, hoy).isoformat()  # type: ignore[union-attr]
    if notas is not None:
        cambios["notas"] = notas.strip()
    if not cambios:
        return actual

    asignaciones = ", ".join(f"{campo} = ?" for campo in cambios)
    with get_db_conn() as conn:
        conn.execute(
            f"UPDATE financiadores SET {asignaciones}, actualizado_en = CURRENT_TIMESTAMP WHERE folio = ?",
            (*cambios.values(), actual.folio),
        )
        conn.commit()
    return ver(actual.folio)  # type: ignore[return-value]
