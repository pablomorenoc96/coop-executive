"""Consola compartida y utilidades de salida para los comandos de la CLI."""
from __future__ import annotations

from datetime import date, datetime
from typing import NoReturn

import click
from rich.console import Console
from rich.panel import Panel

console = Console(legacy_windows=False)

FECHA = click.DateTime(formats=["%Y-%m-%d"])


def fallar(mensaje: str, titulo: str = "Error") -> NoReturn:
    """Muestra el error en un panel rojo y termina con código 1."""
    console.print(Panel(f"[bold red]{mensaje}[/bold red]", title=titulo, border_style="red"))
    raise click.exceptions.Exit(1)


def como_fecha(valor: datetime | None) -> date | None:
    return valor.date() if valor is not None else None


def texto_fecha(valor: date | None) -> str:
    return valor.isoformat() if valor is not None else "-"
