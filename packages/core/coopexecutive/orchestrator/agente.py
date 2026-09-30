"""Turno de conversación con herramientas: el modelo consulta y, con permiso, escribe.

`ejecutar_turno` alterna llamadas al modelo y ejecuciones de herramientas hasta que el
modelo responde sin pedir ninguna o se alcanza `max_pasos`. Toda herramienta que
escribe pasa antes por `confirmar`; si la persona dice que no, el modelo lo sabe y la
revisión posterior no acepta que diga que la acción se hizo.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from coopexecutive import bitacora, herramientas
from coopexecutive.herramientas import Herramienta, Resultado
from coopexecutive.providers import ErrorProveedor
from coopexecutive.providers.tipos import LlamadaHerramienta, TextoDelta

MAX_PASOS = 6
LARGO_RESULTADO = 12_000

INSTRUCCIONES = """### Herramientas
Tienes herramientas para consultar y registrar la información de la organización.
- Usa `fecha_y_plazos` para la fecha de hoy y los días a un cierre; no los calcules de memoria.
- Usa las consultas antes de afirmar qué hay registrado; si una consulta no trae el dato, el dato no consta.
- Las herramientas que escriben piden permiso a la persona. Si lo niega, no digas que se hizo.
- Si falta un dato obligatorio para una herramienta, pregúntalo; no lo inventes. Nunca inventes montos ni fechas.
- Al terminar, di en una línea qué se consultó o registró."""

Confirmar = Callable[[Herramienta, dict[str, Any]], Awaitable[bool]]


@dataclass(frozen=True)
class Aviso:
    """Nota para la persona que no forma parte de la respuesta del modelo."""

    texto: str


Evento = TextoDelta | Resultado | Aviso


async def _negar(_h: Herramienta, _a: dict[str, Any]) -> bool:
    return False


def _rechazo(nombre: str, argumentos: dict[str, Any], motivo: str, canal: str) -> Resultado:
    bitacora.registrar_sin_fallar(canal, f"herramienta:{nombre}", argumentos, estado="error", resultado=motivo)
    return Resultado(nombre, argumentos, "error", {"error": motivo})


def _contenido(resultado: Resultado) -> str:
    texto = resultado.para_modelo()
    if len(texto) > LARGO_RESULTADO:
        texto = texto[:LARGO_RESULTADO] + " ... [resultado recortado]"
    return texto


async def _ejecutar(llamada: LlamadaHerramienta, disponibles: dict[str, Herramienta], confirmar: Confirmar,
                    canal: str) -> Resultado:
    if llamada.argumentos_invalidos:
        return _rechazo(llamada.nombre, {}, "Los argumentos no son un JSON válido; vuelve a intentarlo.", canal)
    h = disponibles.get(llamada.nombre)
    if h is None:
        return _rechazo(llamada.nombre, llamada.argumentos, f"La herramienta «{llamada.nombre}» no está disponible.",
                        canal)
    autorizada = await confirmar(h, llamada.argumentos) if h.escribe else False
    return await asyncio.to_thread(herramientas.ejecutar, h.nombre, llamada.argumentos, canal=canal,
                                   autorizada=autorizada)


async def ejecutar_turno(
    executive: Any,
    mensaje: str,
    historial: list[dict[str, Any]] | None = None,
    *,
    rol: str | None = None,
    confirmar: Confirmar = _negar,
    disponibles: list[Herramienta] | None = None,
    max_pasos: int = MAX_PASOS,
    canal: str = "agente",
) -> AsyncIterator[Evento]:
    """Emite el texto del modelo, cada herramienta ejecutada y los avisos del turno."""
    lista = herramientas.todas() if disponibles is None else disponibles
    por_nombre = {h.nombre: h for h in lista}
    esquemas = herramientas.para_modelo(lista) or None
    mensajes: list[dict[str, Any]] = [
        {"role": "system", "content": f"{executive.build_system_prompt(rol)}\n\n{INSTRUCCIONES}"},
        *(historial or []),
        {"role": "user", "content": mensaje},
    ]
    for paso in range(max_pasos):
        texto = ""
        llamadas: list[LlamadaHerramienta] = []
        try:
            async for evento in executive.client.eventos(mensajes, tools=esquemas):
                if isinstance(evento, TextoDelta):
                    texto += evento.texto
                    yield evento
                elif isinstance(evento, LlamadaHerramienta):
                    llamadas.append(evento)
        except ErrorProveedor as exc:
            # Algunos modelos rechazan el parámetro `tools`: se reintenta una vez sin herramientas.
            if exc.estado == 400 and esquemas and paso == 0 and not texto:
                esquemas = None
                yield Aviso("El modelo no aceptó herramientas; esta respuesta no consulta los registros.")
                continue
            raise
        if not llamadas:
            return
        mensajes.append({
            "role": "assistant",
            "content": texto or None,
            "tool_calls": [
                {"id": ll.id, "type": "function",
                 "function": {"name": ll.nombre, "arguments": json.dumps(ll.argumentos, ensure_ascii=False)}}
                for ll in llamadas
            ],
        })
        for llamada in llamadas:
            resultado = await _ejecutar(llamada, por_nombre, confirmar, canal)
            yield resultado
            mensajes.append({"role": "tool", "tool_call_id": llamada.id, "content": _contenido(resultado)})
    yield Aviso(f"Se alcanzó el límite de {max_pasos} pasos con herramientas; la respuesta puede estar incompleta.")


def resumen_acciones(resultados: list[Resultado]) -> str:
    """Una línea para el historial: qué herramientas corrieron y cómo terminaron."""
    if not resultados:
        return ""
    partes = [f"{r.nombre} ({r.estado})" for r in resultados]
    return "[Herramientas en este turno: " + ", ".join(partes) + "]"


def contexto_de(resultados: list[Resultado]) -> str:
    """Datos devueltos por las herramientas, para que la revisión acepte los montos y fechas que traen."""
    return "\n".join(json.dumps(r.datos, ensure_ascii=False, default=str) for r in resultados if r.ok)
