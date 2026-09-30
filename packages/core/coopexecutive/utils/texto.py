"""Normalización de texto para comparar nombres sin acentos, mayúsculas ni puntuación."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

_BLOQUE_JSON = re.compile(r"\{.*\}", re.DOTALL)


def normalizar(texto: str) -> str:
    """«Fundación  Ejemplo, A.C.» -> «fundacion ejemplo ac» (los puntos no separan siglas)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    sin_puntos = re.sub(r"[.'’]", "", sin_acentos.casefold())
    return re.sub(r"[^0-9a-z]+", " ", sin_puntos).strip()


def extraer_json(texto: str) -> dict[str, Any]:
    """Primer objeto JSON de una respuesta del modelo, aunque venga entre cercas de código."""
    texto = re.sub(r"```(?:json)?", "", texto)
    encontrado = _BLOQUE_JSON.search(texto)
    if not encontrado:
        raise ValueError("El modelo no devolvió un objeto JSON.")
    datos = json.loads(encontrado.group(0))
    if not isinstance(datos, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return datos
