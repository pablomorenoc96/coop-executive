"""Carta de intención, nota conceptual y reportes de monitoreo y de evaluación.

Mismas reglas que `generador.py`: solo datos del perfil, del expediente, de la
evaluación o del contenido que aporta el usuario, y marcadores para lo que falte.
La carta y la nota van a terceros: sin folios, huellas ni notas internas. Los dos
reportes son internos.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from coopexecutive.crm.cases import Expediente
from coopexecutive.documents.contenido import DocumentoPlano, Lista, Parrafo, Tabla, Titulo
from coopexecutive.documents.generador import (
    DECISIONES,
    ContenidoSolicitud,
    _datos_generales,
    _lista_o_pendiente,
    _moneda_de,
    _o_pendiente,
    _tabla_presupuesto,
)
from coopexecutive.guardrails.marcadores import (
    MONTO_POR_DEFINIR,
    RESPONSABLE_POR_CONFIRMAR,
    pendiente,
)
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import fecha_larga
from coopexecutive.utils.moneda import formatear_monto, validar_moneda


class ContenidoCarta(BaseModel):
    """YAML opcional para la carta de intención. Lo que no venga queda pendiente."""

    destinatario: str = ""
    proyecto: str = ""
    objetivo: str = ""
    alineacion: str = ""
    monto_solicitado: float | None = Field(None, ge=0)
    moneda: str | None = None
    contrapartida: str = ""
    firmante: str = ""
    cargo: str = ""
    contacto: str = ""

    @field_validator("moneda")
    @classmethod
    def _moneda(cls, v: str | None) -> str | None:
        return validar_moneda(v) if v else None


def _monto(monto: float | None, moneda: str | None, expediente: Expediente | None) -> str:
    if monto is not None and moneda:
        return formatear_monto(monto, moneda)
    if expediente is not None:
        return expediente.monto_texto
    return MONTO_POR_DEFINIR


def carta_intencion(
    perfil: CoopProfile,
    expediente: Expediente | None,
    contenido: ContenidoCarta | None,
    hoy: date,
) -> DocumentoPlano:
    c = contenido or ContenidoCarta()
    p = perfil.procuracion
    destinatario = c.destinatario or (expediente.entidad if expediente else "")
    proyecto = c.proyecto or (expediente.titulo if expediente else "")
    moneda = c.moneda or (expediente.moneda if expediente else None) or (p.moneda_base if p else "MXN")
    doc = DocumentoPlano(tipo="carta_intencion", titulo="Carta de intención", subtitulo=_o_pendiente(proyecto, "proyecto"))
    b = doc.bloques
    b.append(Parrafo(f"Fecha: {fecha_larga(hoy)}", justificado=False))
    b.append(Parrafo(f"A: {_o_pendiente(destinatario, 'destinatario')}", justificado=False))
    b.append(Parrafo(
        f"{perfil.name}, {perfil.legal_structure.lower()}, manifiesta su interés en presentar el proyecto "
        f"«{_o_pendiente(proyecto, 'proyecto')}»."
    ))
    b.append(Parrafo(f"Nuestra misión: {_o_pendiente(perfil.mission, 'misión')}"))
    b.append(Parrafo(
        f"El proyecto busca {_o_pendiente(c.objetivo or (expediente.objetivo if expediente else ''), 'objetivo')}"
        .rstrip(".") + "."
    ))
    b.append(Parrafo(
        "Se alinea con las prioridades de la convocatoria en lo siguiente: "
        f"{_o_pendiente(c.alineacion, 'alineación con las prioridades del financiador')}"
    ))
    b.append(Parrafo(f"Monto que se solicita: {_monto(c.monto_solicitado, moneda, expediente)}."))
    if c.contrapartida.strip():
        b.append(Parrafo(f"Contrapartida de la organización: {c.contrapartida.strip()}"))
    if p and p.programas:
        b += [Titulo("Experiencia relacionada", 2), Lista(list(p.programas))]
    b.append(Parrafo(
        "Quedamos a su disposición para ampliar la información y presentar la propuesta completa "
        "en el formato que indique."
    ))
    firmante = c.firmante.strip() or RESPONSABLE_POR_CONFIRMAR
    cargo = c.cargo.strip() or pendiente("cargo de quien firma")
    b.append(Parrafo(f"Atentamente,\n{firmante}\n{cargo}\n{perfil.name}", justificado=False))
    b.append(Parrafo(f"Contacto: {_o_pendiente(c.contacto, 'área o cargo de contacto')}", justificado=False))
    return doc


def nota_conceptual(
    perfil: CoopProfile,
    expediente: Expediente | None,
    contenido: ContenidoSolicitud | None,
    hoy: date,
) -> DocumentoPlano:
    """Dos páginas para presentar la idea antes de la solicitud completa."""
    c = contenido or ContenidoSolicitud()
    p = perfil.procuracion
    proyecto = c.proyecto or (expediente.titulo if expediente else "")
    doc = DocumentoPlano(tipo="nota_conceptual", titulo="Nota conceptual", subtitulo=_o_pendiente(proyecto, "proyecto"))
    b = doc.bloques
    b.append(Parrafo(f"Fecha: {fecha_larga(hoy)}", justificado=False))
    if expediente is not None:
        b.append(Parrafo(f"Dirigida a: {expediente.entidad}", justificado=False))
    b += [Titulo("La organización"), _datos_generales(perfil), Parrafo(_o_pendiente(perfil.mission, "misión"))]
    b += [Titulo("Problema que atiende"), Parrafo(_o_pendiente(c.justificacion, "problema y justificación"))]
    objetivo = c.objetivo_general or (expediente.objetivo if expediente else "")
    b += [Titulo("Objetivo"), Parrafo(_o_pendiente(objetivo, "objetivo general"))]
    b += [Titulo("Población y territorio"), _lista_o_pendiente(perfil.target_communities, "población atendida")]
    b.append(Parrafo(f"Territorio: {_o_pendiente(p.territorio if p else '', 'territorio')}"))
    b += [Titulo("Actividades principales"),
          _lista_o_pendiente([a.actividad for a in c.actividades], "actividades principales")]
    b += [Titulo("Resultados esperados"), _lista_o_pendiente(c.resultados, "resultados esperados")]
    moneda = _moneda_de(perfil, expediente, c)
    b += [Titulo("Presupuesto estimado"), _tabla_presupuesto(c, moneda)]
    b.append(Titulo("Capacidad de la organización"))
    b.append(_lista_o_pendiente(p.metricas_impacto if p else [], "métricas de impacto verificables"))
    b += [Titulo("Contacto"), Parrafo(_o_pendiente(c.contacto, "área o cargo de contacto"))]
    return doc


def reporte_monitoreo(perfil: CoopProfile, reporte) -> DocumentoPlano:
    """Reporte interno de un `monitoring.Reporte`."""
    doc = DocumentoPlano(
        tipo="reporte_monitoreo", titulo="Reporte de monitoreo de convocatorias",
        subtitulo=f"{perfil.name} · {fecha_larga(reporte.hoy)}",
    )
    b = doc.bloques
    b.append(Parrafo(
        f"Temas: {', '.join(reporte.temas) or pendiente('temas')}. "
        f"Fuentes consultadas: {', '.join(reporte.consultadas) or 'ninguna'}. "
        f"Avisos leídos: {reporte.leidos}."
    ))

    def tabla(avisos) -> Tabla:
        return Tabla(
            ["Convocatoria", "Fuente", "Plazo", "Enlace"],
            [[a.titulo, a.fuente, a.plazo, a.enlace or "-"] for a in avisos],
            [2.4, 1, 1.4, 1.8],
        )

    b.append(Titulo("Priorizadas"))
    b.append(tabla(reporte.priorizadas) if reporte.priorizadas else Parrafo("Ningún aviso coincide con los temas."))
    if reporte.por_revisar:
        b += [Titulo("Por revisar"), tabla(reporte.por_revisar)]
    if reporte.cerradas:
        b += [Titulo("Cerradas"), tabla(reporte.cerradas)]
    if reporte.manuales:
        b += [Titulo("Revisión manual"), Lista([f"{f.nombre}: {f.url}" for f in reporte.manuales])]
    if reporte.fallidas:
        b += [Titulo("Fuentes que no respondieron"), Lista([f"{n}: {m}" for n, m in reporte.fallidas])]
    b.append(Parrafo(
        "Antes de evaluar, confirme las bases y la fecha de cierre en el sitio oficial de cada convocatoria."
    ))
    return doc


def reporte_evaluacion(perfil: CoopProfile, comparacion, hoy: date) -> DocumentoPlano:
    """Reporte interno de una `grant_tools.comparar.Comparacion`."""
    doc = DocumentoPlano(
        tipo="reporte_evaluacion", titulo="Reporte de evaluación de oportunidades",
        subtitulo=f"{perfil.name} · {fecha_larga(hoy)}",
    )
    b = doc.bloques
    filas = []
    for f in comparacion.filas:
        r = f.resultado
        filas.append([
            f"#{f.id} {r.convocatoria}",
            r.financiador or "-",
            DECISIONES.get(r.decision, r.decision),
            f"{r.puntaje}/{r.puntaje_maximo_evaluado}",
            f.plazo,
        ])
    b += [Titulo("Comparación"), Tabla(["Oportunidad", "Financiador", "Decisión", "Puntaje", "Plazo"], filas,
                                       [2.3, 1.4, 1.2, 0.8, 1.5])]
    b.append(Titulo("Qué atender primero"))
    if comparacion.prioridad is None:
        b.append(Parrafo(comparacion.motivo))
    else:
        r = comparacion.prioridad.resultado
        b.append(Parrafo(f"{r.convocatoria}. {comparacion.motivo}"))
        b += [Titulo("Siguiente paso", 2), Parrafo(r.siguiente_paso)]
        if r.contrapunto:
            b += [Titulo("Contrapunto", 2), Parrafo(r.contrapunto)]
    pendientes = sorted({p for f in comparacion.filas for p in f.resultado.pendientes})
    if pendientes:
        b += [Titulo("Criterios pendientes"), Lista(pendientes)]
    return doc
