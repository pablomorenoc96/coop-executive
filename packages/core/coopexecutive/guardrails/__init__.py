"""Reglas contra datos inventados: marcadores estándar y revisión posterior de respuestas."""
from coopexecutive.guardrails.marcadores import (
    COSTO_POR_COTIZAR,
    LEYENDA_BORRADOR,
    MONTO_POR_DEFINIR,
    ORIGENES,
    VIGENCIA_NO_VERIFICADA,
    pendiente,
)
from coopexecutive.guardrails.revision import Revision, agregar_leyenda, revisar_respuesta

__all__ = [
    "COSTO_POR_COTIZAR",
    "LEYENDA_BORRADOR",
    "MONTO_POR_DEFINIR",
    "ORIGENES",
    "VIGENCIA_NO_VERIFICADA",
    "pendiente",
    "Revision",
    "agregar_leyenda",
    "revisar_respuesta",
]
