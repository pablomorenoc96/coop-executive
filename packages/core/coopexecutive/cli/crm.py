"""Comandos de seguimiento: financiadores y expedientes."""
from __future__ import annotations

from datetime import datetime

import click
from rich.panel import Panel
from rich.table import Table

from coopexecutive.cli._consola import FECHA, como_fecha, console, fallar, texto_fecha
from coopexecutive.crm import cases, funders
from coopexecutive.crm.cases import Expediente
from coopexecutive.crm.funders import Financiador
from coopexecutive.guardrails.marcadores import ORIGENES
from coopexecutive.utils.fechas import local_desde_utc


def _momento(texto: str) -> str:
    return local_desde_utc(texto).strftime("%Y-%m-%d %H:%M") if texto else "-"


# --- financiadores ------------------------------------------------------------


@click.group("financiadores")
def financiadores() -> None:
    """Base de financiadores: donantes, fundaciones, gobierno, agencias y financieras."""


def _panel_financiador(f: Financiador, titulo: str) -> Panel:
    cuerpo = (
        f"[bold]Folio:[/bold] {f.folio}\n"
        f"[bold]Organización:[/bold] {f.organizacion}\n"
        f"[bold]Proyecto:[/bold] {f.proyecto}\n"
        f"[bold]Tipo:[/bold] {f.tipo} | [bold]Canal:[/bold] {f.canal}\n"
        f"[bold]Contacto:[/bold] {f.contacto or '-'}\n"
        f"[bold]Estatus:[/bold] {f.estatus}\n"
        f"[bold]Solicitado:[/bold] {f.monto(f.monto_solicitado)}\n"
        f"[bold]Comprometido:[/bold] {f.monto(f.monto_comprometido)}\n"
        f"[bold]Recibido:[/bold] {f.monto(f.monto_recibido)}\n"
        f"[bold]Seguimiento:[/bold] {texto_fecha(f.seguimiento)}\n"
        f"[bold]Notas:[/bold] {f.notas or '-'}\n"
        f"[dim]Actualizado: {_momento(f.actualizado_en)}[/dim]"
    )
    return Panel(cuerpo, title=titulo, border_style="cyan")


@financiadores.command("registrar")
@click.argument("organizacion")
@click.option("--proyecto", required=True, help="Iniciativa que interesa al financiador (sin montos ni fechas).")
@click.option("--tipo", required=True, help=f"Uno de: {', '.join(funders.TIPOS)}.")
@click.option("--canal", required=True, help=f"Uno de: {', '.join(funders.CANALES)}.")
@click.option("--moneda", default="MXN", show_default=True, help="Código ISO 4217.")
@click.option("--monto-solicitado", type=float, default=None, help="Monto solicitado, sin conversión.")
@click.option("--contacto", default="", help="Área o cargo de contacto.")
@click.option("--seguimiento", type=FECHA, default=None, help="Fecha del siguiente seguimiento (AAAA-MM-DD).")
@click.option("--notas", default="")
def financiadores_registrar(
    organizacion: str,
    proyecto: str,
    tipo: str,
    canal: str,
    moneda: str,
    monto_solicitado: float | None,
    contacto: str,
    seguimiento: datetime | None,
    notas: str,
) -> None:
    """Registrar un financiador nuevo."""
    try:
        f = funders.registrar(
            organizacion, proyecto, tipo, canal, moneda=moneda, monto_solicitado=monto_solicitado,
            contacto=contacto, seguimiento=como_fecha(seguimiento), notas=notas,
        )
    except ValueError as exc:
        fallar(str(exc))
    console.print(_panel_financiador(f, "Financiador registrado"))


@financiadores.command("buscar")
@click.argument("texto", required=False, default="")
@click.option("--limite", type=int, default=20, show_default=True)
def financiadores_buscar(texto: str, limite: int) -> None:
    """Buscar por folio o texto parcial. Sin texto, muestra los más recientes."""
    encontrados = funders.buscar(texto, limite)
    if not encontrados:
        console.print("[dim]No hay financiadores que coincidan.[/dim]")
        return
    tabla = Table(title="Financiadores", header_style="bold cyan")
    for columna in ("Folio", "Organización", "Tipo", "Estatus", "Solicitado", "Seguimiento"):
        tabla.add_column(columna)
    for f in encontrados:
        tabla.add_row(f.folio, f.organizacion, f.tipo, f.estatus, f.monto(f.monto_solicitado),
                      texto_fecha(f.seguimiento))
    console.print(tabla)


@financiadores.command("ver")
@click.argument("folio")
def financiadores_ver(folio: str) -> None:
    """Mostrar un financiador."""
    f = funders.ver(folio)
    if f is None:
        fallar(f"No existe el financiador {folio}.")
    console.print(_panel_financiador(f, f.organizacion))


@financiadores.command("actualizar")
@click.argument("folio")
@click.option("--estatus", default=None, help=f"Uno de: {', '.join(funders.ESTATUS)}.")
@click.option("--canal", default=None)
@click.option("--contacto", default=None)
@click.option("--proyecto", default=None)
@click.option("--moneda", default=None)
@click.option("--monto-solicitado", type=float, default=None)
@click.option("--monto-comprometido", type=float, default=None)
@click.option("--monto-recibido", type=float, default=None)
@click.option("--seguimiento", type=FECHA, default=None)
@click.option("--notas", default=None)
def financiadores_actualizar(folio: str, seguimiento: datetime | None, **cambios: object) -> None:
    """Actualizar estatus, montos, contacto o seguimiento de un financiador."""
    cambios = {k: v for k, v in cambios.items() if v is not None}
    if not cambios and seguimiento is None:
        fallar("Indique al menos un dato por actualizar.")
    try:
        f = funders.actualizar(folio, seguimiento=como_fecha(seguimiento), **cambios)  # type: ignore[arg-type]
    except ValueError as exc:
        fallar(str(exc))
    console.print(_panel_financiador(f, "Financiador actualizado"))


# --- expedientes --------------------------------------------------------------


@click.group("expedientes")
def expedientes() -> None:
    """Expedientes de procuración: una oportunidad o relación con su historial de avances."""


def _panel_expediente(e: Expediente, titulo: str) -> Panel:
    cuerpo = (
        f"[bold]Folio:[/bold] {e.folio}\n"
        f"[bold]Título:[/bold] {e.titulo}\n"
        f"[bold]Objetivo:[/bold] {e.objetivo or '-'}\n"
        f"[bold]Responsable:[/bold] {e.responsable or '-'}\n"
        f"[bold]Fecha límite:[/bold] {texto_fecha(e.fecha_limite)}\n"
        f"[bold]Monto:[/bold] {e.monto_texto}\n"
        f"[bold]Estado:[/bold] {'abierto' if e.abierto else 'cerrado'}"
    )
    return Panel(cuerpo, title=titulo, border_style="cyan")


@expedientes.command("abrir")
@click.argument("entidad")
@click.option("--tipo", required=True, help=f"Uno de: {', '.join(cases.TIPOS)}.")
@click.option("--objetivo", default="")
@click.option("--responsable", default="")
@click.option("--fecha-limite", type=FECHA, default=None, help="AAAA-MM-DD")
@click.option("--monto", type=float, default=None, help="Sin monto se muestra MONTO POR DEFINIR.")
@click.option("--moneda", default="MXN", show_default=True)
def expedientes_abrir(
    entidad: str,
    tipo: str,
    objetivo: str,
    responsable: str,
    fecha_limite: datetime | None,
    monto: float | None,
    moneda: str,
) -> None:
    """Abrir un expediente (uno abierto por entidad y tipo)."""
    try:
        e = cases.abrir(tipo, entidad, objetivo=objetivo, responsable=responsable,
                        fecha_limite=como_fecha(fecha_limite), monto=monto, moneda=moneda)
    except ValueError as exc:
        fallar(str(exc))
    console.print(_panel_expediente(e, "Expediente abierto"))


@expedientes.command("avance")
@click.argument("folio")
@click.option("--estado", required=True, help="Situación actual en una frase.")
@click.option("--pendientes", default="")
@click.option("--siguiente", "siguiente_accion", default="", help="Siguiente acción y quién la ejecuta.")
@click.option("--origen", default=ORIGENES[0], show_default=True, help=f"Uno de: {', '.join(ORIGENES)}.")
@click.option("--cerrar", is_flag=True, help="Cerrar el expediente con este avance.")
def expedientes_avance(folio: str, estado: str, pendientes: str, siguiente_accion: str, origen: str,
                       cerrar: bool) -> None:
    """Registrar un avance en un expediente."""
    try:
        a = cases.registrar_avance(folio, estado, pendientes=pendientes, siguiente_accion=siguiente_accion,
                                   origen=origen, cerrar=cerrar)
    except ValueError as exc:
        fallar(str(exc))
    cierre = "\n[bold]El expediente quedó cerrado.[/bold]" if cerrar else ""
    console.print(f"[green]Avance registrado en {folio.upper()}[/green] ({a.origen}): {a.estado}{cierre}")


@expedientes.command("ver")
@click.argument("folio")
def expedientes_ver(folio: str) -> None:
    """Mostrar un expediente con sus avances y evaluaciones."""
    e = cases.obtener(folio)
    if e is None:
        fallar(f"No existe el expediente {folio}.")
    console.print(_panel_expediente(e, e.titulo))
    historial = cases.avances(e.folio)
    if historial:
        tabla = Table(title="Avances", header_style="bold cyan")
        for columna in ("Fecha", "Estado", "Pendientes", "Siguiente acción", "Origen"):
            tabla.add_column(columna)
        for a in historial:
            tabla.add_row(_momento(a.registrado_en), a.estado, a.pendientes or "-", a.siguiente_accion or "-",
                          a.origen)
        console.print(tabla)
    else:
        console.print("[dim]Sin avances registrados.[/dim]")
    vinculadas = cases.evaluaciones(e.folio)
    if vinculadas:
        tabla = Table(title="Evaluaciones", header_style="bold cyan")
        for columna in ("Id", "Decisión", "Puntaje", "Fecha", "Huella"):
            tabla.add_column(columna)
        for v in vinculadas:
            tabla.add_row(str(v.id), v.decision, f"{v.puntaje:g}", _momento(v.evaluado_en), (v.hash or "-")[:12])
        console.print(tabla)


@expedientes.command("listar")
@click.option("--responsable", default=None)
@click.option("--estado", default="abiertos", show_default=True, help="abiertos, cerrados o todos.")
def expedientes_listar(responsable: str | None, estado: str) -> None:
    """Listar expedientes, con filtro por responsable."""
    try:
        encontrados = cases.listar(responsable, estado)
    except ValueError as exc:
        fallar(str(exc))
    if not encontrados:
        console.print("[dim]No hay expedientes que coincidan.[/dim]")
        return
    tabla = Table(title="Expedientes", header_style="bold cyan")
    for columna in ("Folio", "Título", "Responsable", "Fecha límite", "Monto", "Estado"):
        tabla.add_column(columna)
    for e in encontrados:
        tabla.add_row(e.folio, e.titulo, e.responsable or "-", texto_fecha(e.fecha_limite), e.monto_texto,
                      "abierto" if e.abierto else "cerrado")
    console.print(tabla)


COMANDOS = (financiadores, expedientes)
