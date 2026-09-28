"""Línea de comandos de CoopExecutive."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table

from coopexecutive.cli import crm as _crm
from coopexecutive.cli import documentos as _documentos
from coopexecutive.cli import monitoreo as _monitoreo
from coopexecutive.cli import procuracion as _procuracion
from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings, usar_espacio
from coopexecutive import identidad as _identidad
from coopexecutive.guardrails import LEYENDA_BORRADOR, agregar_leyenda, revisar_respuesta
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.orchestrator.coop_executive import CoopExecutive
from coopexecutive.governance.voting import (
    create_proposal,
    cast_vote,
    tally_votes,
    list_proposals,
    get_proposal,
    VoteChoice,
)
from coopexecutive.utils.fechas import hoy_local, local_desde_utc


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


@cli.command()
@click.argument("pregunta")
@click.option("--rol", default=None, help="Especialista a enfocar: procurador, vigilancia, legal, finanzas, tecnico, comunicacion, asamblea")
@click.option("--estricto", is_flag=True, help="Sustituir montos y fechas sin respaldo por marcadores antes de mostrar la respuesta.")
def ask(pregunta: str, rol: str | None, estricto: bool) -> None:
    """Hacer una consulta directa al Director Colegiado."""
    asyncio.run(_ask(pregunta, rol, estricto))


async def _ask(pregunta: str, rol: str | None, estricto: bool = False) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold green]🏛️ CoopExecutive ({executive.profile.name})[/bold green]\n")
    texto = ""
    async for chunk in executive.stream_chat(pregunta, specialist_focus=rol):
        texto += chunk
        if not estricto:
            console.print(chunk, end="", highlight=False)
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
        console.print(final, highlight=False)
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
def chat() -> None:
    """Iniciar sesión interactiva con el Director Colegiado de la cooperativa."""
    asyncio.run(_chat())


async def _chat() -> None:
    executive = CoopExecutive()
    settings = get_settings()
    _identidad.mostrar_intro(console, executive.profile, settings.company_profile_path.parent)
    console.print(
        f"Organización: [bold]{executive.profile.name}[/bold] · {executive.profile.legal_structure}\n"
        f"Modelo IA: [bold yellow]{settings.default_model}[/bold yellow] · Escribe 'salir' para terminar\n",
        highlight=False,
    )

    history: list[dict[str, str]] = []

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]Asamblea / Tú[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Sesión finalizada. En favor del bien común.[/dim]")
            break

        if user_input.lower() in ("salir", "exit", "quit", "q"):
            console.print("[dim]Sesión finalizada.[/dim]")
            break

        if not user_input.strip():
            continue

        console.print("\n[bold green]🏛️ CoopExecutive[/bold green]\n")
        response_text = ""
        async for chunk in executive.stream_chat(user_input, history=history):
            response_text += chunk
            console.print(chunk, end="", highlight=False)
        console.print("\n")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response_text})


@cli.command("marco-logico")
@click.argument("proyecto", type=str)
def marco_logico(proyecto: str) -> None:
    """Generar la Matriz de Marco Lógico 4x4 y Teoría del Cambio para un proyecto."""
    asyncio.run(_marco_logico(proyecto))


async def _marco_logico(proyecto: str) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold cyan]📐 Generando Matriz de Marco Lógico (MML) para: {proyecto}[/bold cyan]\n")
    
    prompt = (
        f"Para la organización {executive.profile.name}, genera una propuesta técnica con Metodología de Marco Lógico "
        f"para el proyecto: '{proyecto}'.\n"
        f"Incluye:\n"
        f"1. Planteamiento del problema y Árbol de Objetivos.\n"
        f"2. Teoría del Cambio (Theory of Change) vinculada a los ODS (ODS 7, 8, 9 o 12).\n"
        f"3. Matriz 4x4 de Marco Lógico (Fin, Propósito, Componentes y Actividades) con Indicadores, Medios de Verificación y Supuestos."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("presupuesto")
@click.argument("proyecto", type=str)
def presupuesto(proyecto: str) -> None:
    """Generar un presupuesto auditable y desglose de costos para un proyecto."""
    asyncio.run(_presupuesto(proyecto))


async def _presupuesto(proyecto: str) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold cyan]💰 Estructurando Presupuesto Auditable para: {proyecto}[/bold cyan]\n")
    
    prompt = (
        f"Actúa como el Agente Procurador de Fondos de {executive.profile.name}. "
        f"Estructura un presupuesto detallado y auditable para el proyecto: '{proyecto}'.\n"
        f"Incluye:\n"
        f"1. Tabla de costos desglosada por rubros estándar de cooperación internacional: "
        f"Personal Técnico, Equipamiento/CAPEX, Gastos Operativos/OPEX, Auditoría Externa y Costos Indirectos (máx 7-10%).\n"
        f"2. Distinción clara entre Fondos Solicitados al Donante y Contrapartida Institucional (en especie o valorizada).\n"
        f"3. Resumen financiero total y notas de justificación presupuestal."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("dossier")
@click.argument("proyecto")
@click.option("--donante", default="Banco Interamericano de Desarrollo / Agencias Multilaterales", help="Agencia donante o cooperante")
@click.option("--convocatoria", default="Fondo de Transición Sostenible y Economía Social", help="Título de la convocatoria")
def dossier(proyecto: str, donante: str, convocatoria: str) -> None:
    """Generar un dossier formal de postulación técnica y financiera."""
    asyncio.run(_dossier(proyecto, donante, convocatoria))


async def _dossier(proyecto: str, donante: str, convocatoria: str) -> None:
    executive = CoopExecutive()
    console.print(f"[bold cyan]📁 Generando Dossier Multilateral de Postulación:[/bold cyan] {proyecto}")
    console.print(f"[dim]Donante: {donante} | Convocatoria: {convocatoria}[/dim]\n")

    prompt = (
        f"Actúa como el Agente Procurador de Fondos Colegiado de {executive.profile.name}.\n"
        f"Redacta un Dossier Formal Completo de Postulación para el proyecto '{proyecto}', dirigido a '{donante}' "
        f"bajo la convocatoria '{convocatoria}'.\n"
        f"Estructura el documento con el máximo rigor técnico conforme a los estándares de Research Grants y RBM:\n"
        f"1. Resumen Ejecutivo y Perfil del Proponente (subrayando el modelo cooperativo y asambleario).\n"
        f"2. Diagnóstico del Problema Central y Línea Base.\n"
        f"3. Matriz de Marco Lógico 4x4 (Fin, Propósito, Componentes, Actividades) con ODS vinculados.\n"
        f"4. Plan Presupuestal Consolidado (Fondos Solicitados vs. Contrapartida en Especie).\n"
        f"5. Salvaguardas Cooperativas y Anticorrupción (Fondo de Reserva 15%, Previsión 10%, Educación 10%).\n"
        f"6. Estrategia de Sostenibilidad y Salida Post-Donante."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("dashboard")
def dashboard() -> None:
    """Abrir el Panel de Control Web y Gobernanza Colegiada en el navegador."""
    import webbrowser
    from pathlib import Path
    web_file = Path(__file__).resolve().parent.parent / "web" / "dashboard.html"
    console.print(f"[bold cyan]🌐 Abriendo Panel de Control Web:[/bold cyan] {web_file}")
    webbrowser.open(web_file.as_uri())


@cli.command("info")
def info() -> None:
    """Mostrar la información y estatus de la organización activa."""
    executive = CoopExecutive()
    console.print(Panel(
        Markdown(executive.profile.to_prompt_block()),
        title=f"🏛️ Organización Activa: {executive.profile.name}",
        border_style="cyan"
    ))



# ------------------------------------------------------------------------------
# Comandos de Gobernanza Democrática y Votaciones (Un Socio = Un Voto)
# ------------------------------------------------------------------------------

@cli.command("propuesta")
@click.argument("titulo", type=str)
@click.option("--descripcion", "-d", required=True, type=str, help="Materia detallada de la propuesta a votar.")
@click.option("--categoria", "-c", default="subvencion", type=click.Choice(["subvencion", "estatutario", "financiero", "operativo"]), help="Categoría estatutaria.")
def cmd_propuesta(titulo: str, descripcion: str, categoria: str) -> None:
    """Registrar una nueva propuesta a someter a votación de la Asamblea."""
    try:
        prop_id = create_proposal(titulo, descripcion, categoria)
        body = (
            f"[bold green]✓ Propuesta registrada con éxito[/bold green]\n\n"
            f"[bold]Folio Oficial:[/bold] #{prop_id}\n"
            f"[bold]Título:[/bold] {titulo}\n"
            f"[bold]Categoría:[/bold] {categoria.upper()}\n"
            f"[bold]Descripción:[/bold] {descripcion}\n\n"
            f"[dim]Para emitir un voto ejecute:[/dim]\n"
            f"[cyan]uv run coopexecutive votar {prop_id} --socio-id SOC-001 --socio-nombre \"Nombre\" --voto A_FAVOR[/cyan]"
        )
        console.print(Panel(body, title="🗳️ Nueva Propuesta de Asamblea", border_style="green"))
    except ValueError as e:
        console.print(Panel(f"[bold red]✗ Error Estatutario:[/bold red] {e}", title="Alerta LGSC", border_style="red"))


@cli.command("propuestas")
@click.option("--estatus", default=None, help="Filtrar por estatus (abierta, aprobada, rechazada)")
def cmd_propuestas(estatus: str | None) -> None:
    """Listar las propuestas de asamblea registradas."""
    props = list_proposals(estatus)
    if not props:
        console.print("[dim]No hay propuestas registradas en la memoria.[/dim]")
        return

    table = Table(title="🗳️ Propuestas de Asamblea General", show_header=True, header_style="bold cyan")
    table.add_column("Folio", style="dim", no_wrap=True)
    table.add_column("Categoría", no_wrap=True)
    table.add_column("Título", ratio=1)
    table.add_column("Estatus", no_wrap=True)
    table.add_column("Fecha", no_wrap=True)

    for p in props:
        status_color = "green" if p["status"] == "abierta" else ("cyan" if p["status"] == "aprobada" else "red")
        table.add_row(
            f"#{p['id']}",
            p["category"].upper(),
            p["title"],
            f"[{status_color}]{p['status'].upper()}[/{status_color}]",
            local_desde_utc(p["created_at"]).strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@cli.command("votar")
@click.argument("propuesta_id", type=int)
@click.option("--socio-id", "-s", required=True, type=str, help="ID o número de socio acreditado.")
@click.option("--socio-nombre", "-n", required=True, type=str, help="Nombre completo del socio.")
@click.option("--voto", "-v", required=True, type=click.Choice(["A_FAVOR", "EN_CONTRA", "ABSTENCION"], case_sensitive=False), help="Sentido del voto.")
@click.option("--justificacion", "-j", default="", type=str, help="Fundamentación opcional del voto.")
def cmd_votar(propuesta_id: int, socio_id: str, socio_nombre: str, voto: str, justificacion: str) -> None:
    """Emitir voto soberano en una propuesta de asamblea (Un Socio = Un Voto)."""
    try:
        res = cast_vote(propuesta_id, socio_id, socio_nombre, voto, justificacion)
        color = "green" if res["choice"] == "A_FAVOR" else ("red" if res["choice"] == "EN_CONTRA" else "yellow")
        body = (
            f"[bold green]✓ Cédula de Voto Recibida y Registrada[/bold green]\n\n"
            f"[bold]Propuesta Folio:[/bold] #{propuesta_id}\n"
            f"[bold]Socio Acreditado:[/bold] {socio_nombre} ([dim]{socio_id}[/dim])\n"
            f"[bold]Sentido del Voto:[/bold] [{color}]{res['choice']}[/{color}]\n"
            f"[dim]Principio LGSC salvaguardado: Un socio = Un voto.[/dim]"
        )
        console.print(Panel(body, title="🗳️ Acreditación de Voto", border_style="cyan"))
    except ValueError as e:
        console.print(Panel(f"[bold red]✗ Rechazo de Cédula:[/bold red] {e}", title="Error de Votación", border_style="red"))


@cli.command("escrutinio")
@click.argument("propuesta_id", type=int)
@click.option("--padron", "-p", default=12, type=int, help="Número total de socios activos en el padrón.")
def cmd_escrutinio(propuesta_id: int, padron: int) -> None:
    """Efectuar el escrutinio de votos y emitir el Acta de Resolución."""
    try:
        tally = tally_votes(propuesta_id, total_census_members=padron)
        console.print("\n")
        console.print(Markdown(tally["acta_md"]))
    except ValueError as e:
        console.print(Panel(f"[bold red]✗ Error en Escrutinio:[/bold red] {e}", title="Error", border_style="red"))


for _comando in (*_procuracion.COMANDOS, *_crm.COMANDOS, *_documentos.COMANDOS, *_monitoreo.COMANDOS):
    cli.add_command(_comando)


if __name__ == "__main__":
    cli()
