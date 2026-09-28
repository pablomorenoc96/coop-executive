"""Normalización de texto para comparar nombres sin acentos, mayúsculas ni puntuación."""
from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """«Fundación  Ejemplo, A.C.» -> «fundacion ejemplo ac» (los puntos no separan siglas)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    sin_puntos = re.sub(r"[.'’]", "", sin_acentos.casefold())
    return re.sub(r"[^0-9a-z]+", " ", sin_puntos).strip()
