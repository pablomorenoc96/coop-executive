"""Línea de comandos de CoopExecutive."""
from __future__ import annotations

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
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from coopexecutive import identidad as _identidad
from coopexecutive.cli import analisis as _analisis
from coopexecutive.cli import asamblea as _asamblea
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
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.orchestrator.coop_executive import ROLES, CoopExecutive
from coopexecutive.providers import ErrorProveedor
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


@cli.command()
@click.argument("pregunta")
@_ROL
@click.option("--estricto", is_flag=True,
              help="Sustituir montos y fechas sin respaldo por marcadores antes de mostrar la respuesta.")
def ask(pregunta: str, rol: str | None, estricto: bool) -> None:
    """Hacer una consulta directa al Director Colegiado."""
    ejecutar(_ask(pregunta, rol, estricto))


async def _ask(pregunta: str, rol: str | None, estricto: bool = False) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold green]CoopExecutive ({executive.profile.name})[/bold green]\n", highlight=False)
    texto = ""
    async for chunk in executive.stream_chat(pregunta, specialist_focus=rol):
        texto += chunk
        if not estricto:
            console.print(chunk, end="", highlight=False, markup=False)
    if not estricto and rol != "procurador":
        console.print("\n")
        return

    # Revisión posterior: montos y fechas sin respaldo, emojis, extensión y contrapunto.
    contexto = f"{pregunta}\n{executive.profile.to_prompt_block()}"
    revision = revisar_respuesta(
        texto, contexto, estricto=estricto, hoy=hoy_local(executive.settings.user_timezone)
    )
    if estricto:
        final = agregar_leyenda(revision.texto) if rol == "procurador" else revision.texto
        console.print(final, highlight=False, markup=False)
    else:
        console.print(f"\n\n{LEYENDA_BORRADOR}", highlight=False)
    if revision.observaciones:
        console.print(Panel(
            "\n".join(f"- {o}" for o in revision.observaciones),
            title="Revisión automática",
            border_style="yellow",
        ))
    console.print()


@cli.command()
@_ROL
def chat(rol: str | None) -> None:
    """Iniciar sesión interactiva con el Director Colegiado."""
    ejecutar(_chat(rol))


async def _chat(rol: str | None = None) -> None:
    executive = CoopExecutive()
    settings = get_settings()
    _identidad.mostrar_intro(console, executive.profile, settings.company_profile_path.parent)
    console.print(
        f"Organización: [bold]{executive.profile.name}[/bold] · {executive.profile.legal_structure}\n"
        f"Modelo IA: [bold yellow]{settings.default_model}[/bold yellow] · Escriba 'salir' para terminar\n",
        highlight=False,
    )

    history: list[dict[str, str]] = []
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
        response_text = ""
        try:
            async for chunk in executive.stream_chat(user_input, history=history, specialist_focus=rol):
                response_text += chunk
                console.print(chunk, end="", highlight=False, markup=False)
        except ErrorProveedor as exc:
            # Un error del proveedor no termina la sesión; el turno fallido no entra al historial.
            console.print(Panel(f"[bold red]{exc}[/bold red]", title="Error del modelo", border_style="red"))
            continue
        console.print("\n")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response_text})


@cli.command("dashboard")
def dashboard() -> None:
    """Abrir el panel web en el navegador."""
    import webbrowser

    web_file = Path(__file__).resolve().parent.parent / "web" / "dashboard.html"
    console.print(f"[bold cyan]Abriendo el panel:[/bold cyan] {web_file}", highlight=False)
    webbrowser.open(web_file.as_uri())


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
    *_analisis.COMANDOS, *_redaccion.COMANDOS,
):
    cli.add_command(_comando)


if __name__ == "__main__":
    cli()
