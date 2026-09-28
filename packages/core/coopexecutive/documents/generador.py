"""Arma el contenido de la solicitud, el documento institucional y la ficha de oportunidad.

Solo se usan datos del perfil, del expediente, de la evaluación o del archivo de
contenido que aporta el usuario. Lo que falte queda marcado; nada se completa por
suposición. La solicitud y el documento institucional son para terceros: no llevan
folios, huellas ni notas internas.
"""
from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

from coopexecutive.crm.cases import Expediente
from coopexecutive.documents.contenido import DocumentoPlano, Lista, Parrafo, Tabla, Titulo
from coopexecutive.grant_tools.matrix import PUNTAJE_MAXIMO, ResultadoMatriz
from coopexecutive.guardrails.marcadores import COSTO_POR_COTIZAR, MONTO_POR_DEFINIR, pendiente
from coopexecutive.memory.company_profile import TIPOS_ORGANIZACION, CoopProfile
from coopexecutive.utils.fechas import fecha_larga
from coopexecutive.utils.moneda import formatear_monto, validar_moneda

DECISIONES: dict[str, str] = {
    "APLICAR": "Aplicar",
    "EXPLORAR": "Explorar",
    "CONDICIONAL": "Condicional",
    "DESCARTAR": "Descartar",
    "VERIFICAR_ELEGIBILIDAD": "Verificar elegibilidad",
    "VERIFICAR_VIGENCIA": "Verificar vigencia",
    "ESCALAR_DIRECCION": "Decisión de la dirección",
    "EVALUACION_INCOMPLETA": "Evaluación incompleta",
    "ERROR_VALIDACION": "Error de validación",
}

TITULO_SOLICITUD: dict[str, str] = {"Beca": "Solicitud de beca", "Crédito": "Solicitud de crédito"}


# --- Contenido que aporta el usuario para la solicitud ---------------------------------


class Actividad(BaseModel):
    actividad: str
    periodo: str = ""


class Partida(BaseModel):
    concepto: str
    monto: float | None = Field(None, ge=0)
    moneda: str | None = None

    @field_validator("moneda")
    @classmethod
    def _moneda(cls, v: str | None) -> str | None:
        return validar_moneda(v) if v else None


class ContenidoSolicitud(BaseModel):
    """Archivo YAML opcional con el contenido del proyecto. Lo que no venga queda pendiente."""

    proyecto: str = ""
    objetivo_general: str = ""
    justificacion: str = ""
    objetivos: list[str] = Field(default_factory=list)
    actividades: list[Actividad] = Field(default_factory=list)
    resultados: list[str] = Field(default_factory=list)
    presupuesto: list[Partida] = Field(default_factory=list)
    monto_solicitado: float | None = Field(None, ge=0)
    moneda: str | None = None
    contacto: str = ""

    @field_validator("moneda")
    @classmethod
    def _moneda(cls, v: str | None) -> str | None:
        return validar_moneda(v) if v else None


# --- Piezas comunes ----------------------------------------------------------------


def _o_pendiente(valor: str, dato: str) -> str:
    return valor.strip() or pendiente(dato)


def _lista_o_pendiente(valores: list[str], dato: str) -> Lista:
    limpios = [v.strip() for v in valores if v.strip()]
    return Lista(limpios or [pendiente(dato)])


def _datos_generales(perfil: CoopProfile) -> Tabla:
    p = perfil.procuracion
    filas = [
        ["Nombre", perfil.name],
        ["Figura jurídica", perfil.legal_structure],
        ["Tipo de organización", TIPOS_ORGANIZACION[perfil.tipo_organizacion or "cooperativa"]],
        ["Estatus legal", _o_pendiente(p.estatus_legal if p else "", "estatus legal")],
        ["Estatus fiscal", _o_pendiente(p.estatus_fiscal if p else "", "estatus fiscal")],
        ["Territorio", _o_pendiente(p.territorio if p else "", "territorio")],
        ["País", perfil.country],
    ]
    return Tabla(["Dato", "Valor"], filas, [1, 2.2])


def _moneda_de(perfil: CoopProfile, expediente: Expediente | None, contenido: ContenidoSolicitud) -> str:
    if contenido.moneda:
        return contenido.moneda
    if expediente is not None and expediente.moneda:
        return expediente.moneda
    return perfil.procuracion.moneda_base if perfil.procuracion else "MXN"


# --- Solicitud -----------------------------------------------------------------------


def solicitud(
    perfil: CoopProfile,
    expediente: Expediente,
    contenido: ContenidoSolicitud | None,
    hoy: date,
) -> DocumentoPlano:
    c = contenido or ContenidoSolicitud()
    p = perfil.procuracion
    moneda = _moneda_de(perfil, expediente, c)
    doc = DocumentoPlano(
        tipo="solicitud",
        titulo=TITULO_SOLICITUD.get(expediente.tipo, "Solicitud de apoyo"),
        subtitulo=_o_pendiente(c.proyecto, "nombre del proyecto"),
    )
    b = doc.bloques
    b.append(Parrafo(f"Fecha: {fecha_larga(hoy)}"))
    b.append(Parrafo(f"Dirigida a: {expediente.entidad}"))

    b += [Titulo("Datos de la organización"), _datos_generales(perfil)]
    b += [Titulo("Misión"), Parrafo(_o_pendiente(perfil.mission, "misión"))]

    b.append(Titulo("Objetivo general"))
    b.append(Parrafo(_o_pendiente(c.objetivo_general or expediente.objetivo, "objetivo general")))
    b += [Titulo("Justificación"), Parrafo(_o_pendiente(c.justificacion, "justificación del proyecto"))]
    b += [Titulo("Objetivos específicos"), _lista_o_pendiente(c.objetivos, "objetivos específicos")]

    b.append(Titulo("Población y territorio"))
    b.append(_lista_o_pendiente(perfil.target_communities, "población atendida"))
    b.append(Parrafo(f"Territorio: {_o_pendiente(p.territorio if p else '', 'territorio')}"))

    b.append(Titulo("Actividades y calendario"))
    filas = [[a.actividad, _o_pendiente(a.periodo, "periodo")] for a in c.actividades]
    b.append(Tabla(["Actividad", "Periodo"], filas or [[pendiente("actividades"), pendiente("calendario")]], [2.5, 1]))

    b += [Titulo("Resultados esperados"), _lista_o_pendiente(c.resultados, "resultados esperados")]

    b.append(Titulo("Presupuesto"))
    b.append(_tabla_presupuesto(c, moneda))
    if c.monto_solicitado is not None:
        solicitado = formatear_monto(c.monto_solicitado, moneda)
    else:
        solicitado = expediente.monto_texto
    b.append(Parrafo(f"Monto solicitado: {solicitado}"))

    b.append(Titulo("Experiencia de la organización"))
    b.append(Titulo("Programas", 2))
    b.append(_lista_o_pendiente(p.programas if p else [], "programas"))
    b.append(Titulo("Resultados verificables", 2))
    b.append(_lista_o_pendiente(p.metricas_impacto if p else [], "métricas de impacto verificables"))
    if p and p.alianzas:
        b += [Titulo("Alianzas", 2), Lista(list(p.alianzas))]

    b += [Titulo("Contacto"), Parrafo(_o_pendiente(c.contacto, "área o cargo de contacto"))]
    return doc


def _tabla_presupuesto(c: ContenidoSolicitud, moneda: str) -> Tabla:
    if not c.presupuesto:
        return Tabla(["Concepto", "Monto"], [[pendiente("conceptos del presupuesto"), COSTO_POR_COTIZAR]], [2.5, 1])
    filas = []
    for partida in c.presupuesto:
        monto = COSTO_POR_COTIZAR if partida.monto is None else formatear_monto(partida.monto, partida.moneda or moneda)
        filas.append([partida.concepto, monto])
    monedas = {partida.moneda or moneda for partida in c.presupuesto}
    completos = all(partida.monto is not None for partida in c.presupuesto)
    # Solo se suma si todas las partidas tienen monto y la misma moneda; no se convierte.
    total = (
        formatear_monto(sum(partida.monto for partida in c.presupuesto), monedas.pop())  # type: ignore[misc]
        if completos and len(monedas) == 1
        else MONTO_POR_DEFINIR
    )
    filas.append(["Total", total])
    return Tabla(["Concepto", "Monto"], filas, [2.5, 1])


# --- Documento institucional -------------------------------------------------------------


def documento_institucional(perfil: CoopProfile, hoy: date) -> DocumentoPlano:
    p = perfil.procuracion
    doc = DocumentoPlano(tipo="documento_institucional", titulo=perfil.name, subtitulo="Documento institucional")
    b = doc.bloques
    b.append(Parrafo(f"Fecha: {fecha_larga(hoy)}"))
    b += [Titulo("Datos generales"), _datos_generales(perfil)]
    b += [Titulo("Misión"), Parrafo(_o_pendiente(perfil.mission, "misión"))]
    if perfil.vision.strip():
        b += [Titulo("Visión"), Parrafo(perfil.vision.strip())]
    if perfil.values:
        b += [Titulo("Valores"), Lista(list(perfil.values))]
    b += [Titulo("Población atendida"), _lista_o_pendiente(perfil.target_communities, "población atendida")]
    if perfil.focus_areas:
        b += [Titulo("Ejes de trabajo"), Lista(list(perfil.focus_areas))]
    b += [Titulo("Programas"), _lista_o_pendiente(p.programas if p else [], "programas")]
    b.append(Titulo("Resultados verificables"))
    b.append(_lista_o_pendiente(p.metricas_impacto if p else [], "métricas de impacto verificables"))
    if p and p.alianzas:
        b += [Titulo("Alianzas"), Lista(list(p.alianzas))]
    if p and p.financiadores_historicos:
        b += [Titulo("Han apoyado nuestro trabajo"), Lista(list(p.financiadores_historicos))]
    if perfil.tiene_asamblea:
        g = perfil.governance
        b.append(Titulo("Gobierno"))
        b.append(Tabla(["Órgano", "Función"], [
            [g.supreme_organ, "Órgano supremo de decisión"],
            [g.executive_body, "Administración"],
            [g.supervisory_body, "Vigilancia"],
        ], [2, 1]))
    if p and p.mecanismos_cobro:
        b += [Titulo("Cómo apoyar"), Lista(list(p.mecanismos_cobro))]
    return doc


# --- Ficha de oportunidad ------------------------------------------------------------------

_ORACIONES = re.compile(r"(?<=[.!?])\s+")


def _sin_tension(texto: str) -> str:
    """Quita las oraciones sobre tensiones internas: no se escriben en archivos."""
    oraciones = [o for o in _ORACIONES.split(texto.strip()) if not re.search(r"tensi[oó]n|posici[oó]n p[uú]blica", o, re.I)]
    return " ".join(oraciones).strip()


def ficha_oportunidad(
    perfil: CoopProfile,
    resultado: ResultadoMatriz,
    expediente: Expediente | None,
) -> DocumentoPlano:
    """Ficha interna de decisión: datos, decisión, puntaje con evidencia y siguiente paso."""
    doc = DocumentoPlano(tipo="ficha_oportunidad", titulo="Ficha de oportunidad", subtitulo=resultado.convocatoria)
    b = doc.bloques
    filas = [
        ["Organización", perfil.name],
        ["Oportunidad", resultado.convocatoria],
        ["Financiador", _o_pendiente(resultado.financiador, "financiador")],
        ["Tipo", resultado.tipo.capitalize()],
        ["Monto", resultado.monto or MONTO_POR_DEFINIR],
        ["Fecha de cierre", fecha_larga(resultado.fecha_cierre) if resultado.fecha_cierre else pendiente("fecha de cierre")],
        ["Plazo al evaluar", resultado.plazo],
        ["Fecha de evaluación", fecha_larga(resultado.fecha_evaluacion)],
    ]
    if expediente is not None:
        filas.append(["Expediente", expediente.folio])
    b += [Titulo("Datos de la oportunidad"), Tabla(["Dato", "Valor"], filas, [1, 2.2])]

    b.append(Titulo(f"Decisión: {DECISIONES.get(resultado.decision, resultado.decision)}"))
    motivo = _sin_tension(resultado.motivo) or resultado.siguiente_paso
    b.append(Parrafo(motivo))

    b.append(Titulo("Puntaje"))
    b.append(Parrafo(
        f"{resultado.puntaje} puntos de {resultado.puntaje_maximo_evaluado} evaluados "
        f"({PUNTAJE_MAXIMO} posibles)."
    ))
    b.append(Tabla(
        ["Criterio", "Peso", "Puntos", "Evidencia"],
        [[c.nombre, str(c.peso), "Pendiente" if c.puntos is None else str(c.puntos), c.evidencia or "-"]
         for c in resultado.criterios],
        [2.2, 0.6, 0.7, 3],
    ))
    if resultado.pendientes:
        b += [Titulo("Pendientes"), Lista(list(resultado.pendientes))]
    if resultado.errores:
        b += [Titulo("Datos por corregir"), Lista(list(resultado.errores))]
    b += [Titulo("Siguiente paso"), Parrafo(resultado.siguiente_paso)]
    contrapunto = _sin_tension(resultado.contrapunto)
    if contrapunto:
        b += [Titulo("Contrapunto"), Parrafo(contrapunto)]
    b.append(Parrafo(f"Huella de la evaluación (SHA-256): {resultado.hash}"))
    return doc
