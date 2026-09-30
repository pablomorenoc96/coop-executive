"""Bitácora desde la línea de comandos: registro automático de cada comando y consulta."""
from __future__ import annotations

from pathlib import Path

import click
from rich.markup import escape
from rich.table import Table

from coopexecutive import bitacora as _bitacora
from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings
from coopexecutive.utils.fechas import hoy_local

# Comandos que solo muestran información: no se registran para no llenar la bitácora de ruido.
SIN_REGISTRO = frozenset({"bitacora", "info", "intro", "modelos", "fecha", "panel", "dashboard", "mcp",
                          "servidor-mcp"})


def _ruta(ctx: click.Context) -> str:
    return " ".join(ctx.command_path.split()[1:]) or ctx.info_name or ""


def _envolver(comando: click.Command) -> None:
    original = comando.invoke

    def invoke(ctx: click.Context):
        ruta = _ruta(ctx)
        if ruta.split(" ", 1)[0] in SIN_REGISTRO:
            return original(ctx)
        estado = "error"
        try:
            resultado = original(ctx)
            estado = "ok"
            return resultado
        except click.exceptions.Exit as exc:
            estado = "error" if exc.exit_code else "ok"
            raise
        finally:
            _bitacora.registrar_sin_fallar("cli", ruta, dict(ctx.params), estado=estado)

    invoke.__auditado__ = True  # type: ignore[attr-defined]
    comando.invoke = invoke  # type: ignore[method-assign]


def auditar(grupo: click.Group) -> None:
    """Envuelve cada comando final del árbol. Un comando con alias se envuelve una sola vez."""
    pendientes: list[click.Command] = [grupo]
    while pendientes:
        comando = pendientes.pop()
        if isinstance(comando, click.Group):
            pendientes.extend(comando.commands.values())
        elif not getattr(comando.invoke, "__auditado__", False):
            _envolver(comando)


@click.group("bitacora")
def bitacora() -> None:
    """Bitácora de acciones con huellas encadenadas: ver, verificar y exportar."""


@bitacora.command("ver")
@click.option("--limite", default=30, show_default=True, type=click.IntRange(1, 1000))
@click.option("--canal", type=click.Choice(_bitacora.CANALES), default=None, help="Solo un canal.")
def ver(limite: int, canal: str | None) -> None:
    """Mostrar los registros más recientes."""
    registros = _bitacora.ver(limite, canal)
    if not registros:
        console.print("[yellow]La bitácora está vacía.[/yellow]")
        return
    tabla = Table(title="Bitácora", header_style="bold cyan")
    for columna in ("Id", "Fecha (UTC)", "Canal", "Acción", "Estado", "Resultado"):
        tabla.add_column(columna)
    for r in registros:
        color = {"ok": "green", "denegada": "yellow"}.get(r.estado, "red")
        tabla.add_row(str(r.id), r.registrado_en, r.canal, escape(r.accion), f"[{color}]{r.estado}[/{color}]",
                      escape(r.resultado))
    console.print(tabla)


@bitacora.command("verificar")
def verificar() -> None:
    """Recalcular la cadena de huellas; sale con código 1 si alguien editó o borró un registro."""
    v = _bitacora.verificar()
    if v.integra:
        console.print(f"[green]Bitácora íntegra:[/green] {v.total} registro(s).", highlight=False)
        return
    fallar(f"El registro {v.roto_en} {v.motivo}. Revisados: {v.total}.", "Bitácora alterada")


@bitacora.command("exportar")
@click.argument("destino", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--jsonl", is_flag=True, default=True, hidden=True)
def exportar(destino: Path | None, jsonl: bool) -> None:
    """Guardar todos los registros en JSON Lines (una línea por registro). Nunca sobrescribe."""
    settings = get_settings()
    destino = destino or settings.salidas_dir / f"bitacora-{hoy_local(settings.user_timezone).isoformat()}.jsonl"
    try:
        total = _bitacora.exportar_jsonl(destino)
    except FileExistsError:
        fallar(f"Ya existe {destino}; elija otro nombre.", "No se exportó")
    console.print(f"[green]{total} registro(s) exportado(s) a[/green] {destino}", highlight=False)


COMANDOS = (bitacora,)
