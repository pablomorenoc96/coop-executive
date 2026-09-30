"""Línea de comandos de CoopExecutive."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
import httpx
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from coopexecutive import herramientas as _herramientas
from coopexecutive import identidad as _identidad
from coopexecutive.cli import analisis as _analisis
from coopexecutive.cli import asamblea as _asamblea
from coopexecutive.cli import auditoria as _auditoria
from coopexecutive.cli import crm as _crm
from coopexecutive.cli import documentos as _documentos
from coopexecutive.cli import monitoreo as _monitoreo
from coopexecutive.cli import procuracion as _procuracion
from coopexecutive.cli import proyecto as _proyecto
from coopexecutive.cli import redaccion as _redaccion
from coopexecutive.cli._consola import console, fallar
from coopexecutive.cli._modelo import ejecutar
from coopexecutive.config import env_cargados, get_settings, usar_espacio
from coopexecutive.guardrails import LEYENDA_BORRADOR, agregar_leyenda, revisar_respuesta
from coopexecutive.herramientas import Herramienta, Resultado
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.orchestrator.agente import contexto_de, ejecutar_turno, resumen_acciones
from coopexecutive.orchestrator.coop_executive import ROLES, CoopExecutive
from coopexecutive.providers import ErrorProveedor
from coopexecutive.providers.tipos import TextoDelta
from coopexecutive.registro import configurar_registro
from coopexecutive.utils.fechas import hoy_local


@click.group(invoke_without_command=True)
@click.option(
    "--espacio",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Carpeta de la organización (perfil, base de datos y salidas). También: COOPEXECUTIVE_WORKSPACE.",
)
@click.pass_context
def cli(ctx: click.Context, espacio: Path | None) -> None:
    """CoopExecutive — Sistema Directivo y Procurador de Fondos para la Economía Social."""
    ctx.ensure_object(dict)
    ctx.obj["espacio"] = espacio
    if espacio is not None:
        usar_espacio(espacio)
    configurar_registro(get_settings().log_level)
    if ctx.invoked_subcommand is None:
        _mostrar_intro()
        console.print(ctx.get_help(), highlight=False)


def _mostrar_intro() -> None:
    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    _identidad.mostrar_intro(console, perfil, settings.company_profile_path.parent)


@cli.group(invoke_without_command=True)
@click.pass_context
def intro(ctx: click.Context) -> None:
    """Mostrar la intro de la organización (o la de CoopExecutive si no tiene una)."""
    if ctx.invoked_subcommand is None:
        _mostrar_intro()


@intro.command("generar")
def intro_generar() -> None:
    """Crear intro.txt con el logo, la fuente y el lema del bloque `identidad` del perfil."""
    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    try:
        destino = _identidad.generar_para_perfil(perfil, settings.company_profile_path.parent)
    except (RuntimeError, OSError, ValueError) as exc:
        fallar(str(exc), "No se generó la intro")
    _mostrar_intro()
    console.print(f"[green]Intro guardada en[/green] {destino}", highlight=False)


_ROL = click.option("--rol", default=None, type=click.Choice(sorted(ROLES)), help="Especialista a enfocar.")
_SIN_HERRAMIENTAS = click.option("--sin-herramientas", is_flag=True,
                                 help="Solo conversar: el modelo no consulta ni registra nada.")
SI = {"s", "si", "sí", "y", "yes"}
_SOLO_LECTURA = click.option("--solo-lectura", is_flag=True,
                             help="Ofrecer solo las herramientas de consulta; ninguna que escriba.")


@cli.command()
@click.argument("pregunta")
@_ROL
@click.option("--estricto", is_flag=True,
              help="Sustituir montos y fechas sin respaldo por marcadores antes de mostrar la respuesta.")
@_SIN_HERRAMIENTAS
@_SOLO_LECTURA
def ask(pregunta: str, rol: str | None, estricto: bool, sin_herramientas: bool, solo_lectura: bool) -> None:
    """Hacer una consulta directa al Director Colegiado."""
    ejecutar(_ask(pregunta, rol, estricto, sin_herramientas, solo_lectura))


async def _confirmar_cli(h: Herramienta, argumentos: dict) -> bool:
    """Muestra la acción y pide un sí explícito. Sin terminal interactiva, la respuesta es no."""
    detalle = json.dumps(argumentos, ensure_ascii=False, indent=2, default=str)
    console.print(Panel(escape(detalle), title=f"Acción que escribe: {h.nombre}", border_style="yellow"),
                  highlight=False)
    try:
        respuesta = await asyncio.to_thread(click.prompt, "¿Autoriza esta acción? [s/N]", default="n",
                                            show_default=False)
    except (click.Abort, EOFError):
        console.print("[dim]Sin respuesta: la acción no se ejecutó.[/dim]")
        return False
    return respuesta.strip().lower() in SI


async def _turno(executive: CoopExecutive, mensaje: str, historial: list[dict], rol: str | None, *,
                 mostrar: bool, sin_herramientas: bool, solo_lectura: bool) -> tuple[str, list[Resultado]]:
    """Un turno completo. Devuelve el texto del modelo y las herramientas ejecutadas."""
    texto = ""
    resultados: list[Resultado] = []
    if sin_herramientas:
        async for chunk in executive.stream_chat(mensaje, history=historial, specialist_focus=rol):
            texto += chunk
            if mostrar:
                console.print(chunk, end="", highlight=False, markup=False)
        return texto, resultados
    disponibles = _herramientas.todas(solo_lectura=solo_lectura)
    async for evento in ejecutar_turno(executive, mensaje, historial, rol=rol, confirmar=_confirmar_cli,
                                       disponibles=disponibles):
        if isinstance(evento, TextoDelta):
            texto += evento.texto
            if mostrar:
                console.print(evento.texto, end="", highlight=False, markup=False)
        elif isinstance(evento, Resultado):
            resultados.append(evento)
            detalle = str(evento.datos.get("error") or evento.datos.get("resumen") or "")
            color = {"ok": "cyan", "denegada": "yellow"}.get(evento.estado, "red")
            console.print(f"\n[{color}]· {evento.nombre} ({evento.estado})[/{color}] [dim]{escape(detalle)}[/dim]",
                          highlight=False)
        else:
            console.print(f"\n[yellow]{escape(evento.texto)}[/yellow]", highlight=False)
    return texto, resultados


def _panel_acciones(resultados: list[Resultado]) -> None:
    if not resultados:
        return
    tabla = Table(show_header=True, header_style="bold")
    tabla.add_column("Herramienta")
    tabla.add_column("Estado")
    tabla.add_column("Resultado")
    for r in resultados:
        tabla.add_row(r.nombre, r.estado, escape(str(r.datos.get("error") or r.datos.get("resumen") or "")))
    console.print(Panel(tabla, title="Acciones ejecutadas", border_style="cyan"))


async def _ask(pregunta: str, rol: str | None, estricto: bool = False, sin_herramientas: bool = False,
               solo_lectura: bool = False) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold green]CoopExecutive ({executive.profile.name})[/bold green]\n", highlight=False)
    texto, resultados = await _turno(executive, pregunta, [], rol, mostrar=not estricto,
                                     sin_herramientas=sin_herramientas, solo_lectura=solo_lectura)
    escritas = any(r.ok and r.escribe for r in resultados)
    # Revisión posterior: montos y fechas sin respaldo, emojis, extensión, contrapunto y acciones afirmadas.
    contexto = f"{pregunta}\n{executive.profile.to_prompt_block()}\n{contexto_de(resultados)}"
    revision = revisar_respuesta(texto, contexto, estricto=estricto, acciones_ejecutadas=escritas,
                                 hoy=hoy_local(executive.settings.user_timezone))
    completa = estricto or rol == "procurador"
    if estricto:
        final = agregar_leyenda(revision.texto) if rol == "procurador" else revision.texto
        console.print(final, highlight=False, markup=False)
    elif completa:
        console.print(f"\n\n{LEYENDA_BORRADOR}", highlight=False)
    else:
        console.print("\n")
    # Sin revisión completa solo se avisa de acciones afirmadas que no se ejecutaron.
    observaciones = revision.observaciones if completa else [
        o for o in revision.observaciones if o.startswith("Afirma una acción")
    ]
    if observaciones:
        console.print(Panel("\n".join(f"- {escape(o)}" for o in observaciones), title="Revisión automática",
                            border_style="yellow"))
    _panel_acciones(resultados)
    console.print()


@cli.command()
@_ROL
@_SIN_HERRAMIENTAS
@_SOLO_LECTURA
def chat(rol: str | None, sin_herramientas: bool, solo_lectura: bool) -> None:
    """Iniciar sesión interactiva con el Director Colegiado."""
    ejecutar(_chat(rol, sin_herramientas, solo_lectura))


async def _chat(rol: str | None = None, sin_herramientas: bool = False, solo_lectura: bool = False) -> None:
    executive = CoopExecutive()
    settings = get_settings()
    _identidad.mostrar_intro(console, executive.profile, settings.company_profile_path.parent)
    modo = "sin herramientas" if sin_herramientas else ("solo consultas" if solo_lectura else "con herramientas")
    console.print(
        f"Organización: [bold]{executive.profile.name}[/bold] · {executive.profile.legal_structure}\n"
        f"Modelo IA: [bold yellow]{settings.default_model}[/bold yellow] · {modo} · Escriba 'salir' para terminar\n",
        highlight=False,
    )

    history: list[dict] = []
    while True:
        try:
            user_input = Prompt.ask("[bold yellow]Usted[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Sesión finalizada.[/dim]")
            break
        if user_input.lower() in ("salir", "exit", "quit", "q"):
            console.print("[dim]Sesión finalizada.[/dim]")
            break
        if not user_input.strip():
            continue

        console.print("\n[bold green]CoopExecutive[/bold green]\n")
        try:
            response_text, resultados = await _turno(executive, user_input, history, rol, mostrar=True,
                                                     sin_herramientas=sin_herramientas, solo_lectura=solo_lectura)
        except ErrorProveedor as exc:
            # Un error del proveedor no termina la sesión; el turno fallido no entra al historial.
            console.print(Panel(f"[bold red]{escape(str(exc))}[/bold red]", title="Error del modelo",
                                border_style="red"))
            continue
        console.print("\n")
        escritas = any(r.ok and r.escribe for r in resultados)
        revision = revisar_respuesta(response_text, contexto_de(resultados), acciones_ejecutadas=escritas)
        for o in revision.observaciones:
            if o.startswith("Afirma una acción"):
                console.print(f"[yellow]Revisión: {escape(o)}[/yellow]", highlight=False)
        # El historial guarda solo texto: los resultados completos no se reenvían en cada turno.
        acciones = resumen_acciones(resultados)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": f"{response_text}\n{acciones}".strip()})


@cli.command("panel")
@click.option("--puerto", default=8765, show_default=True, type=click.IntRange(1024, 65535))
@click.option("--no-abrir", is_flag=True, help="No abrir el navegador.")
def panel(puerto: int, no_abrir: bool) -> None:
    """Panel web local con los datos reales de la organización y un chat con confirmación."""
    try:
        import uvicorn

        from coopexecutive.web.app import crear_app, nuevo_token
    except ImportError:
        fallar("Faltan fastapi y uvicorn. Instálelos con: pip install 'coopexecutive[web]' "
               "(o uv sync --extra web).", "Panel no disponible")
    token = nuevo_token()
    app = crear_app(token=token, puerto=puerto)
    direccion = f"http://127.0.0.1:{puerto}/#token={token}"
    console.print(
        f"[bold cyan]Panel en[/bold cyan] {direccion}\n"
        "[dim]Solo escucha en este equipo. El enlace incluye un token nuevo en cada arranque; "
        "Ctrl+C para detenerlo.[/dim]",
        highlight=False,
    )
    if not no_abrir:
        import threading
        import webbrowser

        threading.Timer(1.0, webbrowser.open, args=(direccion,)).start()
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


cli.add_command(panel, "dashboard")


@cli.command("mcp")
@click.option("--solo-lectura", is_flag=True, help="Anunciar solo las herramientas que no escriben.")
def mcp(solo_lectura: bool) -> None:
    """Servidor MCP en stdio para Claude Desktop, Claude Code u otro cliente compatible."""
    from coopexecutive.mcp_server import FaltaMCP, servir_stdio

    try:
        asyncio.run(servir_stdio(solo_lectura=solo_lectura))
    except FaltaMCP as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(1) from exc
    except KeyboardInterrupt:
        pass


cli.add_command(mcp, "servidor-mcp")


@cli.command("info")
def info() -> None:
    """Mostrar la organización activa y la configuración cargada."""
    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    console.print(Panel(
        Markdown(perfil.to_prompt_block()),
        title=f"Organización activa: {perfil.name}",
        border_style="cyan",
    ))
    cargados = env_cargados()
    env = ", ".join(str(r) for r in cargados) if cargados else "ninguno; se usan los valores por omisión"
    if settings.usa_local:
        proveedor, modelo = "local (Ollama)", ", ".join(settings.local_models_list)
    else:
        proveedor, modelo = settings.provider, settings.default_model
    console.print(
        f"[bold]Perfil:[/bold] {settings.company_profile_path}\n"
        f"[bold]Archivos .env:[/bold] {env}\n"
        f"[bold]Proveedor:[/bold] {proveedor} · [bold]Modelo:[/bold] {modelo}",
        highlight=False,
    )


def _admite_herramientas(modelo: dict) -> bool:
    return "tools" in (modelo.get("supported_parameters") or [])


@cli.command("modelos")
@click.option("--herramientas", is_flag=True, help="Solo los que aceptan llamadas a herramientas.")
def modelos(herramientas: bool) -> None:
    """Listar los modelos gratuitos disponibles hoy en OpenRouter."""
    settings = get_settings()
    try:
        respuesta = httpx.get(f"{settings.openrouter_base_url.rstrip('/')}/models", timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json().get("data", [])
    except (httpx.HTTPError, ValueError) as exc:
        fallar(f"No se pudo consultar la lista de modelos: {exc}", "Sin conexión")
    gratuitos = [m for m in datos if str(m.get("id", "")).endswith(":free")]
    if herramientas:
        gratuitos = [m for m in gratuitos if _admite_herramientas(m)]
    if not gratuitos:
        console.print("[yellow]No hay modelos gratuitos que cumplan el filtro.[/yellow]")
        return
    tabla = Table(title=f"Modelos gratuitos en OpenRouter ({len(gratuitos)})", header_style="bold cyan")
    tabla.add_column("Modelo", no_wrap=True)
    tabla.add_column("Contexto", justify="right")
    tabla.add_column("Herramientas", justify="center")
    for m in sorted(gratuitos, key=lambda m: m["id"]):
        marca = " (por omisión)" if m["id"] == settings.default_model else ""
        tabla.add_row(m["id"] + marca, f"{m.get('context_length') or 0:,}", "sí" if _admite_herramientas(m) else "no")
    console.print(tabla)
    console.print("[dim]Se cambia con DEFAULT_MODEL en el archivo .env.[/dim]")


for _comando in (
    *_procuracion.COMANDOS, *_proyecto.COMANDOS, *_asamblea.COMANDOS,
    *_crm.COMANDOS, *_documentos.COMANDOS, *_monitoreo.COMANDOS,
    *_analisis.COMANDOS, *_redaccion.COMANDOS, *_auditoria.COMANDOS,
):
    cli.add_command(_comando)

# Cada comando que cambia algo queda en la bitácora con sus parámetros censurados.
_auditoria.auditar(cli)


if __name__ == "__main__":
    cli()
