"""Marcadores estándar para datos que faltan y etiquetas de procedencia.

Cuando un dato no está en la entrada, el perfil o una fuente verificada, se deja
el marcador en lugar de inventarlo.
"""
from __future__ import annotations

MONTO_POR_DEFINIR = "MONTO POR DEFINIR"
COSTO_POR_COTIZAR = "COSTO POR COTIZAR"
VIGENCIA_NO_VERIFICADA = "VIGENCIA NO VERIFICADA"
RESPONSABLE_POR_CONFIRMAR = "RESPONSABLE POR CONFIRMAR"
ESTATUS_FISCAL_PENDIENTE = "ESTATUS FISCAL PENDIENTE"
MECANISMO_DONACION_PENDIENTE = "MECANISMO DE DONACIÓN PENDIENTE"

MARCADORES: tuple[str, ...] = (
    MONTO_POR_DEFINIR,
    COSTO_POR_COTIZAR,
    VIGENCIA_NO_VERIFICADA,
    RESPONSABLE_POR_CONFIRMAR,
    ESTATUS_FISCAL_PENDIENTE,
    MECANISMO_DONACION_PENDIENTE,
)

# Solo para respuestas de chat del procurador; nunca se escribe en archivos.
LEYENDA_BORRADOR = "Borrador: requiere revisión humana."

# Etiquetas de origen que acompañan cada dato importante de una respuesta o documento.
ETIQUETAS: tuple[str, ...] = (
    "DATO DEL USUARIO",
    "DATO INSTITUCIONAL",
    "DATO PÚBLICO VERIFICADO",
    "SUPUESTO",
    "INFERENCIA ESTRATÉGICA",
    "NO VERIFICADO",
    "PENDIENTE",
)

# Procedencia de cada avance registrado en un expediente. «Propuesta del agente»
# se conserva por compatibilidad con expedientes anteriores.
ORIGENES: tuple[str, ...] = (
    "Dato del usuario",
    "Dato institucional",
    "Dato público verificado",
    "Supuesto",
    "Inferencia estratégica",
    "No verificado",
    "Propuesta del agente",
)

_EQUIVALENCIAS = {"Propuesta del agente": "INFERENCIA ESTRATÉGICA"}


def etiqueta_de(origen: str) -> str:
    """Etiqueta en mayúsculas para un origen de `ORIGENES`."""
    return _EQUIVALENCIAS.get(origen, origen.upper())


def pendiente(dato: str) -> str:
    """Marcador para un dato faltante: `[PENDIENTE: dato]`."""
    return f"[PENDIENTE: {dato.strip()}]"
