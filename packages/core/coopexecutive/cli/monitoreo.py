"""Comando para monitorear convocatorias abiertas."""
from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from coopexecutive import monitoring
from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import hoy_local

MAX_POR_REVISAR = 10


def _tabla(titulo: str, avisos: list[monitoring.Aviso], estilo: str, numerar: bool = False) -> Table:
    tabla = Table(title=titulo, title_style=f"bold {estilo}", show_lines=True, expand=True)
    if numerar:
        tabla.add_column("#", justify="right", no_wrap=True)
    tabla.add_column("Convocatoria", ratio=5)
    tabla.add_column("Fuente", ratio=2)
    tabla.add_column("Plazo", ratio=2)
    tabla.add_column("Coincide con", ratio=2)
    for n, aviso in enumerate(avisos, 1):
        convocatoria = f"[bold]{aviso.titulo}[/bold]"
        if aviso.enlace:
            convocatoria += f"\n[dim]{aviso.enlace}[/dim]"
        coincide = ", ".join(aviso.temas) if aviso.temas else ", ".join(aviso.coincidencias)
        plazo = aviso.plazo if aviso.vigencia_verificada else f"[yellow]{aviso.plazo}[/yellow]"
        fila = [convocatoria, aviso.fuente, plazo, coincide]
        tabla.add_row(*([str(n)] if numerar else []), *fila)
    return tabla


@click.command("monitorear")
@click.option("--tema", "temas", multiple=True,
              help="Tema a buscar (repetible). Sustituye a los ejes de trabajo del perfil.")
@click.option("--sin-cache", is_flag=True, help="Descarga todo de nuevo aunque haya una copia reciente.")
@click.option("--todas", is_flag=True, help=f"Muestra todas las convocatorias por revisar (no solo {MAX_POR_REVISAR}).")
def monitorear(temas: tuple[str, ...], sin_cache: bool, todas: bool) -> None:
    """Busca convocatorias abiertas que coincidan con los temas de la organización.

    Lee los canales públicos de las fuentes incluidas y de fuentes.yaml del espacio.
    A la web no sale ningún dato de la organización.
    """
    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    elegidos = list(temas) or perfil.focus_areas
    hoy = hoy_local(settings.user_timezone)
    with console.status("Consultando fuentes..."):
        try:
            reporte = monitoring.monitorear(
                elegidos, hoy, settings.carpeta_base,
                cache=settings.cache_dir / "monitoreo", usar_cache=not sin_cache,
            )
        except ValueError as exc:
            fallar(str(exc), "Monitoreo")

    console.print(Panel(
        f"[bold]Temas:[/bold] {', '.join(reporte.temas)}\n"
        f"[bold]Fuentes consultadas:[/bold] {', '.join(reporte.consultadas) or 'ninguna'}\n"
        f"[dim]{reporte.leidos} avisos leídos; {reporte.antiguos} descartados por tener más de "
        f"{monitoring.ANTIGUEDAD_MAXIMA_DIAS} días de publicados.[/dim]",
        title=f"Monitoreo de convocatorias - {hoy.isoformat()}",
        border_style="cyan",
    ))

    if reporte.priorizadas:
        console.print(_tabla("Priorizadas", reporte.priorizadas, "green", numerar=True))
    else:
        console.print("[yellow]Ningún aviso coincide con los temas en las fuentes consultadas.[/yellow]")
    if reporte.por_revisar:
        visibles = reporte.por_revisar if todas else reporte.por_revisar[:MAX_POR_REVISAR]
        console.print(_tabla("Por revisar", visibles, "cyan"))
        ocultas = len(reporte.por_revisar) - len(visibles)
        if ocultas:
            console.print(f"[dim]... y {ocultas} más. Use --todas para verlas.[/dim]")
    if reporte.cerradas:
        console.print(_tabla("Cerradas", reporte.cerradas, "red"))

    if reporte.manuales:
        console.print("\n[bold]Revisión manual[/bold] (fuentes sin canal RSS):")
        for fuente in reporte.manuales:
            console.print(f"  - {fuente.nombre}: {fuente.url}")
    for nombre, motivo in reporte.fallidas:
        console.print(f"[yellow]No se pudo consultar {nombre}: {motivo}.[/yellow]")
    for nota in reporte.notas:
        console.print(f"[dim]{nota}[/dim]")

    console.print(
        "\n[dim]Confirme bases y fecha de cierre en el sitio oficial antes de evaluar. "
        "Para evaluar una convocatoria: coopexecutive evaluar-convocatoria.[/dim]"
    )


COMANDOS = (monitorear,)
