"""Diseño de proyecto: marco lógico, presupuesto y dossier.

Por omisión nada se genera con el modelo: la matriz y el presupuesto salen de un YAML
del usuario (``--desde``) o quedan como esqueleto con pendientes. Con ``--asistido`` el
modelo propone la estructura, que se valida y se revisa en modo estricto; los costos
propuestos por el modelo nunca se aceptan y quedan como COSTO POR COTIZAR.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import BaseModel, ValidationError
from rich.markdown import Markdown
from rich.panel import Panel

from coopexecutive.cli._consola import console, fallar
from coopexecutive.cli._modelo import pedir_modelo
from coopexecutive.config import get_settings
from coopexecutive.crm import cases
from coopexecutive.grant_tools.budget_builder import PLANTILLA_YAML as PLANTILLA_PRESUPUESTO
from coopexecutive.grant_tools.budget_builder import PresupuestoEntrada, presupuesto_desde_datos
from coopexecutive.grant_tools.dossier_generator import ProposalDossier
from coopexecutive.grant_tools.logical_framework import NIVELES, MarcoLogicoEntrada, marco_desde_datos
from coopexecutive.grant_tools.logical_framework import PLANTILLA_YAML as PLANTILLA_MARCO
from coopexecutive.guardrails import revisar_respuesta
from coopexecutive.guardrails.marcadores import pendiente
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import hoy_local

_SALIDA = click.option(
    "--salida", "-o", type=click.Path(dir_okay=False, path_type=Path), default=None,
    help="Guardar el resultado en un archivo Markdown (nunca sobrescribe).",
)
_DESDE = click.option(
    "--desde", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
    help="YAML con los datos (vea --plantilla).",
)
_PLANTILLA = click.option("--plantilla", is_flag=True, help="Mostrar la plantilla YAML y salir.")
_ASISTIDO = click.option(
    "--asistido", is_flag=True, help="Pedir al modelo una propuesta de estructura (se valida y se revisa).",
)


def _cargar_yaml(ruta: Path, modelo: type[BaseModel]) -> Any:
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        return modelo.model_validate(datos)
    except (yaml.YAMLError, ValidationError, UnicodeDecodeError) as exc:
        fallar(f"{ruta.name} no es válido: {exc}", "Datos no válidos")


def _entregar(markdown: str, salida: Path | None, contexto: str | None = None) -> None:
    """Revisa (si vino del modelo), muestra y, si se pide, guarda sin sobrescribir."""
    if contexto is not None:
        revision = revisar_respuesta(
            markdown, contexto, estricto=True, acciones_ejecutadas=True,
            hoy=hoy_local(get_settings().user_timezone),
        )
        markdown = revision.texto
        if revision.observaciones:
            console.print(Panel(
                "\n".join(f"- {o}" for o in revision.observaciones),
                title="Revisión automática", border_style="yellow",
            ))
    console.print(Markdown(markdown))
    if salida is not None:
        salida.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(salida, "x", encoding="utf-8") as archivo:
                archivo.write(markdown + "\n")
        except FileExistsError:
            fallar(f"{salida} ya existe; elija otro nombre.", "No se sobrescribe")
        console.print(f"[green]Guardado en[/green] {salida}", highlight=False)


def _perfil() -> CoopProfile:
    return CoopProfile.load_from_yaml(get_settings().company_profile_path)


# --- Marco lógico ------------------------------------------------------------------

_PEDIDO_MARCO = """\
Propón la estructura de un marco lógico para el proyecto «{proyecto}».
Responde solo con un objeto JSON con estas claves:
  "problema": texto, "teoria_cambio": texto, "ods": lista,
  "filas": lista de objetos con "nivel" ({niveles}), "resumen", "indicadores", "medios", "supuestos".
Reglas: no inventes cifras, fechas, líneas base, metas numéricas ni alianzas; si un dato no
consta en el perfil, escribe "[PENDIENTE: dato]". Deja "ods" vacío salvo que el perfil los cite.
"""


@click.command("marco-logico")
@click.argument("proyecto", type=str)
@_DESDE
@_PLANTILLA
@_ASISTIDO
@_SALIDA
def marco_logico(proyecto: str, desde: Path | None, plantilla: bool, asistido: bool, salida: Path | None) -> None:
    """Armar la Matriz de Marco Lógico (Fin, Propósito, Componentes, Actividades)."""
    if plantilla:
        console.print(PLANTILLA_MARCO, highlight=False, markup=False)
        return
    if desde and asistido:
        fallar("Use --desde o --asistido, no ambos.", "Opciones incompatibles")
    contexto = None
    if desde:
        entrada = _cargar_yaml(desde, MarcoLogicoEntrada)
    elif asistido:
        pedido = _PEDIDO_MARCO.format(proyecto=proyecto, niveles=", ".join(NIVELES))
        entrada, perfil = pedir_modelo(pedido, MarcoLogicoEntrada)
        contexto = f"{pedido}\n{perfil}"
    else:
        entrada = MarcoLogicoEntrada()
        console.print(
            "[dim]Esqueleto con pendientes. Llénelo con --desde (vea --plantilla) o pida una propuesta "
            "con --asistido.[/dim]\n"
        )
    _entregar(marco_desde_datos(proyecto, entrada).to_markdown(), salida, contexto)


# --- Presupuesto -------------------------------------------------------------------

_PEDIDO_PRESUPUESTO = """\
Propón las partidas del presupuesto del proyecto «{proyecto}».
Responde solo con un objeto JSON: {{"partidas": [{{"rubro": ..., "concepto": ..., "unidad": ..., "cantidad": ...}}]}}.
No incluyas costos ni montos: se cotizan después.
"""


@click.command("presupuesto")
@click.argument("proyecto", type=str)
@_DESDE
@_PLANTILLA
@_ASISTIDO
@click.option("--moneda", default=None, help="Código ISO 4217; por omisión, el del YAML o la moneda base del perfil.")
@click.option("--tope-indirectos", type=click.FloatRange(0, 100), default=None,
              help="Tope de costos indirectos (%) que fija la convocatoria.")
@_SALIDA
def presupuesto(
    proyecto: str, desde: Path | None, plantilla: bool, asistido: bool, moneda: str | None,
    tope_indirectos: float | None, salida: Path | None,
) -> None:
    """Armar un presupuesto con solicitado, contrapartida y partidas por cotizar."""
    if plantilla:
        console.print(PLANTILLA_PRESUPUESTO, highlight=False, markup=False)
        return
    if desde and asistido:
        fallar("Use --desde o --asistido, no ambos.", "Opciones incompatibles")
    perfil = _perfil()
    moneda_base = perfil.procuracion.moneda_base if perfil.procuracion else None
    if desde:
        entrada = _cargar_yaml(desde, PresupuestoEntrada)
        if moneda is None and "moneda" not in entrada.model_fields_set:
            moneda = moneda_base
    elif asistido:
        entrada, _ = pedir_modelo(_PEDIDO_PRESUPUESTO.format(proyecto=proyecto), PresupuestoEntrada)
        # Los costos nunca vienen del modelo: todo queda por cotizar.
        for partida in entrada.partidas:
            partida.costo_unitario = partida.solicitado = None
            partida.contrapartida = 0
        moneda = moneda or moneda_base
    else:
        entrada = PresupuestoEntrada()
        moneda = moneda or moneda_base
        console.print("[dim]Presupuesto vacío. Llénelo con --desde (vea --plantilla).[/dim]\n")
    try:
        armado = presupuesto_desde_datos(proyecto, entrada, moneda=moneda, tope_indirectos=tope_indirectos)
    except ValueError as exc:
        fallar(str(exc), "Datos no válidos")
    _entregar(armado.to_markdown(), salida)


# --- Dossier -----------------------------------------------------------------------


def _salvaguardas(perfil: CoopProfile) -> str:
    """Solo datos declarados en el perfil; los valores por omisión no cuentan como dato."""
    partes = []
    if perfil.es_cooperativa and "statutory_funds" in perfil.model_fields_set:
        f = perfil.statutory_funds
        partes.append(
            f"Fondos estatutarios: reserva {f.reserve_fund_pct:g} %, previsión social "
            f"{f.social_welfare_fund_pct:g} %, educación cooperativa {f.education_fund_pct:g} %."
        )
    if "governance" in perfil.model_fields_set:
        partes.append(f"Órgano de vigilancia: {perfil.governance.supervisory_body}.")
    return "\n\n".join(partes)


def _presupuesto_yaml(titulo: str, ruta: Path, moneda_base: str | None) -> Any:
    entrada = _cargar_yaml(ruta, PresupuestoEntrada)
    moneda = None if "moneda" in entrada.model_fields_set else moneda_base
    try:
        return presupuesto_desde_datos(titulo, entrada, moneda=moneda)
    except ValueError as exc:
        fallar(str(exc), "Datos no válidos")


@click.command("dossier")
@click.argument("proyecto")
@click.option("--expediente", default=None, help="Folio EXP-AAAA-NNNN: toma el financiador y la convocatoria.")
@click.option("--donante", default=None, help="Financiador o agencia cooperante.")
@click.option("--convocatoria", default=None, help="Título de la convocatoria.")
@click.option("--marco", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
              help="YAML del marco lógico.")
@click.option("--presupuesto", "presupuesto_yaml", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default=None, help="YAML del presupuesto.")
@_SALIDA
def dossier(
    proyecto: str, expediente: str | None, donante: str | None, convocatoria: str | None,
    marco: Path | None, presupuesto_yaml: Path | None, salida: Path | None,
) -> None:
    """Reunir el dossier de postulación; lo que falte queda pendiente."""
    perfil = _perfil()
    if expediente:
        exp = cases.obtener(expediente)
        if exp is None:
            fallar(f"No existe el expediente {expediente}.")
        donante = donante or exp.entidad
        convocatoria = convocatoria or exp.titulo
    moneda = perfil.procuracion.moneda_base if perfil.procuracion else None
    documento = ProposalDossier(
        project_name=proyecto,
        organization_name=perfil.name,
        donor_agency=donante or "",
        call_title=convocatoria or "",
        target_country=perfil.procuracion.territorio if perfil.procuracion else "",
        executive_summary=(
            f"{pendiente('resumen ejecutivo del proyecto')}\n\n**Misión de la organización:** {perfil.mission}"
            if perfil.mission else ""
        ),
        logical_framework=marco_desde_datos(proyecto, _cargar_yaml(marco, MarcoLogicoEntrada)) if marco else None,
        budget=_presupuesto_yaml(proyecto, presupuesto_yaml, moneda) if presupuesto_yaml else None,
        cooperative_safeguards=_salvaguardas(perfil),
        es_cooperativa=perfil.es_cooperativa,
    )
    _entregar(documento.to_markdown(), salida)


@click.group("proyecto")
def proyecto() -> None:
    """Diseño de proyecto: marco lógico, presupuesto y dossier."""


for _comando in (marco_logico, presupuesto, dossier):
    proyecto.add_command(_comando)

# Los tres también quedan en el nivel superior por compatibilidad.
COMANDOS = (proyecto, marco_logico, presupuesto, dossier)
