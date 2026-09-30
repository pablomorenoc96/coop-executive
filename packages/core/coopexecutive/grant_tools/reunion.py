"""Preparación de una reunión con un financiador o posible aliado.

El modelo propone un JSON; aquí se valida y se ajustan las etiquetas de origen:
- «DATO PÚBLICO VERIFICADO» solo vale si la fuente es una de las páginas leídas y la
  cita aparece en ellas. Si no, baja a «NO VERIFICADO».
- «DATO INSTITUCIONAL» solo vale si el texto aparece en el perfil de la organización.
  Si no, baja a «INFERENCIA ESTRATÉGICA».
- Una etiqueta desconocida se vuelve «NO VERIFICADO».
La ficha de la propia organización no la redacta el modelo: sale del perfil.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from coopexecutive.documents.contenido import DocumentoPlano, Lista, Parrafo, Tabla, Titulo
from coopexecutive.guardrails.marcadores import ETIQUETAS, pendiente
from coopexecutive.guardrails.sensibles import limpiar_datos_sensibles
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.memory.desde_sitio import Pagina
from coopexecutive.utils.texto import normalizar

PUBLICO, INSTITUCIONAL, NO_VERIFICADO, INFERENCIA = (
    "DATO PÚBLICO VERIFICADO", "DATO INSTITUCIONAL", "NO VERIFICADO", "INFERENCIA ESTRATÉGICA",
)
CARACTERES_POR_PAGINA = 5_000


class Dato(BaseModel):
    texto: str
    etiqueta: str = NO_VERIFICADO
    fuente: str = ""
    cita: str = ""

    @field_validator("texto", "fuente", "cita", mode="before")
    @classmethod
    def _limpio(cls, v: object) -> str:
        return limpiar_datos_sensibles(str(v or "")).strip()

    @field_validator("etiqueta", mode="before")
    @classmethod
    def _etiqueta(cls, v: object) -> str:
        texto = str(v or "").strip().strip("[]").upper()
        return texto if texto in ETIQUETAS else NO_VERIFICADO


class Preparacion(BaseModel):
    perfil_publico: list[Dato] = Field(default_factory=list)
    puntos_en_comun: list[Dato] = Field(default_factory=list)
    riesgos: list[Dato] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    preguntas: list[str] = Field(default_factory=list)
    siguiente_paso: str = ""

    @field_validator("agenda", "preguntas", mode="before")
    @classmethod
    def _textos(cls, v: object) -> list[str]:
        return [limpiar_datos_sensibles(str(x)).strip() for x in (v or []) if str(x).strip()]

    @field_validator("siguiente_paso", mode="before")
    @classmethod
    def _paso(cls, v: object) -> str:
        return limpiar_datos_sensibles(str(v or "")).strip()


def instrucciones(entidad: str, objetivo: str, contexto: str, paginas: list[Pagina]) -> str:
    textos = "\n\n".join(
        f"### Página: {p.url}\n{p.texto[:CARACTERES_POR_PAGINA]}" for p in paginas
    ) or "(No se leyó ninguna página pública.)"
    etiquetas = ", ".join(ETIQUETAS)
    return (
        f"Prepara una reunión con «{entidad}». Objetivo de la reunión: {objetivo or 'por definir'}.\n\n"
        "Responde SOLO con un objeto JSON con esta forma:\n"
        '{"perfil_publico": [{"texto": "...", "etiqueta": "...", "fuente": "URL", "cita": "..."}],\n'
        ' "puntos_en_comun": [{"texto": "...", "etiqueta": "...", "fuente": "", "cita": ""}],\n'
        ' "riesgos": [{"texto": "...", "etiqueta": "...", "fuente": "", "cita": ""}],\n'
        ' "agenda": ["..."], "preguntas": ["..."], "siguiente_paso": "..."}\n\n'
        "Reglas:\n"
        f"- «etiqueta» es una de: {etiquetas}.\n"
        "- perfil_publico: solo lo que dicen las páginas de abajo, con la URL en «fuente» y una cita "
        "textual breve en «cita». Si no hay páginas, deja la lista vacía.\n"
        "- puntos_en_comun y riesgos cruzan el perfil de la organización con lo público; marca como "
        "INFERENCIA ESTRATÉGICA lo que sea tu interpretación.\n"
        "- No inventes montos, fechas, nombres de personas ni alianzas. Lo que falte, como pregunta.\n"
        "- agenda: de 4 a 6 puntos. preguntas: de 4 a 8, concretas.\n"
        "- No escribas cuentas, CLABE, tarjetas, RFC, CURP, correos ni teléfonos.\n\n"
        f"Contexto interno:\n{contexto or '(sin contexto adicional)'}\n\n"
        f"Páginas públicas leídas:\n{textos}"
    )


def _en_paginas(dato: Dato, paginas: list[Pagina]) -> bool:
    cita = normalizar(dato.cita)
    if len(cita) < 3:
        return False
    return any(
        p.url.rstrip("/") == dato.fuente.rstrip("/") and cita in normalizar(p.texto) for p in paginas
    )


def validar(prep: Preparacion, paginas: list[Pagina], perfil_texto: str) -> Preparacion:
    """Ajusta las etiquetas según la evidencia disponible."""
    perfil_n = normalizar(perfil_texto)

    def ajustar(dato: Dato) -> Dato:
        etiqueta = dato.etiqueta
        if etiqueta == PUBLICO and not _en_paginas(dato, paginas):
            etiqueta = NO_VERIFICADO
        if etiqueta == INSTITUCIONAL and normalizar(dato.texto) not in perfil_n:
            etiqueta = INFERENCIA
        return dato.model_copy(update={"etiqueta": etiqueta})

    publicos = [ajustar(d) for d in prep.perfil_publico if d.texto]
    # En el perfil público solo queda lo que tiene respaldo en las páginas.
    publicos = [d for d in publicos if d.etiqueta == PUBLICO]
    return prep.model_copy(update={
        "perfil_publico": publicos,
        "puntos_en_comun": [ajustar(d) for d in prep.puntos_en_comun if d.texto],
        "riesgos": [ajustar(d) for d in prep.riesgos if d.texto],
    })


def _linea(d: Dato) -> str:
    fuente = f" ({d.fuente})" if d.fuente else ""
    return f"[{d.etiqueta}] {d.texto}{fuente}"


def a_plano(
    prep: Preparacion, entidad: str, objetivo: str, perfil: CoopProfile, paginas: list[Pagina]
) -> DocumentoPlano:
    """Documento interno de preparación. La ficha propia sale del perfil, no del modelo."""
    doc = DocumentoPlano(tipo="preparacion_reunion", titulo=f"Preparación de reunión: {entidad}",
                         subtitulo=objetivo or pendiente("objetivo de la reunión"))
    b = doc.bloques
    b.append(Titulo(f"Perfil público de {entidad}"))
    if prep.perfil_publico:
        b.append(Lista([_linea(d) for d in prep.perfil_publico]))
    elif paginas:
        b.append(Parrafo("Las páginas leídas no respaldan ningún dato; confirme el perfil en la reunión."))
    else:
        b.append(Parrafo("No se leyó un sitio público. Use --sitio para incluir datos verificados."))
    p = perfil.procuracion
    filas = [
        ["Organización", perfil.name],
        ["Misión", perfil.mission or pendiente("misión")],
        ["Ejes de trabajo", "; ".join(perfil.focus_areas) or pendiente("ejes de trabajo")],
        ["Programas", "; ".join(p.programas) if p and p.programas else pendiente("programas")],
        ["Resultados", "; ".join(p.metricas_impacto) if p and p.metricas_impacto else pendiente("resultados verificables")],
    ]
    b += [Titulo("Nuestra organización [DATO INSTITUCIONAL]"), Tabla(["Dato", "Valor"], filas, [1, 3])]
    if prep.puntos_en_comun:
        b += [Titulo("Puntos en común"), Lista([_linea(d) for d in prep.puntos_en_comun])]
    if prep.riesgos:
        b += [Titulo("Riesgos y temas sensibles"), Lista([_linea(d) for d in prep.riesgos])]
    b += [Titulo("Agenda propuesta"), Lista(prep.agenda or [pendiente("agenda")])]
    b += [Titulo("Preguntas para la reunión"), Lista(prep.preguntas or [pendiente("preguntas")])]
    b += [Titulo("Siguiente paso"), Parrafo(prep.siguiente_paso or pendiente("siguiente paso"))]
    if paginas:
        b += [Titulo("Páginas consultadas"), Lista([pg.url for pg in paginas])]
    return doc
