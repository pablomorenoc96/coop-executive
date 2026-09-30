"""Redacción asistida y preparación de reuniones, siempre con revisión estricta."""
from __future__ import annotations

import click
from pydantic import ValidationError
from rich.markdown import Markdown
from rich.panel import Panel

from coopexecutive.cli import _modelo
from coopexecutive.cli._consola import console, fallar
from coopexecutive.cli.analisis import MAX_FUENTE, leer_fuente
from coopexecutive.config import get_settings
from coopexecutive.crm import cases, funders
from coopexecutive.crm.cases import Expediente
from coopexecutive.documents import a_markdown, desde_markdown
from coopexecutive.grant_tools import reunion as _reunion
from coopexecutive.guardrails import agregar_leyenda, revisar_respuesta
from coopexecutive.lectura import ErrorLectura
from coopexecutive.memory import desde_sitio
from coopexecutive.utils.fechas import fecha_larga, hoy_local

# tipo -> (título del documento, indicaciones de estructura)
TIPOS: dict[str, tuple[str, str]] = {
    "propuesta": (
        "Propuesta",
        "Una propuesta de proyecto con estas secciones: Resumen, Problema y justificación, Objetivo general, "
        "Objetivos específicos, Población y territorio, Actividades, Resultados esperados, Presupuesto "
        "(solo montos que aparezcan en el contexto; si no, MONTO POR DEFINIR), Capacidad de la "
        "organización y Contacto.",
    ),
    "carta-intencion": (
        "Carta de intención",
        "Una carta de intención de una página: destinatario, interés en la convocatoria, breve presentación "
        "de la organización, alineación con las prioridades del financiador, monto que se solicita "
        "(MONTO POR DEFINIR si no consta) y cierre con firmante (RESPONSABLE POR CONFIRMAR si no consta).",
    ),
    "nota-conceptual": (
        "Nota conceptual",
        "Una nota conceptual de dos páginas como máximo: la organización, problema, objetivo, población y "
        "territorio, actividades principales, resultados esperados, presupuesto estimado y contacto.",
    ),
    "justificacion": (
        "Justificación",
        "Una justificación de proyecto: problema, evidencia disponible, por qué la organización está en "
        "condiciones de atenderlo y qué cambia si el proyecto se ejecuta. Solo cifras del contexto.",
    ),
    "correo-seguimiento": (
        "Correo de seguimiento",
        "Un correo breve de seguimiento (máximo 150 palabras): asunto, saludo, referencia a la gestión, "
        "lo que se pide o se ofrece y despedida con RESPONSABLE POR CONFIRMAR si no consta quién firma.",
    ),
}


def _contexto_expediente(e: Expediente) -> str:
    partes = [
        f"Expediente {e.folio}: {e.titulo}",
        f"Entidad: {e.entidad}",
        f"Tipo: {e.tipo}",
        f"Objetivo: {e.objetivo or 'por definir'}",
        f"Monto: {e.monto_texto}",
        f"Fecha límite: {fecha_larga(e.fecha_limite) if e.fecha_limite else 'por confirmar'}",
    ]
    return "\n".join(partes)


def _expediente(folio: str | None) -> Expediente | None:
    if not folio:
        return None
    e = cases.obtener(folio)
    if e is None:
        fallar(f"No existe el expediente {folio}.")
    return e


@click.command("redactar")
@click.argument("tipo", type=click.Choice(list(TIPOS)))
@click.option("--expediente", "folio", default=None, help="Folio EXP-AAAA-NNNN: aporta entidad, objetivo, monto y plazo.")
@click.option("--bases", default=None, help="URL o archivo con las bases de la convocatoria.")
@click.option("--indicaciones", default="", help="Lo que debe decir o destacar el texto.")
@click.option("--word", is_flag=True, help="Guardar también en Word con el membrete.")
@click.option("--si", "aceptar", is_flag=True, help="Con --word, guardar sin pedir confirmación.")
def redactar(tipo: str, folio: str | None, bases: str | None, indicaciones: str, word: bool, aceptar: bool) -> None:
    """Redacta un borrador para terceros con los datos del perfil, del expediente y de las bases.

    Montos y fechas sin respaldo se sustituyen por marcadores antes de mostrarse.
    """
    titulo, estructura = TIPOS[tipo]
    e = _expediente(folio)
    contexto = []
    if e is not None:
        contexto.append(_contexto_expediente(e))
    if bases:
        contexto.append("Bases de la convocatoria:\n" + leer_fuente(bases)[:MAX_FUENTE])
    if indicaciones.strip():
        contexto.append(f"Indicaciones del usuario: {indicaciones.strip()}")
    pedido = (
        f"Redacta en Markdown: {estructura}\n\n"
        "Reglas: el texto va para terceros. Usa solo datos del perfil de la organización y del contexto de "
        "abajo. No pongas etiquetas de origen entre corchetes; para lo que falte usa [PENDIENTE: dato], "
        "MONTO POR DEFINIR o RESPONSABLE POR CONFIRMAR. No inventes cifras, fechas, alianzas ni resultados. "
        "Sin emojis, sin notas internas y sin folios. Empieza con un encabezado de nivel 1.\n\n"
        + ("\n\n".join(contexto) or "(Sin contexto adicional.)")
    )
    texto, bloque = _modelo.ejecutar(_modelo.consultar(pedido, "procurador"))
    hoy = hoy_local(get_settings().user_timezone)
    revisado = _modelo.mostrar_revisada(texto, f"{pedido}\n{bloque}", titulo, hoy)
    if word:
        from coopexecutive.cli.documentos import _escribir, _perfil

        perfil, carpeta = _perfil()
        plano = desde_markdown.a_plano(revisado, tipo.replace("-", "_"), titulo)
        _escribir(plano, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None)


@click.group("reunion")
def reunion() -> None:
    """Preparar reuniones con financiadores o posibles aliados."""


@reunion.command("preparar")
@click.argument("entidad")
@click.option("--sitio", default=None, help="Sitio web público de la entidad; se leen la portada y hasta 3 páginas.")
@click.option("--financiador", "folio_financiador", default=None, help="Folio del financiador registrado.")
@click.option("--expediente", "folio", default=None, help="Folio EXP-AAAA-NNNN relacionado.")
@click.option("--objetivo", default="", help="Qué se busca obtener de la reunión.")
@click.option("--word", is_flag=True, help="Guardar también la preparación en Word.")
@click.option("--si", "aceptar", is_flag=True, help="Con --word, guardar sin pedir confirmación.")
def reunion_preparar(entidad: str, sitio: str | None, folio_financiador: str | None, folio: str | None,
                     objetivo: str, word: bool, aceptar: bool) -> None:
    """Perfil público, puntos en común, riesgos, agenda y preguntas. Cada dato lleva su etiqueta de origen."""
    from coopexecutive.cli.documentos import _escribir, _perfil

    perfil, carpeta = _perfil()
    contexto: list[str] = []
    if folio_financiador:
        f = funders.ver(folio_financiador)
        if f is None:
            fallar(f"No existe el financiador {folio_financiador}.")
        contexto.append(
            f"Financiador registrado: {f.organizacion}. Proyecto de interés: {f.proyecto}. Tipo: {f.tipo}. "
            f"Estatus: {f.estatus}. Canal: {f.canal}. Monto solicitado: {f.monto(f.monto_solicitado)}."
        )
    e = _expediente(folio)
    if e is not None:
        contexto.append(_contexto_expediente(e))

    paginas: list[desde_sitio.Pagina] = []
    if sitio:
        with console.status("Leyendo el sitio público..."):
            try:
                rastreo = desde_sitio.rastrear(sitio, max_paginas=3)
            except ErrorLectura as exc:
                fallar(str(exc), "No se pudo leer el sitio")
        paginas = rastreo.paginas
        console.print(f"[dim]Páginas leídas: {len(paginas)}.[/dim]")

    pedido = _reunion.instrucciones(entidad, objetivo, "\n".join(contexto), paginas)
    respuesta, bloque = _modelo.ejecutar(_modelo.consultar(pedido, "procurador"))
    try:
        prep = _reunion.Preparacion.model_validate(_modelo.extraer_json(respuesta))
    except (ValueError, ValidationError) as exc:
        fallar(f"La preparación del modelo no es válida: {exc}", "Propuesta no válida")
    prep = _reunion.validar(prep, paginas, bloque)
    plano = _reunion.a_plano(prep, entidad, objetivo, perfil, paginas)

    # Revisión estricta del texto completo: montos y fechas sin respaldo quedan marcados.
    fuentes = "\n".join(p.texto for p in paginas)
    revision = revisar_respuesta(a_markdown(plano), f"{pedido}\n{bloque}\n{fuentes}", estricto=True,
                                 hoy=hoy_local(get_settings().user_timezone))
    console.print(Panel(Markdown(agregar_leyenda(revision.texto)), title="Preparación de reunión",
                        border_style="cyan"))
    if revision.observaciones:
        console.print(Panel("\n".join(f"- {o}" for o in revision.observaciones),
                            title="Revisión automática", border_style="yellow"))
    if word:
        final = plano if revision.texto == a_markdown(plano) else desde_markdown.a_plano(revision.texto, plano.tipo)
        _escribir(final, perfil, carpeta, aceptar, expediente_folio=e.folio if e else None)


COMANDOS = (redactar, reunion)
