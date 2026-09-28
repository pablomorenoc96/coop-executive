"""Comandos para generar documentos Word con el membrete de la organización."""
from __future__ import annotations

from pathlib import Path

import click
import yaml
from pydantic import ValidationError
from rich.markdown import Markdown
from rich.panel import Panel

from coopexecutive import documents
from coopexecutive.cli._consola import console, fallar
from coopexecutive.config import get_settings
from coopexecutive.crm import cases
from coopexecutive.crm.cases import Expediente
from coopexecutive.documents import generador
from coopexecutive.documents.contenido import DocumentoPlano
from coopexecutive.grant_tools import matrix
from coopexecutive.memory.company_profile import CoopProfile, Membrete
from coopexecutive.utils.fechas import hoy_local


@click.group("documento")
def documento() -> None:
    """Generar la solicitud, el documento institucional o la ficha de una oportunidad en Word."""


def _perfil() -> tuple[CoopProfile, Path]:
    ruta = get_settings().company_profile_path
    return CoopProfile.load_from_yaml(ruta), ruta.parent


def _expediente(folio: str) -> Expediente:
    e = cases.obtener(folio)
    if e is None:
        fallar(f"No existe el expediente {folio}.")
    return e


def _escribir(
    plano: DocumentoPlano,
    perfil: CoopProfile,
    carpeta_perfil: Path,
    aceptar: bool,
    *,
    expediente_folio: str | None = None,
    evaluacion_id: int | None = None,
) -> None:
    """Muestra la vista previa, pide confirmación y guarda el Word."""
    console.print(Panel(Markdown(documents.a_markdown(plano)), title="Vista previa", border_style="cyan"))
    faltantes = plano.pendientes()
    if faltantes:
        console.print(Panel(
            "\n".join(f"- {m}" for m in faltantes)
            + "\n\n[dim]Complete estos datos en el perfil, el expediente o el archivo de contenido.[/dim]",
            title=f"Datos pendientes ({len(faltantes)})",
            border_style="yellow",
        ))
    if not aceptar and not click.confirm("¿Generar el documento Word?", default=True):
        console.print("[dim]No se generó ningún archivo.[/dim]")
        return
    settings = get_settings()
    membrete = perfil.procuracion.membrete if perfil.procuracion else Membrete()
    try:
        guardado = documents.guardar(
            plano, membrete, carpeta_perfil, settings.salidas_dir, hoy_local(settings.user_timezone),
            autor=perfil.name, expediente_folio=expediente_folio, evaluacion_id=evaluacion_id,
        )
    except (OSError, ValueError) as exc:
        fallar(str(exc), "No se generó el documento")
    vinculo = f"\nRegistrado en el expediente {expediente_folio}." if expediente_folio else ""
    console.print(
        f"[bold green]Documento guardado[/bold green] en {guardado.ruta}\n"
        f"[dim]Huella SHA-256: {guardado.sha256}[/dim]{vinculo}"
    )


@documento.command("solicitud")
@click.option("--expediente", "folio", required=True, help="Folio EXP-AAAA-NNNN de la oportunidad.")
@click.option("--contenido", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
              help="YAML con proyecto, justificación, objetivos, actividades, resultados, presupuesto y contacto.")
@click.option("--si", "aceptar", is_flag=True, help="Guardar sin pedir confirmación.")
def documento_solicitud(folio: str, contenido: Path | None, aceptar: bool) -> None:
    """Solicitud dirigida a quien otorga el recurso. Lo que falte queda marcado."""
    perfil, carpeta = _perfil()
    e = _expediente(folio)
    datos = None
    if contenido is not None:
        try:
            crudo = yaml.safe_load(contenido.read_text(encoding="utf-8")) or {}
            datos = generador.ContenidoSolicitud.model_validate(crudo)
        except (yaml.YAMLError, ValidationError, ValueError) as exc:
            fallar(f"{contenido.name} no es válido: {exc}", "Contenido no válido")
    plano = generador.solicitud(perfil, e, datos, hoy_local(get_settings().user_timezone))
    _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio)


@documento.command("institucional")
@click.option("--expediente", "folio", default=None, help="Folio al que se vincula el documento (opcional).")
@click.option("--si", "aceptar", is_flag=True, help="Guardar sin pedir confirmación.")
def documento_institucional(folio: str | None, aceptar: bool) -> None:
    """Presentación de la organización a partir del perfil."""
    perfil, carpeta = _perfil()
    e = _expediente(folio) if folio else None
    plano = generador.documento_institucional(perfil, hoy_local(get_settings().user_timezone))
    _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None)


@documento.command("ficha")
@click.option("--expediente", "folio", default=None, help="Usa la evaluación más reciente del expediente.")
@click.option("--evaluacion", "id_evaluacion", type=int, default=None, help="Id de una evaluación guardada.")
@click.option("--si", "aceptar", is_flag=True, help="Guardar sin pedir confirmación.")
def documento_ficha(folio: str | None, id_evaluacion: int | None, aceptar: bool) -> None:
    """Ficha interna de una oportunidad evaluada: decisión, puntaje con evidencia y siguiente paso."""
    if folio is None and id_evaluacion is None:
        fallar("Indique --expediente o --evaluacion.")
    perfil, carpeta = _perfil()
    e = _expediente(folio) if folio else None
    if id_evaluacion is None:
        vinculadas = cases.evaluaciones(e.folio)  # type: ignore[union-attr]
        if not vinculadas:
            fallar(f"El expediente {e.folio} no tiene evaluaciones.")  # type: ignore[union-attr]
        id_evaluacion = vinculadas[-1].id
    try:
        guardada = matrix.cargar(id_evaluacion)
    except ValueError as exc:
        fallar(str(exc))
    if e is None and guardada.expediente_folio:
        e = cases.obtener(guardada.expediente_folio)
    plano = generador.ficha_oportunidad(perfil, guardada.resultado, e)
    _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None,
              evaluacion_id=guardada.id)


COMANDOS = (documento,)
