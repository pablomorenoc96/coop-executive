"""Consultas al modelo desde la CLI: errores legibles, JSON validado y revisión estricta."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import date
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from rich.markdown import Markdown
from rich.panel import Panel

from coopexecutive.cli._consola import console, fallar
from coopexecutive.guardrails import agregar_leyenda, revisar_respuesta
from coopexecutive.providers import ErrorProveedor
from coopexecutive.utils.texto import extraer_json

__all__ = ["consultar", "ejecutar", "extraer_json", "mostrar_revisada", "pedir_modelo"]

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


def ejecutar(corrutina: Coroutine[Any, Any, T]) -> T:
    """Corre la corrutina; si el proveedor falla, termina con código 1 y un mensaje claro."""
    try:
        return asyncio.run(corrutina)
    except ErrorProveedor as exc:
        fallar(str(exc), "Error del modelo")


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


def mostrar_revisada(texto: str, contexto: str, titulo: str, hoy: date, *, leyenda: bool = True) -> str:
    """Revisión estricta, panel con el resultado y las observaciones. Devuelve el texto revisado.

    La leyenda de borrador solo se muestra en la terminal; no entra al texto devuelto.
    """
    revision = revisar_respuesta(texto, contexto, estricto=True, hoy=hoy)
    mostrado = agregar_leyenda(revision.texto) if leyenda else revision.texto
    console.print(Panel(Markdown(mostrado), title=titulo, border_style="cyan"))
    if revision.observaciones:
        console.print(Panel("\n".join(f"- {o}" for o in revision.observaciones),
                            title="Revisión automática", border_style="yellow"))
    return revision.texto
