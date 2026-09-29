"""Eventos que emite el cliente de modelos y el error común de los proveedores."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextoDelta:
    """Fragmento de texto de la respuesta."""

    texto: str


@dataclass(frozen=True)
class LlamadaHerramienta:
    """El modelo pide ejecutar una herramienta. `argumentos` ya viene decodificado."""

    id: str
    nombre: str
    argumentos: dict[str, Any] = field(default_factory=dict)
    argumentos_invalidos: str = ""


@dataclass(frozen=True)
class Fin:
    """Fin de la respuesta: `motivo` es 'stop', 'tool_calls' o 'length'."""

    motivo: str
    modelo: str
    proveedor: str


Evento = TextoDelta | LlamadaHerramienta | Fin


class ErrorProveedor(Exception):
    """Fallo al consultar el modelo. El mensaje nunca contiene claves."""

    def __init__(self, mensaje: str, *, estado: int | None = None, proveedor: str = "", modelo: str = "") -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.proveedor = proveedor
        self.modelo = modelo


def censurar(texto: str, secretos: list[str | None]) -> str:
    """Sustituye cada secreto por `***` (solo los de 6 caracteres o más)."""
    for secreto in secretos:
        if secreto and len(secreto) >= 6:
            texto = texto.replace(secreto, "***")
    return texto
