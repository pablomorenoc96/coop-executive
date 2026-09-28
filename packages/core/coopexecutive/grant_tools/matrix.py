"""Matriz determinista de evaluación de oportunidades de financiamiento.

Sirve para convocatorias, becas, premios y créditos con los mismos ocho criterios.
El código decide (puntaje, plazo, precedencia y contrapunto); un modelo de lenguaje,
si se usa, solo propone puntajes con evidencia y redacta el análisis.

Reglas principales:
- Un criterio vacío queda pendiente; nunca cuenta como cero.
- Todo puntaje debe ser entero, estar dentro de su peso y llevar evidencia.
- Los puntos de Tiempos deben corresponder a los días que faltan para el cierre.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from coopexecutive.guardrails.marcadores import MONTO_POR_DEFINIR

# Clave -> (nombre, peso). El orden es el de presentación.
CRITERIOS: dict[str, tuple[str, int]] = {
    "alineacion": ("Alineación con la Misión", 20),
    "elegibilidad": ("Elegibilidad Geográfica y Legal", 10),
    "presupuesto": ("Rango Presupuestal Adecuado", 15),
    "tiempos": ("Viabilidad de Tiempos y Entrega", 10),
    "capacidad": ("Capacidad Técnica y Operativa", 15),
    "impacto": ("Potencial de Impacto Medible (ODS)", 15),
    "estrategico": ("Valor Estratégico a Largo Plazo", 10),
    "reporte": ("Requisitos de Auditoría y Reporte", 5),
}
PESOS: dict[str, int] = {clave: peso for clave, (_, peso) in CRITERIOS.items()}
PUNTAJE_MAXIMO = sum(PESOS.values())

UMBRAL_APLICAR = 80
UMBRAL_EXPLORAR = 60
UMBRAL_CONDICIONAL = 40

Decision = Literal[
    "ERROR_VALIDACION",
    "DESCARTAR",
    "VERIFICAR_ELEGIBILIDAD",
    "VERIFICAR_VIGENCIA",
    "ESCALAR_DIRECCION",
    "EVALUACION_INCOMPLETA",
    "APLICAR",
    "EXPLORAR",
    "CONDICIONAL",
]

SIGUIENTE_PASO: dict[str, str] = {
    "ERROR_VALIDACION": "Corregir los datos señalados y volver a evaluar.",
    "VERIFICAR_ELEGIBILIDAD": (
        "Confirmar en las bases oficiales los requisitos de elegibilidad "
        "(figura jurídica, territorio, antigüedad, documentación)."
    ),
    "VERIFICAR_VIGENCIA": "Confirmar en la fuente oficial que la oportunidad sigue abierta y su fecha de cierre.",
    "ESCALAR_DIRECCION": "Llevar la decisión a la dirección o al órgano de gobierno antes de avanzar.",
    "EVALUACION_INCOMPLETA": "Reunir la evidencia de los criterios pendientes y volver a evaluar.",
    "APLICAR": "Abrir o actualizar el expediente y preparar la solicitud.",
    "EXPLORAR": "Cerrar las brechas de los criterios más débiles (alianzas, datos, capacidad) antes de decidir.",
    "CONDICIONAL": "Postular solo si hay capacidad disponible y se resuelven las condiciones señaladas.",
}


class Calificacion(BaseModel):
    """Puntaje propuesto para un criterio. `puntos` vacío significa pendiente."""

    puntos: Any = None
    evidencia: str = ""


class EntradaMatriz(BaseModel):
    convocatoria: str = Field(min_length=1)
    financiador: str = ""
    tipo: Literal["convocatoria", "beca", "premio", "credito", "otro"] = "convocatoria"
    monto: str = ""
    criterios: dict[str, Calificacion] = Field(default_factory=dict)
    elegibilidad: Literal["confirmada", "excluida", "pendiente"] = "pendiente"
    vigencia: Literal["vigente", "vencida", "pendiente"] = "pendiente"
    tension: Literal["ninguna", "resuelta", "pendiente", "posicion_publica"] = "ninguna"
    tension_detalle: str = ""
    fecha_cierre: date | None = None
    dias_restantes: int | None = None
    evidencia_plazo: str = ""


class CriterioEvaluado(BaseModel):
    clave: str
    nombre: str
    peso: int
    puntos: int | None
    evidencia: str

    @property
    def pendiente(self) -> bool:
        return self.puntos is None


class ResultadoMatriz(BaseModel):
    convocatoria: str
    financiador: str = ""
    tipo: str = "convocatoria"
    monto: str = ""
    puntaje: int = 0
    puntaje_maximo_evaluado: int = 0
    criterios: list[CriterioEvaluado] = Field(default_factory=list)
    pendientes: list[str] = Field(default_factory=list)
    plazo: str = ""
    dias_restantes: int | None = None
    fecha_cierre: date | None = None
    decision: Decision
    motivo: str
    errores: list[str] = Field(default_factory=list)
    siguiente_paso: str = ""
    contrapunto: str = ""
    fecha_evaluacion: date
    hash: str = ""

    def calcular_hash(self) -> str:
        datos = self.model_dump(mode="json", exclude={"hash"})
        canonico = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()

    def to_markdown(self) -> str:
        lineas = [
            f"# Evaluación: {self.convocatoria}",
            "",
            f"- **Financiador:** {self.financiador or '[PENDIENTE: financiador]'}",
            f"- **Tipo:** {self.tipo}",
            f"- **Monto:** {self.monto or MONTO_POR_DEFINIR}",
            f"- **Plazo:** {self.plazo}",
            f"- **Fecha de evaluación:** {self.fecha_evaluacion.isoformat()}",
            "",
            f"## Decisión: {self.decision}",
            "",
            self.motivo,
        ]
        if self.errores:
            lineas += ["", "### Errores de validación", ""]
            lineas += [f"- {e}" for e in self.errores]
        lineas += [
            "",
            f"## Puntaje: {self.puntaje} de {self.puntaje_maximo_evaluado} evaluados "
            f"({PUNTAJE_MAXIMO} posibles)",
            "",
            "| Criterio | Peso | Puntos | Evidencia |",
            "| :--- | :---: | :---: | :--- |",
        ]
        for c in self.criterios:
            puntos = "pendiente" if c.puntos is None else str(c.puntos)
            evidencia = (c.evidencia or "-").replace("|", "/").replace("\n", " ")
            lineas.append(f"| {c.nombre} | {c.peso} | {puntos} | {evidencia} |")
        if self.pendientes:
            lineas += ["", "### Pendientes", ""]
            lineas += [f"- {p}" for p in self.pendientes]
        lineas += ["", "## Siguiente paso", "", self.siguiente_paso]
        if self.contrapunto:
            lineas += ["", "## Contrapunto", "", self.contrapunto]
        lineas += ["", f"Huella SHA-256: `{self.hash}`"]
        return "\n".join(lineas)


# --- Plazos -------------------------------------------------------------------


def banda_tiempos(dias: int | None, vencida: bool = False) -> tuple[int, int]:
    """Rango de puntos admitido para Tiempos según los días que faltan."""
    if vencida or (dias is not None and dias < 0):
        return (0, 2)
    if dias is None:
        return (0, 10)
    if dias < 7:
        return (0, 2)
    if dias <= 13:
        return (3, 5)
    if dias <= 28:
        return (6, 8)
    return (9, 10)


def texto_plazo(dias: int | None, vencida: bool = False) -> str:
    if vencida or (dias is not None and dias < 0):
        return "Vencida"
    if dias is None:
        return "Fecha de cierre por confirmar"
    if dias == 0:
        return "Cierra hoy (URGENTE)"
    if dias == 1:
        return "Falta 1 día (URGENTE)"
    if dias <= 13:
        return f"Faltan {dias} días (URGENTE)"
    return f"Faltan {dias} días"


# --- Validación ----------------------------------------------------------------

_ENTERO = re.compile(r"^[+-]?\d+$")


def _leer_puntos(valor: Any, nombre: str, peso: int) -> tuple[int | None, str | None]:
    """Devuelve (puntos, error). Vacío -> (None, None): pendiente, no cero."""
    if valor is None:
        return None, None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None, None
        if not _ENTERO.match(texto):
            return None, f"{nombre}: el puntaje «{texto}» no es un número entero."
        valor = int(texto)
    if isinstance(valor, bool):
        return None, f"{nombre}: el puntaje debe ser un número entero."
    if isinstance(valor, float):
        if not valor.is_integer():
            return None, f"{nombre}: el puntaje {valor} es decimal; use enteros."
        valor = int(valor)
    if not isinstance(valor, int):
        return None, f"{nombre}: el puntaje debe ser un número entero."
    if not 0 <= valor <= peso:
        return None, f"{nombre}: el puntaje {valor} está fuera del rango 0 a {peso}."
    return valor, None


def _error_de_esquema(datos: Any, exc: ValidationError, hoy: date) -> ResultadoMatriz:
    errores = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e["loc"]) or "entrada"
        errores.append(f"{campo}: {e['msg']}")
    titulo = datos.get("convocatoria", "") if isinstance(datos, dict) else ""
    return _sellar(
        ResultadoMatriz(
            convocatoria=str(titulo or "[PENDIENTE: nombre de la oportunidad]"),
            decision="ERROR_VALIDACION",
            motivo="La entrada no tiene el formato esperado.",
            errores=errores,
            siguiente_paso=SIGUIENTE_PASO["ERROR_VALIDACION"],
            fecha_evaluacion=hoy,
        )
    )


def _sellar(resultado: ResultadoMatriz) -> ResultadoMatriz:
    resultado.hash = resultado.calcular_hash()
    return resultado


# --- Evaluación ----------------------------------------------------------------


def _contrapunto(decision: str, calificados: list[CriterioEvaluado], vencida: bool, tension: str,
                 tension_detalle: str) -> str:
    if vencida:
        return (
            "La oportunidad ya cerró, pero muchas se abren cada año: conviene registrar al "
            "financiador y preparar desde ahora los requisitos para la siguiente edición."
        )
    if not calificados:
        return "Sin criterios calificados no hay base para sostener ninguna decisión."
    if decision == "DESCARTAR":
        fuerte = max(calificados, key=lambda c: (c.puntos / c.peso, c.peso))
        return (
            f"A favor de reconsiderarla: «{fuerte.nombre}» obtuvo {fuerte.puntos} de {fuerte.peso}"
            + (f" ({fuerte.evidencia})." if fuerte.evidencia else ".")
        )
    debil = min(calificados, key=lambda c: (c.puntos / c.peso, -c.peso))
    texto = (
        f"El punto más débil es «{debil.nombre}», con {debil.puntos} de {debil.peso}"
        + (f" ({debil.evidencia})." if debil.evidencia else ".")
    )
    if tension == "pendiente":
        detalle = f": {tension_detalle}" if tension_detalle else ""
        texto += f" Además hay una tensión sin resolver con la misión o las alianzas{detalle}."
    return texto


def evaluar(
    entrada: EntradaMatriz | dict[str, Any],
    *,
    hoy: date | None = None,
    rango_presupuesto_definido: bool = True,
) -> ResultadoMatriz:
    """Evalúa una oportunidad y devuelve un resultado sellado con su huella SHA-256."""
    if hoy is None:
        from coopexecutive.utils import hoy_local

        hoy = hoy_local()

    if not isinstance(entrada, EntradaMatriz):
        try:
            entrada = EntradaMatriz.model_validate(entrada)
        except ValidationError as exc:
            return _error_de_esquema(entrada, exc, hoy)

    errores: list[str] = []
    for clave in entrada.criterios:
        if clave not in CRITERIOS:
            errores.append(
                f"Criterio desconocido «{clave}». Válidos: {', '.join(CRITERIOS)}."
            )

    # Plazo
    dias = entrada.dias_restantes
    if entrada.fecha_cierre is not None:
        calculados = (entrada.fecha_cierre - hoy).days
        if dias is not None and dias != calculados:
            errores.append(
                f"Plazo: la fecha de cierre {entrada.fecha_cierre.isoformat()} implica "
                f"{calculados} días, no {dias}."
            )
        dias = calculados
    if (entrada.fecha_cierre is not None or entrada.dias_restantes is not None) and not entrada.evidencia_plazo.strip():
        errores.append("Plazo: falta la evidencia de la fecha de cierre (fuente o cita de las bases).")
    vencida = entrada.vigencia == "vencida" or (dias is not None and dias < 0)

    # Criterios
    evaluados: list[CriterioEvaluado] = []
    pendientes: list[str] = []
    for clave, (nombre, peso) in CRITERIOS.items():
        cal = entrada.criterios.get(clave, Calificacion())
        evidencia = cal.evidencia.strip()
        if clave == "presupuesto" and not rango_presupuesto_definido:
            evaluados.append(CriterioEvaluado(clave=clave, nombre=nombre, peso=peso, puntos=None,
                                              evidencia=MONTO_POR_DEFINIR))
            pendientes.append(f"{nombre}: el perfil no define el rango de presupuesto ({MONTO_POR_DEFINIR}).")
            continue
        puntos, error = _leer_puntos(cal.puntos, nombre, peso)
        if error:
            errores.append(error)
        elif puntos is not None and not evidencia:
            errores.append(f"{nombre}: el puntaje {puntos} no tiene evidencia.")
        elif puntos is not None and clave == "tiempos":
            minimo, maximo = banda_tiempos(dias, vencida)
            if not minimo <= puntos <= maximo:
                errores.append(
                    f"{nombre}: con el plazo «{texto_plazo(dias, vencida)}» corresponden "
                    f"{minimo} a {maximo} puntos, no {puntos}."
                )
        evaluados.append(CriterioEvaluado(clave=clave, nombre=nombre, peso=peso, puntos=puntos,
                                          evidencia=evidencia))
        if puntos is None and not error:
            pendientes.append(f"{nombre}: sin calificar.")

    calificados = [c for c in evaluados if c.puntos is not None]
    puntaje = sum(c.puntos for c in calificados)  # type: ignore[misc]
    maximo_evaluado = sum(c.peso for c in calificados)

    decision, motivo = _decidir(entrada, errores, vencida, puntaje, len(calificados))
    siguiente = SIGUIENTE_PASO.get(decision, "")
    if decision == "DESCARTAR":
        if entrada.elegibilidad == "excluida":
            siguiente = "Archivar la oportunidad: la organización no cumple un requisito de elegibilidad."
        elif vencida:
            siguiente = "Registrar al financiador y vigilar la reapertura de la oportunidad."
        else:
            siguiente = "No postular y documentar el motivo para futuras oportunidades."
    elif decision == "EVALUACION_INCOMPLETA":
        faltan = [c.nombre for c in evaluados if c.puntos is None]
        siguiente = f"{siguiente} Faltan: {', '.join(faltan)}."

    contrapunto = ""
    if decision in ("APLICAR", "EXPLORAR", "CONDICIONAL", "DESCARTAR", "ESCALAR_DIRECCION"):
        contrapunto = _contrapunto(decision, calificados, vencida, entrada.tension, entrada.tension_detalle)

    return _sellar(
        ResultadoMatriz(
            convocatoria=entrada.convocatoria,
            financiador=entrada.financiador,
            tipo=entrada.tipo,
            monto=entrada.monto,
            puntaje=puntaje,
            puntaje_maximo_evaluado=maximo_evaluado,
            criterios=evaluados,
            pendientes=pendientes,
            plazo=texto_plazo(dias, vencida),
            dias_restantes=dias,
            fecha_cierre=entrada.fecha_cierre,
            decision=decision,
            motivo=motivo,
            errores=errores,
            siguiente_paso=siguiente,
            contrapunto=contrapunto,
            fecha_evaluacion=hoy,
        )
    )


def _decidir(entrada: EntradaMatriz, errores: list[str], vencida: bool, puntaje: int,
             num_calificados: int) -> tuple[str, str]:
    """Aplica la primera regla que corresponda, en orden de precedencia."""
    if errores:
        return "ERROR_VALIDACION", "Hay datos que no cumplen las reglas de la matriz."
    if entrada.elegibilidad == "excluida":
        return "DESCARTAR", "La organización queda excluida por un requisito de elegibilidad."
    if vencida:
        return "DESCARTAR", "La fecha de cierre ya pasó."
    if entrada.elegibilidad == "pendiente":
        return "VERIFICAR_ELEGIBILIDAD", "La elegibilidad no está confirmada en las bases oficiales."
    if entrada.vigencia == "pendiente":
        return "VERIFICAR_VIGENCIA", "No está confirmado que la oportunidad siga abierta."
    if entrada.tension == "posicion_publica":
        return (
            "ESCALAR_DIRECCION",
            "La oportunidad choca con una posición pública de la organización; decide la dirección.",
        )
    if num_calificados < len(CRITERIOS):
        return (
            "EVALUACION_INCOMPLETA",
            f"Solo hay {num_calificados} de {len(CRITERIOS)} criterios calificados; "
            "un criterio pendiente no cuenta como cero.",
        )
    if puntaje >= UMBRAL_APLICAR:
        decision, motivo = "APLICAR", f"Puntaje de {puntaje}: alta compatibilidad."
    elif puntaje >= UMBRAL_EXPLORAR:
        decision, motivo = "EXPLORAR", f"Puntaje de {puntaje}: compatible, con brechas por cerrar."
    elif puntaje >= UMBRAL_CONDICIONAL:
        decision, motivo = "CONDICIONAL", f"Puntaje de {puntaje}: compatibilidad limitada."
    else:
        return "DESCARTAR", f"Puntaje de {puntaje}: por debajo del mínimo de {UMBRAL_CONDICIONAL}."
    if entrada.tension == "pendiente" and decision in ("APLICAR", "EXPLORAR"):
        return "CONDICIONAL", f"{motivo} Baja a CONDICIONAL por una tensión sin resolver."
    return decision, motivo


# --- Persistencia --------------------------------------------------------------


def guardar(resultado: ResultadoMatriz, expediente: str | None = None) -> int:
    """Guarda el resultado en `grant_evaluations` y devuelve su id."""
    from coopexecutive.memory.episodic import get_db_conn, initialize_db

    initialize_db()
    with get_db_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO grant_evaluations
                (call_title, donor_agency, total_score, recommendation, report_md,
                 resultado_json, expediente_folio, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resultado.convocatoria,
                resultado.financiador,
                resultado.puntaje,
                resultado.decision,
                resultado.to_markdown(),
                resultado.model_dump_json(),
                expediente,
                resultado.hash,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
