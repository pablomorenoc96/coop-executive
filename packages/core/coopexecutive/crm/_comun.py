"""Piezas compartidas por financiadores y expedientes."""
from __future__ import annotations

import re
import sqlite3
from typing import Sequence

from coopexecutive.utils.texto import normalizar


def siguiente_folio(conn: sqlite3.Connection, tabla: str, prefijo: str, anio: int) -> str:
    """Folio consecutivo por año: PREFIJO-AAAA-NNNN."""
    base = f"{prefijo}-{anio}-"
    fila = conn.execute(
        f"SELECT folio FROM {tabla} WHERE folio LIKE ? ORDER BY folio DESC LIMIT 1", (base + "%",)
    ).fetchone()
    consecutivo = int(fila["folio"].rsplit("-", 1)[1]) + 1 if fila else 1
    return f"{base}{consecutivo:04d}"


def elegir(valor: str, catalogo: Sequence[str], campo: str) -> str:
    """Devuelve la forma canónica del catálogo, sin distinguir acentos ni mayúsculas."""
    buscado = normalizar(valor)
    for opcion in catalogo:
        if normalizar(opcion) == buscado:
            return opcion
    raise ValueError(f"{campo} «{valor}» no es válido. Opciones: {', '.join(catalogo)}.")


def es_folio(texto: str, prefijo: str) -> bool:
    return re.fullmatch(rf"{prefijo}-\d{{4}}-\d{{4}}", texto.strip().upper()) is not None


def monto_valido(monto: float | None, campo: str) -> float | None:
    if monto is None:
        return None
    if monto < 0:
        raise ValueError(f"{campo}: el monto no puede ser negativo.")
    return float(monto)
