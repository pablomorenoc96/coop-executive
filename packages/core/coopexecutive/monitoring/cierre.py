"""Fecha de cierre de un aviso, en español o inglés.

Solo se acepta una fecha que aparece poco después de una palabra de cierre
(«fecha límite», «cierra», «deadline»...). Una fecha suelta puede ser la de
publicación o la de inicio del programa, así que no cuenta: el aviso queda con
la vigencia sin verificar.
"""
from __future__ import annotations

import re
from datetime import date

from coopexecutive.utils.texto import normalizar

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}
_MES = "(" + "|".join(sorted(MESES, key=len, reverse=True)) + ")"
_ORDINAL = r"(?:st|nd|rd|th)?"

CLAVES = re.compile(
    r"fecha limite|fecha de cierre|cierre|cierra|vence|vencimiento|hasta el|a mas tardar"
    r"|deadline|closing date|closes|close on|due date|due by|apply by|submit by|until"
)

# El texto llega normalizado: minúsculas, sin acentos y sin signos (las diagonales se vuelven espacios).
_FORMATOS = [
    ("ymd", re.compile(r"\b(\d{4}) (\d{1,2}) (\d{1,2})\b")),
    ("dmy_es", re.compile(rf"\b(\d{{1,2}}){_ORDINAL} (?:de )?{_MES} (?:de |del )?(\d{{4}})\b")),
    ("mdy", re.compile(rf"\b{_MES} (\d{{1,2}}){_ORDINAL} (\d{{4}})\b")),
    ("dmy_num", re.compile(r"\b(\d{1,2}) (\d{1,2}) (\d{4})\b")),
]

VENTANA = 90  # caracteres después de la palabra de cierre


def _a_fecha(formato: str, grupos: tuple[str, ...]) -> date | None:
    try:
        if formato == "ymd":
            return date(int(grupos[0]), int(grupos[1]), int(grupos[2]))
        if formato == "dmy_es":
            return date(int(grupos[2]), MESES[grupos[1]], int(grupos[0]))
        if formato == "mdy":
            return date(int(grupos[2]), MESES[grupos[0]], int(grupos[1]))
        # dd/mm/aaaa, la convención de México.
        return date(int(grupos[2]), int(grupos[1]), int(grupos[0]))
    except ValueError:
        return None


def _primera_fecha(tramo: str) -> date | None:
    candidatas: list[tuple[int, date]] = []
    for formato, patron in _FORMATOS:
        for m in patron.finditer(tramo):
            fecha = _a_fecha(formato, m.groups())
            if fecha is not None:
                candidatas.append((m.start(), fecha))
    return min(candidatas)[1] if candidatas else None


def extraer_cierre(texto: str) -> date | None:
    """Primera fecha válida que sigue a una palabra de cierre, o None."""
    limpio = normalizar(texto)
    for clave in CLAVES.finditer(limpio):
        fecha = _primera_fecha(limpio[clave.end(): clave.end() + VENTANA])
        if fecha is not None:
            return fecha
    return None
