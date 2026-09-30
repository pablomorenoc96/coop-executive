"""Comandos de análisis: fecha y plazos, comparación de evaluaciones, consulta y revisión de fuentes."""
from __future__ import annotations

import re
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from coopexecutive import knowledge
from coopexecutive.cli import _modelo
from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings
from coopexecutive.documents import cartas
from coopexecutive.documents.generador import DECISIONES
from coopexecutive.grant_tools import comparar
from coopexecutive.guardrails.sensibles import limpiar_datos_sensibles
from coopexecutive.lectura import ErrorLectura, leer_archivo, leer_url
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import fecha_larga, hoy_local
from coopexecutive.utils.plazos import DIAS_SEMANA, plazo

# Texto máximo de una fuente que se envía al modelo en `revisar`.
MAX_FUENTE = 24_000


# --- fecha -------------------------------------------------------------------------

@click.command("fecha")
@click.option("--cierre", "cierres", multiple=True,
              help="Fecha de cierre (repetible): AAAA-MM-DD, DD/MM/AAAA o «30 de octubre de 2026».")
def fecha(cierres: tuple[str, ...]) -> None:
    """Fecha de hoy en la zona configurada y días naturales que faltan a cada cierre."""
    settings = get_settings()
    hoy = hoy_local(settings.user_timezone)
    console.print(
        f"Hoy es [bold]{DIAS_SEMANA[hoy.weekday()]} {fecha_larga(hoy)}[/bold] "
        f"(zona horaria {settings.user_timezone}).",
        highlight=False,
    )
    if not cierres:
        return
    tabla = Table(header_style="bold cyan")
    tabla.add_column("Cierre")
    tabla.add_column("Plazo")
    for texto in cierres:
        try:
            p = plazo(texto, hoy)
        except ValueError as exc:
            fallar(str(exc), "Fecha no válida")
        estilo = "dim" if p.vencida else ("bold red" if p.urgente else "")
        tabla.add_row(p.fecha_larga, p.texto, style=estilo)
    console.print(tabla)
    console.print("[dim]Días naturales. Confirme en las bases si el cierre tiene hora o zona horaria distinta.[/dim]")


# --- comparar-convocatorias ------------------------------------------------------------

@click.command("comparar-convocatorias")
@click.argument("ids", nargs=-1, type=int)
@click.option("--expediente", "folios", multiple=True, help="Usa la evaluación más reciente del expediente (repetible).")
@click.option("--orden", type=click.Choice(["plazo", "puntaje"]), default="plazo", show_default=True,
              help="Orden de la tabla. La prioridad no cambia con el orden.")
@click.option("--word", is_flag=True, help="Guardar también el reporte de evaluación en Word.")
@click.option("--si", "aceptar", is_flag=True, help="Con --word, guardar sin pedir confirmación.")
def comparar_convocatorias(ids: tuple[int, ...], folios: tuple[str, ...], orden: str, word: bool,
                           aceptar: bool) -> None:
    """Compara evaluaciones guardadas y dice cuál atender primero.

    Sin argumentos toma las diez evaluaciones más recientes.
    """
    hoy = hoy_local(get_settings().user_timezone)
    try:
        elegidos = list(ids) + comparar.ultimas_por_expediente(list(folios))
        resultado = comparar.comparar(comparar.cargar_varias(elegidos or comparar.recientes()), hoy, orden)
    except ValueError as exc:
        fallar(str(exc))

    tabla = Table(title=f"Comparación ({len(resultado.filas)} evaluaciones, orden por {orden})",
                  header_style="bold cyan")
    for columna in ("Id", "Oportunidad", "Financiador", "Decisión", "Puntaje", "Plazo"):
        tabla.add_column(columna)
    for f in resultado.filas:
        r = f.resultado
        tabla.add_row(
            str(f.id), r.convocatoria, r.financiador or "-", DECISIONES.get(r.decision, r.decision),
            f"{r.puntaje}/{r.puntaje_maximo_evaluado}", f.plazo,
            style="dim" if f.descartada else ("bold" if f is resultado.prioridad else ""),
        )
    console.print(tabla)
    if resultado.prioridad is None:
        console.print(Panel(resultado.motivo, title="Qué atender primero", border_style="yellow"))
    else:
        r = resultado.prioridad.resultado
        console.print(Panel(
            f"[bold]#{resultado.prioridad.id} {r.convocatoria}[/bold]\n{resultado.motivo}\n\n"
            f"Siguiente paso: {r.siguiente_paso}",
            title="Qué atender primero", border_style="green",
        ))
    if word:
        from coopexecutive.cli.documentos import _escribir, _perfil

        perfil, carpeta = _perfil()
        _escribir(cartas.reporte_evaluacion(perfil, resultado, hoy), perfil, carpeta, aceptar)


# --- consultar ---------------------------------------------------------------------

def _pasajes_en_texto(pasajes: list[knowledge.Pasaje]) -> str:
    return "\n\n".join(
        f"[{i}] Fuente: {p.fuente}{' · ' + p.titulo if p.titulo else ''}\n{p.texto}"
        for i, p in enumerate(pasajes, 1)
    )


@click.command("consultar")
@click.argument("pregunta")
@click.option("--redactar", is_flag=True,
              help="Pedir al modelo una respuesta redactada solo con los pasajes encontrados.")
@click.option("--limite", type=click.IntRange(1, 10), default=4, show_default=True, help="Pasajes a mostrar.")
def consultar(pregunta: str, redactar: bool, limite: int) -> None:
    """Busca en el perfil, en la carpeta conocimiento/ y en las guías incluidas. Cita la fuente.

    Sin --redactar no usa el modelo ni la red: muestra los pasajes tal como están.
    """
    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    carpeta = settings.company_profile_path.parent / knowledge.CARPETA_ESPACIO
    pasajes = knowledge.buscar(pregunta, knowledge.documentos(carpeta, perfil.to_prompt_block()), limite)
    if not pasajes:
        console.print(Panel(knowledge.NO_CONSTA, title="Consulta", border_style="yellow"))
        return
    if not redactar:
        for p in pasajes:
            titulo = p.fuente + (f" · {p.titulo}" if p.titulo else "")
            console.print(Panel(p.texto, title=titulo, subtitle=f"pertinencia {p.puntaje}",
                                border_style="cyan", title_align="left"))
        return
    contexto = _pasajes_en_texto(pasajes)
    pedido = (
        "Responde la pregunta usando SOLO los pasajes numerados de abajo. Después de cada dato indica "
        "entre corchetes el número del pasaje, por ejemplo [2]. Si los pasajes no responden la pregunta, "
        f"responde exactamente: «{knowledge.NO_CONSTA}». Máximo 200 palabras.\n\n"
        f"Pregunta: {pregunta}\n\nPasajes:\n{contexto}"
    )
    texto, bloque = _modelo.ejecutar(_modelo.consultar(pedido, None))
    _modelo.mostrar_revisada(texto, f"{pregunta}\n{contexto}\n{bloque}", "Respuesta",
                             hoy_local(settings.user_timezone), leyenda=False)
    console.print("[dim]Fuentes: " + "; ".join(f"[{i}] {p.fuente}" for i, p in enumerate(pasajes, 1)) + "[/dim]",
                  highlight=False)


# --- revisar ---------------------------------------------------------------------------

def leer_fuente(origen: str) -> str:
    """Texto de una URL (página o PDF) o de un archivo local, ya sin datos sensibles."""
    limpio = origen.strip()
    try:
        if re.match(r"^https?://", limpio, re.IGNORECASE):
            texto = leer_url(limpio)
        elif Path(limpio).is_file():
            texto = leer_archivo(Path(limpio))
        else:
            fallar(f"«{origen}» no es una dirección http(s) ni un archivo existente.")
    except ErrorLectura as exc:
        fallar(str(exc), "No se pudo leer la fuente")
    texto = limpiar_datos_sensibles(texto).strip()
    if not texto:
        fallar("La fuente no tiene texto legible (¿es un PDF escaneado?).")
    return texto


@click.command("revisar")
@click.argument("origen")
@click.option("--pregunta", default=None, help="Pregunta concreta sobre la fuente.")
@click.option("--sin-modelo", is_flag=True,
              help="Sin modelo: muestra los fragmentos de la fuente más pertinentes a la pregunta.")
def revisar(origen: str, pregunta: str | None, sin_modelo: bool) -> None:
    """Resume una página web o un archivo (PDF, Word, HTML o texto), citando la fuente."""
    texto = leer_fuente(origen)
    if sin_modelo:
        if not pregunta:
            fallar("Con --sin-modelo indique --pregunta.")
        pasajes = knowledge.buscar(pregunta, knowledge.partir(texto, origen), limite=4)
        if not pasajes:
            console.print(Panel("La fuente no menciona nada relacionado con la pregunta.", border_style="yellow"))
            return
        for p in pasajes:
            console.print(Panel(p.texto, title=p.titulo or origen, border_style="cyan", title_align="left"))
        return

    recorte = texto[:MAX_FUENTE]
    tarea = (
        f"Responde esta pregunta sobre la fuente: {pregunta}" if pregunta
        else "Resume la fuente en un máximo de 250 palabras: de qué trata, a quién va dirigida, "
             "requisitos, montos y fechas si los menciona, y qué falta por confirmar."
    )
    pedido = (
        f"{tarea}\n\nReglas: usa solo el texto de la fuente; si algo no aparece, di que la fuente no lo "
        "indica. Cita entre comillas los fragmentos que respaldan montos, fechas y requisitos. "
        "No inventes nada.\n\n"
        f"Fuente: {origen}\n\n{recorte}"
    )
    respuesta, bloque = _modelo.ejecutar(_modelo.consultar(pedido, "procurador"))
    hoy = hoy_local(get_settings().user_timezone)
    _modelo.mostrar_revisada(respuesta, f"{pregunta or ''}\n{recorte}\n{bloque}", f"Fuente: {origen}", hoy,
                             leyenda=False)
    if len(texto) > MAX_FUENTE:
        console.print(f"[yellow]Solo se revisaron los primeros {MAX_FUENTE:,} caracteres de "
                      f"{len(texto):,}.[/yellow]")


COMANDOS = (fecha, comparar_convocatorias, consultar, revisar)
