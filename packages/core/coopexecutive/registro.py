"""Registro de eventos en stderr, con el nivel de LOG_LEVEL.

Nunca se escribe en stdout: el servidor MCP usa stdout para el protocolo.
"""
from __future__ import annotations

import logging
import sys

RAIZ = "coopexecutive"


def configurar_registro(nivel: str = "WARNING") -> logging.Logger:
    registro = logging.getLogger(RAIZ)
    registro.setLevel(nivel.upper())
    if not any(getattr(h, "_coopexecutive", False) for h in registro.handlers):
        manejador = logging.StreamHandler(sys.stderr)
        manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S"))
        manejador._coopexecutive = True  # type: ignore[attr-defined]
        registro.addHandler(manejador)
    registro.propagate = False
    return registro


def obtener(nombre: str) -> logging.Logger:
    """Logger hijo de `coopexecutive` (p. ej. `obtener(__name__)`)."""
    return logging.getLogger(nombre if nombre.startswith(RAIZ) else f"{RAIZ}.{nombre}")
