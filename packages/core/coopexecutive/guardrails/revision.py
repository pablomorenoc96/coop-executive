"""Revisión posterior de respuestas del modelo de lenguaje.

Señala montos y fechas que no aparecen en el contexto (entrada, perfil o evidencia),
emojis, respuestas demasiado largas, recomendaciones sin contrapunto y frases que
afirman haber guardado algo cuando no se ejecutó ninguna acción. Las cuentas
bancarias y los números de tarjeta se censuran siempre, también sin `estricto`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from coopexecutive.guardrails.marcadores import LEYENDA_BORRADOR, MONTO_POR_DEFINIR, pendiente
from coopexecutive.guardrails.sensibles import censurar_datos_bancarios
from coopexecutive.utils.fechas import MESES

LIMITE_PALABRAS = 900

_MONEDAS = r"(?:MXN|USD|EUR|CAD|GBP|pesos|d[oó]lares|euros)"
_NUMERO = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_MONTO = re.compile(
    rf"(?:\$\s?(?P<a>{_NUMERO})(?:\s?(?:mil(?:lones)?|MDP))?(?:\s?{_MONEDAS})?)"
    rf"|(?:(?P<b>{_NUMERO})\s?(?:mil(?:lones)?\s(?:de\s)?)?{_MONEDAS})",
    re.IGNORECASE,
)
_MESES_RE = "|".join(MESES)
_FECHA_LARGA = re.compile(rf"\b(\d{{1,2}}) de ({_MESES_RE})(?: de(?:l)? (\d{{4}}))?\b", re.IGNORECASE)
_FECHA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_FECHA_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F02F\U0001F1E6-\U0001F1FF⭐⭕✅❌]"
)
_RECOMENDACION = re.compile(
    r"\b(APLICAR|EXPLORAR|CONDICIONAL|DESCARTAR|recomiendo|recomendaci[oó]n)\b", re.IGNORECASE
)
_AFIRMA_ACCION = re.compile(
    r"\b(?:se\s+(?:ha|han)\s+|he\s+|ya\s+(?:fue|est[aá]|qued[oó])\s+|qued[oó]\s+|fue\s+)"
    r"(?:guardad|registrad|enviad|cread|actualizad|publicad)\w*",
    re.IGNORECASE,
)


@dataclass
class Revision:
    texto: str
    observaciones: list[str] = field(default_factory=list)

    @property
    def limpia(self) -> bool:
        return not self.observaciones


def _cifra(texto: str) -> str:
    """Normaliza una cifra: sin separadores de miles ni decimales en cero."""
    limpio = texto.replace(",", "")
    if "." in limpio:
        limpio = limpio.rstrip("0").rstrip(".")
    return limpio


def _cifras_en(texto: str) -> set[str]:
    return {_cifra(n) for n in re.findall(_NUMERO, texto)}


def _fechas_en(texto: str) -> set[tuple[int | None, int, int]]:
    """Fechas como (año o None, mes, día)."""
    fechas: set[tuple[int | None, int, int]] = set()
    for dia, mes, anio in _FECHA_LARGA.findall(texto):
        fechas.add((int(anio) if anio else None, MESES.index(mes.lower()) + 1, int(dia)))
    for anio, mes, dia in _FECHA_ISO.findall(texto):
        fechas.add((int(anio), int(mes), int(dia)))
    for dia, mes, anio in _FECHA_NUM.findall(texto):
        fechas.add((int(anio), int(mes), int(dia)))
    return fechas


def _fecha_conocida(fecha: tuple[int | None, int, int], conocidas: set[tuple[int | None, int, int]]) -> bool:
    anio, mes, dia = fecha
    for otra_anio, otro_mes, otro_dia in conocidas:
        if (mes, dia) == (otro_mes, otro_dia) and (anio is None or otra_anio is None or anio == otra_anio):
            return True
    return False


def revisar_respuesta(
    texto: str,
    contexto: str = "",
    *,
    estricto: bool = False,
    acciones_ejecutadas: bool = False,
    hoy: date | None = None,
) -> Revision:
    """Revisa una respuesta contra su contexto.

    `contexto` reúne la pregunta, el perfil y la evidencia disponibles. Con
    `estricto`, los montos y fechas sin respaldo se sustituyen por marcadores.
    La fecha de hoy siempre se considera conocida.
    """
    observaciones: list[str] = []
    texto, censurados = censurar_datos_bancarios(texto)
    if censurados:
        observaciones.append(f"Se omitieron {censurados} dato(s) bancario(s): cuentas o tarjetas no se muestran.")
    cifras = _cifras_en(contexto)
    fechas = _fechas_en(contexto)
    if hoy is not None:
        fechas.add((hoy.year, hoy.month, hoy.day))

    def _monto(m: re.Match[str]) -> str:
        cifra = _cifra(m.group("a") or m.group("b"))
        if cifra in cifras:
            return m.group(0)
        observaciones.append(f"Monto sin respaldo en el contexto: «{m.group(0).strip()}».")
        return MONTO_POR_DEFINIR if estricto else m.group(0)

    texto = _MONTO.sub(_monto, texto)

    def _revisar_fecha(m: re.Match[str], fecha: tuple[int | None, int, int]) -> str:
        if _fecha_conocida(fecha, fechas):
            return m.group(0)
        observaciones.append(f"Fecha sin respaldo en el contexto: «{m.group(0)}».")
        return pendiente("fecha") if estricto else m.group(0)

    texto = _FECHA_LARGA.sub(
        lambda m: _revisar_fecha(
            m, (int(m.group(3)) if m.group(3) else None, MESES.index(m.group(2).lower()) + 1, int(m.group(1)))
        ),
        texto,
    )
    texto = _FECHA_ISO.sub(
        lambda m: _revisar_fecha(m, (int(m.group(1)), int(m.group(2)), int(m.group(3)))), texto
    )
    texto = _FECHA_NUM.sub(
        lambda m: _revisar_fecha(m, (int(m.group(3)), int(m.group(2)), int(m.group(1)))), texto
    )

    if _EMOJI.search(texto):
        observaciones.append("La respuesta contiene emojis.")
    palabras = len(texto.split())
    if palabras > LIMITE_PALABRAS:
        observaciones.append(f"La respuesta tiene {palabras} palabras; el límite es {LIMITE_PALABRAS}.")
    if _RECOMENDACION.search(texto) and "contrapunto" not in texto.lower():
        observaciones.append("Hay una recomendación sin CONTRAPUNTO.")
    if not acciones_ejecutadas:
        afirmacion = _AFIRMA_ACCION.search(texto)
        if afirmacion:
            observaciones.append(
                f"Afirma una acción que no se ejecutó: «{afirmacion.group(0)}». "
                "El asistente solo redacta; registrar o enviar lo hace una persona o un comando."
            )
    return Revision(texto=texto, observaciones=observaciones)


def agregar_leyenda(texto: str) -> str:
    """Añade la leyenda de borrador al final de una respuesta de chat (nunca a archivos)."""
    texto = texto.rstrip()
    if texto.endswith(LEYENDA_BORRADOR):
        return texto
    return f"{texto}\n\n{LEYENDA_BORRADOR}"
