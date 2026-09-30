"""Catálogo de herramientas: consultas de solo lectura y acciones que escriben.

Las funciones reutilizan los módulos de la CLI (matriz, expedientes, financiadores,
monitoreo y documentos); aquí solo se validan entradas y se arma la respuesta JSON.
Cada respuesta trae `resumen`, una línea que va a la bitácora.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from coopexecutive.config import get_settings
from coopexecutive.herramientas import Herramienta, registrar
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.fechas import fecha_larga, hoy_local

# --- Utilidades ---------------------------------------------------------------------------


def _perfil() -> CoopProfile:
    return CoopProfile.load_from_yaml(get_settings().company_profile_path)


def _hoy() -> date:
    return hoy_local(get_settings().user_timezone)


class _SinEntrada(BaseModel):
    pass


# --- Fecha y perfil ------------------------------------------------------------------------


class _EntradaFecha(BaseModel):
    cierres: list[str] = Field(default_factory=list, description="Fechas de cierre: AAAA-MM-DD, DD/MM/AAAA o «30 de octubre de 2026».")


def _fecha(e: _EntradaFecha) -> dict[str, Any]:
    from coopexecutive.utils.plazos import plazo

    hoy = _hoy()
    plazos = []
    for texto in e.cierres:
        p = plazo(texto, hoy)
        plazos.append({"cierre": p.cierre.isoformat(), "fecha_larga": p.fecha_larga, "dias": p.dias,
                       "texto": p.texto, "urgente": p.urgente, "vencida": p.vencida})
    return {"hoy": hoy.isoformat(), "hoy_texto": fecha_larga(hoy), "zona_horaria": get_settings().user_timezone,
            "plazos": plazos, "resumen": f"Hoy {hoy.isoformat()}; {len(plazos)} plazo(s) calculado(s)."}


def _ver_perfil(_: _SinEntrada) -> dict[str, Any]:
    perfil = _perfil()
    return {"nombre": perfil.name, "figura": perfil.legal_structure, "ejes": perfil.focus_areas,
            "tiene_asamblea": perfil.tiene_asamblea, "perfil": perfil.to_prompt_block(),
            "resumen": f"Perfil de {perfil.name}."}


class _EntradaConocimiento(BaseModel):
    pregunta: str = Field(min_length=2, description="Qué se quiere saber de la organización o de la procuración.")
    limite: int = Field(4, ge=1, le=10)


def _conocimiento(e: _EntradaConocimiento) -> dict[str, Any]:
    from coopexecutive import knowledge

    settings = get_settings()
    pasajes = knowledge.documentos(settings.carpeta_base / knowledge.CARPETA_ESPACIO, _perfil().to_prompt_block())
    hallados = knowledge.buscar(e.pregunta, pasajes, e.limite)
    if not hallados:
        return {"pasajes": [], "nota": knowledge.NO_CONSTA, "resumen": "Sin pasajes."}
    return {"pasajes": [{"fuente": p.fuente, "titulo": p.titulo, "texto": p.texto} for p in hallados],
            "nota": "Cite la fuente de cada dato; lo que no esté en los pasajes no consta.",
            "resumen": f"{len(hallados)} pasaje(s)."}


# --- Evaluaciones --------------------------------------------------------------------------

from coopexecutive.grant_tools.matrix import CRITERIOS, EntradaMatriz  # noqa: E402

_CRITERIOS_TEXTO = ", ".join(f"{clave} (0 a {peso})" for clave, (_, peso) in CRITERIOS.items())


def _evaluar(e: EntradaMatriz):
    from coopexecutive.grant_tools import matrix

    perfil = _perfil()
    return matrix.evaluar(e.model_dump(), hoy=_hoy(), rango_presupuesto_definido=perfil.rango_presupuesto_definido)


def _evaluacion(e: EntradaMatriz) -> dict[str, Any]:
    r = _evaluar(e)
    return {"resultado": r.model_dump(mode="json"), "guardada": False,
            "resumen": f"{r.decision} con {r.puntaje} puntos: {r.convocatoria}."}


class _EntradaGuardarEvaluacion(EntradaMatriz):
    expediente: str | None = Field(None, description="Folio EXP-AAAA-NNNN al que se vincula.")


def _guardar_evaluacion(e: _EntradaGuardarEvaluacion) -> dict[str, Any]:
    from coopexecutive.crm import cases
    from coopexecutive.grant_tools import matrix

    folio = None
    if e.expediente:
        expediente = cases.obtener(e.expediente)
        if expediente is None:
            raise ValueError(f"No existe el expediente {e.expediente}.")
        folio = expediente.folio
    r = _evaluar(EntradaMatriz.model_validate(e.model_dump(exclude={"expediente"})))
    if r.decision == "ERROR_VALIDACION":
        raise ValueError("La evaluación tiene errores y no se guardó: " + "; ".join(r.errores))
    id_evaluacion = matrix.guardar(r, folio)
    return {"id": id_evaluacion, "expediente": folio, "resultado": r.model_dump(mode="json"), "guardada": True,
            "resumen": f"Evaluación {id_evaluacion} guardada: {r.decision} con {r.puntaje} puntos."}


class _EntradaListarEvaluaciones(BaseModel):
    limite: int = Field(10, ge=1, le=50)


def _listar_evaluaciones(e: _EntradaListarEvaluaciones) -> dict[str, Any]:
    from coopexecutive.grant_tools import comparar

    hoy = _hoy()
    filas = []
    for ev in comparar.cargar_varias(comparar.recientes(e.limite)):
        fila = comparar._fila(ev, hoy)
        r = ev.resultado
        filas.append({"id": ev.id, "expediente": ev.expediente_folio, "convocatoria": r.convocatoria,
                      "financiador": r.financiador, "decision": r.decision, "puntaje": r.puntaje,
                      "plazo": fila.plazo, "dias": fila.dias, "fecha_evaluacion": r.fecha_evaluacion.isoformat()})
    return {"evaluaciones": filas, "resumen": f"{len(filas)} evaluación(es)."}


class _EntradaComparar(BaseModel):
    ids: list[int] = Field(default_factory=list, description="Id de evaluaciones guardadas.")
    expedientes: list[str] = Field(default_factory=list, description="Folios: se usa la última evaluación de cada uno.")
    orden: Literal["plazo", "puntaje"] = "plazo"


def _comparar(e: _EntradaComparar) -> dict[str, Any]:
    from coopexecutive.grant_tools import comparar

    hoy = _hoy()
    elegidos = list(e.ids) + comparar.ultimas_por_expediente(e.expedientes)
    res = comparar.comparar(comparar.cargar_varias(elegidos or comparar.recientes()), hoy, e.orden)
    filas = [{"id": f.id, "expediente": f.expediente, "convocatoria": f.resultado.convocatoria,
              "decision": f.resultado.decision, "puntaje": f.resultado.puntaje, "plazo": f.plazo,
              "descartada": f.descartada} for f in res.filas]
    prioridad = res.prioridad.id if res.prioridad else None
    return {"filas": filas, "prioridad": prioridad, "motivo": res.motivo,
            "resumen": f"Prioridad: {prioridad if prioridad is not None else 'ninguna'}."}


# --- Financiadores -------------------------------------------------------------------------


class _EntradaBuscarFinanciadores(BaseModel):
    texto: str = Field("", description="Folio FIN-AAAA-NNNN o parte del nombre o del proyecto. Vacío: los recientes.")
    limite: int = Field(20, ge=1, le=100)


def _financiador_dict(f) -> dict[str, Any]:
    return {**f.model_dump(mode="json"), "monto_solicitado_texto": f.monto(f.monto_solicitado)}


def _buscar_financiadores(e: _EntradaBuscarFinanciadores) -> dict[str, Any]:
    from coopexecutive.crm import funders

    hallados = funders.buscar(e.texto, e.limite)
    return {"financiadores": [_financiador_dict(f) for f in hallados], "resumen": f"{len(hallados)} financiador(es)."}


class _EntradaFolio(BaseModel):
    folio: str = Field(min_length=3)


def _ver_financiador(e: _EntradaFolio) -> dict[str, Any]:
    from coopexecutive.crm import funders

    f = funders.ver(e.folio)
    if f is None:
        raise LookupError(f"No existe el financiador {e.folio}.")
    return {"financiador": _financiador_dict(f), "resumen": f"{f.folio}: {f.organizacion}."}


class _EntradaRegistrarFinanciador(BaseModel):
    organizacion: str = Field(min_length=1)
    proyecto: str = Field(min_length=1, description="La iniciativa, sin montos ni fechas.")
    tipo: str = Field(description="Empresa, Fundación, Persona física, Agencia internacional, Gobierno o Institución financiera.")
    canal: str = Field(description="Correo, Teléfono, Reunión, Evento, Referencia, Convocatoria pública, Sitio web, Redes sociales u Otro.")
    moneda: str = "MXN"
    monto_solicitado: float | None = Field(None, ge=0, description="Solo si el usuario lo dio; si no, se omite.")
    contacto: str = ""
    seguimiento: date | None = None
    notas: str = ""


def _registrar_financiador(e: _EntradaRegistrarFinanciador) -> dict[str, Any]:
    from coopexecutive.crm import funders

    f = funders.registrar(e.organizacion, e.proyecto, e.tipo, e.canal, moneda=e.moneda,
                          monto_solicitado=e.monto_solicitado, contacto=e.contacto, seguimiento=e.seguimiento,
                          notas=e.notas)
    return {"financiador": _financiador_dict(f), "resumen": f"Financiador {f.folio} registrado: {f.organizacion}."}


# --- Expedientes ---------------------------------------------------------------------------


class _EntradaListarExpedientes(BaseModel):
    estado: Literal["abiertos", "cerrados", "todos"] = "abiertos"
    responsable: str | None = None
    limite: int = Field(50, ge=1, le=200)


def _expediente_dict(e) -> dict[str, Any]:
    return {**e.model_dump(mode="json"), "monto_texto": e.monto_texto}


def _listar_expedientes(e: _EntradaListarExpedientes) -> dict[str, Any]:
    from coopexecutive.crm import cases

    lista = cases.listar(e.responsable, e.estado, e.limite)
    return {"expedientes": [_expediente_dict(x) for x in lista], "resumen": f"{len(lista)} expediente(s)."}


def _ver_expediente(e: _EntradaFolio) -> dict[str, Any]:
    from coopexecutive import documents
    from coopexecutive.crm import cases

    x = cases.obtener(e.folio)
    if x is None:
        raise LookupError(f"No existe el expediente {e.folio}.")
    return {
        "expediente": _expediente_dict(x),
        "avances": [a.model_dump() for a in cases.avances(x.folio)],
        "evaluaciones": [v.model_dump() for v in cases.evaluaciones(x.folio)],
        "documentos": [d.model_dump() for d in documents.documentos_de(x.folio)],
        "resumen": f"{x.folio}: {x.titulo}.",
    }


class _EntradaAbrirExpediente(BaseModel):
    tipo: str = Field(description="Convocatoria, Financiador, Propuesta, Reunión, Crédito, Beca u Otro.")
    entidad: str = Field(min_length=1, description="Financiador o convocatoria.")
    objetivo: str = ""
    responsable: str = ""
    fecha_limite: date | None = None
    monto: float | None = Field(None, ge=0, description="Solo si consta; si no, queda MONTO POR DEFINIR.")
    moneda: str = "MXN"


def _abrir_expediente(e: _EntradaAbrirExpediente) -> dict[str, Any]:
    from coopexecutive.crm import cases

    x = cases.abrir(e.tipo, e.entidad, objetivo=e.objetivo, responsable=e.responsable,
                    fecha_limite=e.fecha_limite, monto=e.monto, moneda=e.moneda)
    return {"expediente": _expediente_dict(x), "resumen": f"Expediente {x.folio} abierto: {x.titulo}."}


class _EntradaAvance(BaseModel):
    folio: str = Field(min_length=3)
    estado: str = Field(min_length=1, description="Qué pasó.")
    pendientes: str = ""
    siguiente_accion: str = ""
    origen: str = Field("Dato del usuario", description="Dato del usuario, Dato institucional, Dato público verificado, "
                        "Supuesto, Inferencia estratégica o No verificado.")
    cerrar: bool = False


def _registrar_avance(e: _EntradaAvance) -> dict[str, Any]:
    from coopexecutive.crm import cases

    a = cases.registrar_avance(e.folio, e.estado, pendientes=e.pendientes, siguiente_accion=e.siguiente_accion,
                               origen=e.origen, cerrar=e.cerrar)
    return {"avance": a.model_dump(), "cerrado": e.cerrar, "resumen": f"Avance registrado en {e.folio.upper()}."}


# --- Documentos ----------------------------------------------------------------------------


class _EntradaListarDocumentos(BaseModel):
    expediente: str | None = None
    limite: int = Field(50, ge=1, le=200)


def _listar_documentos(e: _EntradaListarDocumentos) -> dict[str, Any]:
    from coopexecutive import documents

    lista = documents.documentos_de(e.expediente) if e.expediente else documents.recientes(e.limite)
    return {"documentos": [d.model_dump() for d in lista], "resumen": f"{len(lista)} documento(s)."}


class _EntradaDocumento(BaseModel):
    tipo: Literal["institucional", "ficha", "carta-intencion", "nota-conceptual", "reporte-evaluacion"]
    expediente: str | None = Field(None, description="Folio EXP-AAAA-NNNN.")
    evaluacion: int | None = Field(None, description="Id de la evaluación (ficha).")
    ids: list[int] = Field(default_factory=list, description="Evaluaciones a comparar (reporte-evaluacion).")


def _generar_documento(e: _EntradaDocumento) -> dict[str, Any]:
    from coopexecutive import documents
    from coopexecutive.crm import cases
    from coopexecutive.documents import cartas, generador
    from coopexecutive.grant_tools import comparar, matrix
    from coopexecutive.memory.company_profile import Membrete

    settings = get_settings()
    perfil = _perfil()
    hoy = _hoy()
    exp = None
    if e.expediente:
        exp = cases.obtener(e.expediente)
        if exp is None:
            raise LookupError(f"No existe el expediente {e.expediente}.")
    evaluacion_id = None
    if e.tipo == "institucional":
        plano = generador.documento_institucional(perfil, hoy)
    elif e.tipo == "carta-intencion":
        plano = cartas.carta_intencion(perfil, exp, None, hoy)
    elif e.tipo == "nota-conceptual":
        plano = cartas.nota_conceptual(perfil, exp, None, hoy)
    elif e.tipo == "reporte-evaluacion":
        res = comparar.comparar(comparar.cargar_varias(list(e.ids) or comparar.recientes()), hoy)
        plano = cartas.reporte_evaluacion(perfil, res, hoy)
    else:
        evaluacion_id = e.evaluacion
        if evaluacion_id is None:
            if exp is None:
                raise ValueError("La ficha necesita una evaluación o un expediente con evaluaciones.")
            vinculadas = cases.evaluaciones(exp.folio)
            if not vinculadas:
                raise ValueError(f"El expediente {exp.folio} no tiene evaluaciones.")
            evaluacion_id = vinculadas[-1].id
        guardada = matrix.cargar(evaluacion_id)
        if exp is None and guardada.expediente_folio:
            exp = cases.obtener(guardada.expediente_folio)
        plano = generador.ficha_oportunidad(perfil, guardada.resultado, exp)
    membrete = perfil.procuracion.membrete if perfil.procuracion else Membrete()
    doc = documents.guardar(plano, membrete, settings.company_profile_path.parent, settings.salidas_dir, hoy,
                            autor=perfil.name, expediente_folio=exp.folio if exp else None,
                            evaluacion_id=evaluacion_id)
    return {"documento": doc.model_dump(), "pendientes": plano.pendientes(),
            "resumen": f"Documento {plano.tipo} guardado con huella {doc.sha256[:12]}."}


# --- Monitoreo y asamblea ------------------------------------------------------------------


class _EntradaMonitoreo(BaseModel):
    temas: list[str] = Field(default_factory=list, description="Temas; vacío usa los ejes de trabajo del perfil.")
    usar_cache: bool = True


def _monitorear(e: _EntradaMonitoreo) -> dict[str, Any]:
    from coopexecutive import monitoring

    settings = get_settings()
    reporte = monitoring.monitorear(list(e.temas) or _perfil().focus_areas, _hoy(), settings.carpeta_base,
                                    cache=settings.cache_dir / "monitoreo", usar_cache=e.usar_cache)
    monitoring.guardar_reporte(reporte)
    datos = monitoring.reporte_dict(reporte)
    return {**datos, "resumen": f"{len(reporte.priorizadas)} priorizada(s), {len(reporte.por_revisar)} por revisar."}


def _ultimo_monitoreo(_: _SinEntrada) -> dict[str, Any]:
    from coopexecutive import monitoring

    ultimo = monitoring.ultimo_reporte()
    if ultimo is None:
        return {"monitoreo": None, "resumen": "Sin monitoreos."}
    return {"monitoreo": ultimo, "resumen": f"Monitoreo del {ultimo['ejecutado_en']}."}


class _EntradaPropuestas(BaseModel):
    estado: Literal["abierta", "aprobada", "rechazada"] | None = None


def _propuestas(e: _EntradaPropuestas) -> dict[str, Any]:
    from coopexecutive.governance import voting

    lista = voting.list_proposals(e.estado)
    return {"propuestas": lista, "padron_activo": voting.padron_activo(), "resumen": f"{len(lista)} propuesta(s)."}


# --- Registro --------------------------------------------------------------------------------

for _h in (
    Herramienta("fecha_y_plazos", "Fecha de hoy en la zona horaria configurada y días naturales que faltan a cada "
                "fecha de cierre (urgente con 13 días o menos).", _EntradaFecha, _fecha),
    Herramienta("ver_perfil", "Perfil de la organización: nombre, figura, misión, ejes y datos de procuración.",
                _SinEntrada, _ver_perfil),
    Herramienta("buscar_conocimiento", "Busca en el perfil, la carpeta de conocimiento y las guías incluidas. "
                "Devuelve pasajes con su fuente; si no hay, el dato no consta.", _EntradaConocimiento, _conocimiento),
    Herramienta("evaluar_oportunidad", "Evalúa una convocatoria con la matriz determinista sin guardarla. Criterios: "
                f"{_CRITERIOS_TEXTO}. Cada puntaje necesita evidencia; un criterio sin dato se deja vacío (pendiente).",
                EntradaMatriz, _evaluacion),
    Herramienta("listar_evaluaciones", "Evaluaciones guardadas más recientes con su decisión, puntaje y plazo a hoy.",
                _EntradaListarEvaluaciones, _listar_evaluaciones),
    Herramienta("comparar_evaluaciones", "Compara evaluaciones guardadas e indica cuál atender primero.",
                _EntradaComparar, _comparar),
    Herramienta("buscar_financiadores", "Busca financiadores registrados por folio, nombre o proyecto.",
                _EntradaBuscarFinanciadores, _buscar_financiadores),
    Herramienta("ver_financiador", "Ficha de un financiador por folio FIN-AAAA-NNNN.", _EntradaFolio, _ver_financiador),
    Herramienta("listar_expedientes", "Expedientes de procuración abiertos, cerrados o todos.",
                _EntradaListarExpedientes, _listar_expedientes),
    Herramienta("ver_expediente", "Expediente con sus avances, evaluaciones y documentos.", _EntradaFolio,
                _ver_expediente),
    Herramienta("listar_documentos", "Documentos Word generados, de un expediente o los más recientes.",
                _EntradaListarDocumentos, _listar_documentos),
    Herramienta("monitorear_convocatorias", "Consulta las fuentes públicas de convocatorias y filtra por los temas. "
                "Solo salen a la red los temas; ningún dato de la organización.", _EntradaMonitoreo, _monitorear,
                red=True),
    Herramienta("ultimo_monitoreo", "Resultado del monitoreo más reciente, sin consultar la red.", _SinEntrada,
                _ultimo_monitoreo),
    Herramienta("listar_propuestas_asamblea", "Propuestas de la asamblea y número de socios activos.",
                _EntradaPropuestas, _propuestas),
    Herramienta("registrar_financiador", "Registra un financiador nuevo. Pide confirmación. No inventes montos.",
                _EntradaRegistrarFinanciador, _registrar_financiador, escribe=True),
    Herramienta("abrir_expediente", "Abre un expediente de procuración. Pide confirmación.",
                _EntradaAbrirExpediente, _abrir_expediente, escribe=True),
    Herramienta("registrar_avance", "Registra un avance en un expediente y, si se indica, lo cierra. Pide confirmación.",
                _EntradaAvance, _registrar_avance, escribe=True),
    Herramienta("guardar_evaluacion", "Evalúa con la matriz y guarda el resultado, opcionalmente en un expediente. "
                "Pide confirmación.", _EntradaGuardarEvaluacion, _guardar_evaluacion, escribe=True),
    Herramienta("generar_documento", "Genera un Word con el membrete (institucional, ficha, carta de intención, nota "
                "conceptual o reporte de evaluación). Lo que falte queda marcado. Pide confirmación.",
                _EntradaDocumento, _generar_documento, escribe=True),
):
    registrar(_h)
