"""Comandos de asamblea: padrón de socios, propuestas, votos y escrutinio."""
from __future__ import annotations

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings
from coopexecutive.governance import voting
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import local_desde_utc


def _perfil_con_asamblea() -> CoopProfile:
    perfil = CoopProfile.load_from_yaml(get_settings().company_profile_path)
    if not perfil.tiene_asamblea:
        aprobadores = "; ".join(perfil.procuracion.aprobadores) if perfil.procuracion else ""
        fallar(
            "La organización no tiene asamblea en su perfil. Declare un bloque `governance` "
            "o registre las decisiones con sus aprobadores" + (f" ({aprobadores})." if aprobadores else "."),
            "Sin asamblea",
        )
    return perfil


# --- Padrón ------------------------------------------------------------------------


@click.group("socios")
def socios() -> None:
    """Padrón de socios activos (base del cuórum)."""


@socios.command("alta")
@click.argument("socio_id")
@click.option("--nombre", "-n", required=True, help="Nombre del socio.")
def socios_alta(socio_id: str, nombre: str) -> None:
    """Dar de alta o reactivar a un socio."""
    _perfil_con_asamblea()
    try:
        voting.alta_socio(socio_id, nombre)
    except ValueError as exc:
        fallar(str(exc), "Alta rechazada")
    console.print(f"[green]Socio {socio_id} activo. Padrón: {voting.padron_activo()}.[/green]")


@socios.command("baja")
@click.argument("socio_id")
def socios_baja(socio_id: str) -> None:
    """Dar de baja a un socio (sus votos anteriores se conservan)."""
    _perfil_con_asamblea()
    try:
        voting.baja_socio(socio_id)
    except ValueError as exc:
        fallar(str(exc), "Baja rechazada")
    console.print(f"[green]Socio {socio_id} dado de baja. Padrón: {voting.padron_activo()}.[/green]")


@socios.command("listar")
@click.option("--todos", is_flag=True, help="Incluir a los socios dados de baja.")
def socios_listar(todos: bool) -> None:
    """Listar el padrón."""
    filas = voting.listar_socios(solo_activos=not todos)
    if not filas:
        console.print("[dim]No hay socios registrados. Use: coopexecutive socios alta ID --nombre ...[/dim]")
        return
    tabla = Table(title=f"Padrón de socios ({voting.padron_activo()} activos)", header_style="bold cyan")
    tabla.add_column("ID", no_wrap=True)
    tabla.add_column("Nombre", ratio=1)
    tabla.add_column("Estado", no_wrap=True)
    for f in filas:
        tabla.add_row(f["socio_id"], f["nombre"], "activo" if f["activo"] else "baja")
    console.print(tabla)


# --- Propuestas --------------------------------------------------------------------


@click.command("propuesta")
@click.argument("titulo", type=str)
@click.option("--descripcion", "-d", required=True, type=str, help="Materia de la propuesta a votar.")
@click.option("--categoria", "-c", default="subvencion",
              type=click.Choice(["subvencion", "estatutario", "financiero", "operativo"]), help="Categoría.")
def cmd_propuesta(titulo: str, descripcion: str, categoria: str) -> None:
    """Registrar una propuesta para votación de la asamblea."""
    _perfil_con_asamblea()
    try:
        prop_id = voting.create_proposal(titulo, descripcion, categoria)
    except ValueError as exc:
        fallar(str(exc), "Error Estatutario")
    body = (
        f"[bold green]Propuesta registrada[/bold green]\n\n"
        f"[bold]Folio:[/bold] #{prop_id}\n"
        f"[bold]Título:[/bold] {titulo}\n"
        f"[bold]Categoría:[/bold] {categoria.upper()}\n"
        f"[bold]Descripción:[/bold] {descripcion}\n\n"
        f"[dim]Para votar:[/dim] [cyan]coopexecutive votar {prop_id} --socio-id ID --voto A_FAVOR[/cyan]"
    )
    console.print(Panel(body, title="Nueva propuesta de asamblea", border_style="green"), highlight=False)


@click.command("propuestas")
@click.option("--estatus", default=None, type=click.Choice(["abierta", "aprobada", "rechazada"]),
              help="Filtrar por estatus.")
def cmd_propuestas(estatus: str | None) -> None:
    """Listar las propuestas de asamblea."""
    props = voting.list_proposals(estatus)
    if not props:
        console.print("[dim]No hay propuestas registradas.[/dim]")
        return
    table = Table(title="Propuestas de asamblea", show_header=True, header_style="bold cyan")
    table.add_column("Folio", style="dim", no_wrap=True)
    table.add_column("Categoría", no_wrap=True)
    table.add_column("Título", ratio=1)
    table.add_column("Estatus", no_wrap=True)
    table.add_column("Fecha", no_wrap=True)
    colores = {"abierta": "green", "aprobada": "cyan"}
    for p in props:
        color = colores.get(p["status"], "red")
        table.add_row(
            f"#{p['id']}",
            p["category"].upper(),
            p["title"],
            f"[{color}]{p['status'].upper()}[/{color}]",
            local_desde_utc(p["created_at"]).strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@click.command("votar")
@click.argument("propuesta_id", type=int)
@click.option("--socio-id", "-s", required=True, type=str, help="Identificador del socio en el padrón.")
@click.option("--socio-nombre", "-n", default="", type=str,
              help="Nombre del socio; solo hace falta si no hay padrón registrado.")
@click.option("--voto", "-v", required=True,
              type=click.Choice(["A_FAVOR", "EN_CONTRA", "ABSTENCION"], case_sensitive=False), help="Sentido del voto.")
@click.option("--justificacion", "-j", default="", type=str, help="Fundamentación opcional del voto.")
def cmd_votar(propuesta_id: int, socio_id: str, socio_nombre: str, voto: str, justificacion: str) -> None:
    """Emitir un voto en una propuesta abierta (un socio, un voto)."""
    _perfil_con_asamblea()
    try:
        res = voting.cast_vote(propuesta_id, socio_id, socio_nombre, voto, justificacion)
    except ValueError as exc:
        fallar(str(exc), "Voto rechazado")
    color = {"A_FAVOR": "green", "EN_CONTRA": "red"}.get(res["choice"], "yellow")
    body = (
        f"[bold green]Voto registrado[/bold green]\n\n"
        f"[bold]Propuesta:[/bold] #{propuesta_id}\n"
        f"[bold]Socio:[/bold] {res['member_name']} ([dim]{res['member_id']}[/dim])\n"
        f"[bold]Sentido:[/bold] [{color}]{res['choice']}[/{color}]"
    )
    console.print(Panel(body, title="Voto", border_style="cyan"), highlight=False)


@click.command("escrutinio")
@click.argument("propuesta_id", type=int)
@click.option("--padron", "-p", default=None, type=click.IntRange(min=1),
              help="Socios activos; por omisión se cuenta el padrón registrado.")
def cmd_escrutinio(propuesta_id: int, padron: int | None) -> None:
    """Contar los votos, cerrar la propuesta y emitir el acta."""
    perfil = _perfil_con_asamblea()
    try:
        tally = voting.tally_votes(propuesta_id, total_census_members=padron, mayoria=perfil.governance.mayoria)
    except ValueError as exc:
        fallar(str(exc), "Error en escrutinio")
    if tally.get("ya_cerrada"):
        console.print("[yellow]La propuesta ya estaba cerrada; se muestra el acta guardada.[/yellow]")
    console.print(Markdown(tally["acta_md"]))


COMANDOS = (socios, cmd_propuesta, cmd_propuestas, cmd_votar, cmd_escrutinio)
