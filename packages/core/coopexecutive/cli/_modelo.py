"""Consultas al modelo desde la CLI: errores legibles, JSON validado y revisión estricta."""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Coroutine
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from coopexecutive.cli._consola import fallar
from coopexecutive.providers import ErrorProveedor

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

_BLOQUE_JSON = re.compile(r"\{.*\}", re.DOTALL)


def ejecutar(corrutina: Coroutine[Any, Any, T]) -> T:
    """Corre la corrutina; si el proveedor falla, termina con código 1 y un mensaje claro."""
    try:
        return asyncio.run(corrutina)
    except ErrorProveedor as exc:
        fallar(str(exc), "Error del modelo")


def extraer_json(texto: str) -> dict[str, Any]:
    texto = re.sub(r"```(?:json)?", "", texto)
    encontrado = _BLOQUE_JSON.search(texto)
    if not encontrado:
        raise ValueError("El modelo no devolvió un objeto JSON.")
    datos = json.loads(encontrado.group(0))
    if not isinstance(datos, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return datos


async def consultar(pregunta: str, rol: str | None = "procurador") -> tuple[str, str]:
    """Devuelve (respuesta, bloque de perfil) con el rol indicado."""
    from coopexecutive.orchestrator.coop_executive import CoopExecutive

    executive = CoopExecutive()
    partes = [chunk async for chunk in executive.stream_chat(pregunta, specialist_focus=rol)]
    return "".join(partes), executive.profile.to_prompt_block()


def pedir_modelo(pregunta: str, modelo: type[M], rol: str | None = "procurador") -> tuple[M, str]:
    """Pide un JSON al modelo y lo valida. Devuelve (datos, bloque de perfil)."""
    respuesta, perfil = ejecutar(consultar(pregunta, rol))
    try:
        return modelo.model_validate(extraer_json(respuesta)), perfil
    except (ValueError, ValidationError) as exc:
        fallar(f"La propuesta del modelo no es válida: {exc}", "Propuesta no válida")
