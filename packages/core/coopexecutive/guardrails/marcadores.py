"""Marcadores estándar para datos que faltan y etiquetas de procedencia.

Cuando un dato no está en la entrada, el perfil o una fuente verificada, se deja
el marcador en lugar de inventarlo.
"""
from __future__ import annotations

MONTO_POR_DEFINIR = "MONTO POR DEFINIR"
COSTO_POR_COTIZAR = "COSTO POR COTIZAR"
VIGENCIA_NO_VERIFICADA = "VIGENCIA NO VERIFICADA"

# Solo para respuestas de chat del procurador; nunca se escribe en archivos.
LEYENDA_BORRADOR = "Borrador: requiere revisión humana."

# Procedencia de cada dato registrado en un expediente.
ORIGENES: tuple[str, ...] = (
    "Dato del usuario",
    "Dato institucional",
    "Dato público verificado",
    "Propuesta del agente",
)


def pendiente(dato: str) -> str:
    """Marcador para un dato faltante: `[PENDIENTE: dato]`."""
    return f"[PENDIENTE: {dato.strip()}]"
