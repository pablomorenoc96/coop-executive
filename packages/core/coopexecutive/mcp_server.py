"""Servidor MCP: expone las herramientas de CoopExecutive a cualquier cliente MCP.

Usa el transporte stdio, así que stdout queda reservado para el protocolo; los
mensajes de registro van a stderr. Las herramientas que escriben se anuncian sin
`readOnlyHint` para que el cliente pida permiso a la persona antes de llamarlas.
Toda llamada queda en la bitácora con el canal `mcp`.
"""
from __future__ import annotations

import json
from typing import Any

from coopexecutive import __version__, herramientas
from coopexecutive.registro import obtener

registro = obtener(__name__)

INSTRUCCIONES = (
    "Herramientas de procuración de fondos de una organización de la economía social: perfil, "
    "financiadores, expedientes, evaluación de convocatorias con matriz, documentos Word, monitoreo "
    "y asamblea. No inventes montos, fechas ni resultados: si un dato falta, dilo. Las herramientas "
    "que escriben requieren que la persona lo autorice."
)


class FaltaMCP(RuntimeError):
    """El extra `mcp` no está instalado."""


def crear_servidor(*, solo_lectura: bool = False):
    """Servidor MCP de bajo nivel con el catálogo de herramientas."""
    try:
        import anyio
        from mcp import types
        from mcp.server import Server
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise FaltaMCP(
            "Falta el SDK de MCP. Instálelo con: pip install 'coopexecutive[mcp]' "
            "(o uv sync --extra mcp)."
        ) from exc

    disponibles = {h.nombre: h for h in herramientas.todas(solo_lectura=solo_lectura)}

    def _tool(h: herramientas.Herramienta) -> types.Tool:
        return types.Tool(
            name=h.nombre,
            description=h.descripcion,
            input_schema=h.esquema(),
            annotations=types.ToolAnnotations(
                read_only_hint=not h.escribe,
                destructive_hint=False if h.escribe else None,
                open_world_hint=h.red,
            ),
        )

    async def listar(_ctx: Any, _params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[_tool(h) for h in disponibles.values()])

    async def llamar(_ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        if params.name not in disponibles:
            texto = f"La herramienta «{params.name}» no está disponible en este servidor."
            return types.CallToolResult(content=[types.TextContent(type="text", text=texto)], is_error=True)
        # El cliente MCP ya pidió permiso por las anotaciones; aquí se ejecuta y se registra.
        resultado = await anyio.to_thread.run_sync(
            lambda: herramientas.ejecutar(params.name, params.arguments, canal="mcp", autorizada=True)
        )
        datos = {"estado": resultado.estado, **resultado.datos}
        texto = json.dumps(datos, ensure_ascii=False, default=str, indent=1)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=texto)],
            structured_content=json.loads(json.dumps(datos, default=str)),
            is_error=not resultado.ok,
        )

    return Server(
        "coopexecutive",
        version=__version__,
        instructions=INSTRUCCIONES,
        on_list_tools=listar,
        on_call_tool=llamar,
    )


async def servir_stdio(*, solo_lectura: bool = False) -> None:
    from mcp.server.stdio import stdio_server

    servidor = crear_servidor(solo_lectura=solo_lectura)
    registro.info("Servidor MCP listo en stdio (%s herramientas).", "solo lectura" if solo_lectura else "todas las")
    async with stdio_server() as (lectura, escritura):
        await servidor.run(lectura, escritura, servidor.create_initialization_options())
