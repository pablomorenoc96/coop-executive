"""Detección y censura de datos que nunca deben guardarse ni mostrarse.

Cuentas bancarias (CLABE, IBAN), números de tarjeta, RFC y CURP. Para textos
leídos de un sitio web también se quitan correos de servicios gratuitos y
teléfonos, que suelen ser de personas y no de la organización.
"""
from __future__ import annotations

import re

DATO_BANCARIO_OMITIDO = "[DATO BANCARIO OMITIDO]"
IDENTIFICADOR_OMITIDO = "[IDENTIFICADOR OMITIDO]"
CONTACTO_OMITIDO = "[CONTACTO OMITIDO]"

# Corridas de 13 a 19 dígitos, con espacios o guiones opcionales entre ellos.
_DIGITOS = re.compile(r"(?<![\w.,])\d(?:[ -]?\d){12,18}(?![\w])")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
# RFC de persona física o moral y CURP.
IDENTIFICADOR = re.compile(
    r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b|\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.IGNORECASE
)
_CORREO_GRATUITO = re.compile(
    r"\b[\w.+-]+@(?:gmail|hotmail|outlook|live|yahoo|icloud|protonmail|proton|aol)\.[a-z.]{2,6}\b",
    re.IGNORECASE,
)
_TELEFONO = re.compile(
    r"(?<![\w])(?:\+?\d{1,3}[ .-]?)?(?:\(\d{2,3}\)|\d{2,3})[ .-]?\d{3,4}[ .-]?\d{4}(?![\w])"
)


def _luhn(digitos: str) -> bool:
    total = 0
    for i, c in enumerate(reversed(digitos)):
        n = int(c)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def _iban_valido(texto: str) -> bool:
    compacto = texto.replace(" ", "").upper()
    if not 15 <= len(compacto) <= 34:
        return False
    reordenado = compacto[4:] + compacto[:4]
    numero = "".join(str(int(c, 36)) for c in reordenado)
    return int(numero) % 97 == 1


def _es_cuenta(digitos: str) -> bool:
    """CLABE (18 dígitos) o tarjeta (13 a 19 dígitos que pasan la prueba de Luhn)."""
    return len(digitos) == 18 or _luhn(digitos)


def contiene_dato_bancario(texto: str) -> bool:
    if any(_es_cuenta(re.sub(r"\D", "", m.group(0))) for m in _DIGITOS.finditer(texto)):
        return True
    return any(_iban_valido(m.group(0)) for m in _IBAN.finditer(texto))


def censurar_datos_bancarios(texto: str) -> tuple[str, int]:
    """Sustituye CLABE, IBAN y tarjetas por un marcador. Devuelve el texto y cuántos quitó."""
    cuenta = 0

    def _digitos(m: re.Match[str]) -> str:
        nonlocal cuenta
        if _es_cuenta(re.sub(r"\D", "", m.group(0))):
            cuenta += 1
            return DATO_BANCARIO_OMITIDO
        return m.group(0)

    def _iban(m: re.Match[str]) -> str:
        nonlocal cuenta
        if _iban_valido(m.group(0)):
            cuenta += 1
            return DATO_BANCARIO_OMITIDO
        return m.group(0)

    texto = _DIGITOS.sub(_digitos, texto)
    texto = _IBAN.sub(_iban, texto)
    return texto, cuenta


def limpiar_datos_sensibles(texto: str) -> str:
    """Censura cuentas, identificadores fiscales, correos de servicios gratuitos y teléfonos."""
    texto, _ = censurar_datos_bancarios(texto)
    texto = IDENTIFICADOR.sub(IDENTIFICADOR_OMITIDO, texto)
    texto = _CORREO_GRATUITO.sub(CONTACTO_OMITIDO, texto)
    return _TELEFONO.sub(CONTACTO_OMITIDO, texto)
