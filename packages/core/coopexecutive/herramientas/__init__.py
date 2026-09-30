"""Herramientas que pueden llamar el modelo, el servidor MCP y la API local.

Cada herramienta valida su entrada con pydantic y devuelve un diccionario JSON. Las
que escriben (`escribe=True`) nunca se ejecutan sin confirmación: el agente pregunta
antes, la API exige `confirmar` y el servidor MCP las anuncia sin `readOnlyHint` para
que el cliente pida permiso. Toda ejecución queda en la bitácora.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from coopexecutive import bitacora

__all__ = ["Herramienta", "Resultado", "ejecutar", "obtener", "para_modelo", "todas"]


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    descripcion: str
    Entrada: type[BaseModel]
    funcion: Callable[[Any], dict[str, Any]]
    escribe: bool = False
    red: bool = False  # consulta sitios externos

    def esquema(self) -> dict[str, Any]:
        """Esquema JSON de la entrada, sin referencias `$ref` (algunos proveedores no las aceptan)."""
        return _sin_referencias(self.Entrada.model_json_schema())

    def para_modelo(self) -> dict[str, Any]:
        return {"name": self.nombre, "description": self.descripcion, "parameters": self.esquema()}

    def resumen(self, argumentos: dict[str, Any]) -> str:
        """Una línea para pedir confirmación: nombre y argumentos."""
        return f"{self.nombre} {json.dumps(argumentos, ensure_ascii=False, default=str)}"


@dataclass(frozen=True)
class Resultado:
    nombre: str
    argumentos: dict[str, Any]
    estado: str  # ok, error o denegada
    datos: dict[str, Any]
    escribe: bool = False

    @property
    def ok(self) -> bool:
        return self.estado == "ok"

    def para_modelo(self) -> str:
        """Contenido del mensaje `tool` que recibe el modelo."""
        if self.estado == "denegada":
            return json.dumps({"estado": "denegada", "mensaje": "El usuario no autorizó esta acción; no se ejecutó. "
                               "No digas que se hizo."}, ensure_ascii=False)
        return json.dumps({"estado": self.estado, **self.datos}, ensure_ascii=False, default=str)


def _sin_referencias(esquema: dict[str, Any]) -> dict[str, Any]:
    definiciones = esquema.pop("$defs", {})

    def resolver(nodo: Any) -> Any:
        if isinstance(nodo, dict):
            ref = nodo.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                base = copy.deepcopy(definiciones[ref.split("/")[-1]])
                extra = {k: v for k, v in nodo.items() if k != "$ref"}
                return resolver({**base, **extra})
            return {k: resolver(v) for k, v in nodo.items() if not (k == "title" and isinstance(v, str))}
        if isinstance(nodo, list):
            return [resolver(v) for v in nodo]
        return nodo

    return resolver(esquema)


_REGISTRO: dict[str, Herramienta] = {}


def registrar(herramienta: Herramienta) -> Herramienta:
    if herramienta.nombre in _REGISTRO:
        raise ValueError(f"La herramienta {herramienta.nombre} ya está registrada.")
    _REGISTRO[herramienta.nombre] = herramienta
    return herramienta


def _cargar() -> None:
    if not _REGISTRO:
        from coopexecutive.herramientas import catalogo  # noqa: F401 - registra al importarse


def todas(*, solo_lectura: bool = False) -> list[Herramienta]:
    _cargar()
    return [h for h in _REGISTRO.values() if not (solo_lectura and h.escribe)]


def obtener(nombre: str) -> Herramienta | None:
    _cargar()
    return _REGISTRO.get(nombre)


def para_modelo(herramientas: list[Herramienta]) -> list[dict[str, Any]]:
    return [h.para_modelo() for h in herramientas]


def _errores(exc: ValidationError) -> str:
    partes = []
    for e in exc.errors():
        campo = ".".join(str(x) for x in e.get("loc", ())) or "entrada"
        partes.append(f"{campo}: {e.get('msg', 'no válido')}")
    return "; ".join(partes)


def ejecutar(nombre: str, argumentos: dict[str, Any] | None, *, canal: str, autorizada: bool = False) -> Resultado:
    """Valida y ejecuta. Una herramienta que escribe sin `autorizada=True` queda denegada."""
    argumentos = dict(argumentos or {})
    h = obtener(nombre)
    if h is None:
        resultado = Resultado(nombre, argumentos, "error", {"error": f"No existe la herramienta «{nombre}»."})
    elif h.escribe and not autorizada:
        resultado = Resultado(nombre, argumentos, "denegada", {}, escribe=True)
    else:
        try:
            entrada = h.Entrada.model_validate(argumentos)
            resultado = Resultado(nombre, argumentos, "ok", h.funcion(entrada), escribe=h.escribe)
        except ValidationError as exc:
            resultado = Resultado(nombre, argumentos, "error", {"error": f"Entrada no válida: {_errores(exc)}"},
                                  escribe=h.escribe)
        except (ValueError, LookupError, OSError) as exc:
            resultado = Resultado(nombre, argumentos, "error", {"error": str(exc)}, escribe=h.escribe)
    resumen = resultado.datos.get("error") or resultado.datos.get("resumen") or ""
    bitacora.registrar_sin_fallar(canal, f"herramienta:{nombre}", argumentos, estado=resultado.estado,
                                  resultado=str(resumen))
    return resultado
