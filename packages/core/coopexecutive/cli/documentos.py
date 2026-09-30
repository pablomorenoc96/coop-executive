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
from coopexecutive.documents import cartas, generador
from coopexecutive.documents.contenido import DocumentoPlano
from coopexecutive.grant_tools import comparar, matrix
from coopexecutive.memory.company_profile import CoopProfile, Membrete
from coopexecutive.utils.fechas import hoy_local


@click.group("documento")
def documento() -> None:
    """Generar documentos Word: solicitud, carta, nota conceptual, ficha, reportes e institucional."""


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


def _contenido(ruta: Path | None, modelo):
    if ruta is None:
        return None
    try:
        crudo = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        return modelo.model_validate(crudo)
    except (yaml.YAMLError, ValidationError, ValueError) as exc:
        fallar(f"{ruta.name} no es válido: {exc}", "Contenido no válido")


_CONTENIDO = click.option("--contenido", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
                          help="YAML con el contenido; lo que falte queda marcado.")
_SI = click.option("--si", "aceptar", is_flag=True, help="Guardar sin pedir confirmación.")


@documento.command("carta-intencion")
@click.option("--expediente", "folio", default=None, help="Folio EXP-AAAA-NNNN: toma destinatario, proyecto y monto.")
@_CONTENIDO
@_SI
def documento_carta(folio: str | None, contenido: Path | None, aceptar: bool) -> None:
    """Carta de intención para el financiador. Firmante y monto quedan marcados si faltan."""
    perfil, carpeta = _perfil()
    e = _expediente(folio) if folio else None
    plano = cartas.carta_intencion(perfil, e, _contenido(contenido, cartas.ContenidoCarta),
                                   hoy_local(get_settings().user_timezone))
    _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None)


@documento.command("nota-conceptual")
@click.option("--expediente", "folio", default=None, help="Folio EXP-AAAA-NNNN de la oportunidad.")
@_CONTENIDO
@_SI
def documento_nota(folio: str | None, contenido: Path | None, aceptar: bool) -> None:
    """Nota conceptual breve (acepta el mismo YAML que la solicitud)."""
    perfil, carpeta = _perfil()
    e = _expediente(folio) if folio else None
    plano = cartas.nota_conceptual(perfil, e, _contenido(contenido, generador.ContenidoSolicitud),
                                   hoy_local(get_settings().user_timezone))
    _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None)


@documento.command("reporte-monitoreo")
@click.option("--tema", "temas", multiple=True, help="Tema a buscar (repetible); por omisión, los ejes del perfil.")
@click.option("--sin-cache", is_flag=True, help="Descarga todo de nuevo aunque haya una copia reciente.")
@_SI
def documento_monitoreo(temas: tuple[str, ...], sin_cache: bool, aceptar: bool) -> None:
    """Corre el monitoreo y guarda el resultado como reporte interno."""
    from coopexecutive import monitoring

    settings = get_settings()
    perfil, carpeta = _perfil()
    with console.status("Consultando fuentes..."):
        try:
            reporte = monitoring.monitorear(
                list(temas) or perfil.focus_areas, hoy_local(settings.user_timezone), settings.carpeta_base,
                cache=settings.cache_dir / "monitoreo", usar_cache=not sin_cache,
            )
        except ValueError as exc:
            fallar(str(exc), "Monitoreo")
    _escribir(cartas.reporte_monitoreo(perfil, reporte), perfil, carpeta, aceptar)


@documento.command("reporte-evaluacion")
@click.argument("ids", nargs=-1, type=int)
@click.option("--expediente", "folios", multiple=True, help="Usa la evaluación más reciente de cada expediente.")
@click.option("--orden", type=click.Choice(["plazo", "puntaje"]), default="plazo", show_default=True)
@_SI
def documento_reporte_evaluacion(ids: tuple[int, ...], folios: tuple[str, ...], orden: str, aceptar: bool) -> None:
    """Comparación de evaluaciones guardadas y cuál atender primero (reporte interno)."""
    perfil, carpeta = _perfil()
    hoy = hoy_local(get_settings().user_timezone)
    try:
        elegidos = list(ids) + comparar.ultimas_por_expediente(list(folios))
        comparacion = comparar.comparar(comparar.cargar_varias(elegidos or comparar.recientes()), hoy, orden)
    except ValueError as exc:
        fallar(str(exc))
    _escribir(cartas.reporte_evaluacion(perfil, comparacion, hoy), perfil, carpeta, aceptar)


COMANDOS = (documento,)
