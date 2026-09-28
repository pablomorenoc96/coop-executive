"""Montos con moneda ISO 4217. Nunca convierte entre monedas: solo valida y formatea."""
from __future__ import annotations

# Códigos vigentes de ISO 4217 (lista A). Se excluyen metales, unidades de bonos y códigos de prueba.
CODIGOS_ISO_4217 = frozenset("""
AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD BND BOB BOV BRL BSD BTN BWP BYN BZD
CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP
GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR
KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN
MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD
SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX
USD USN UYI UYU UYW UZS VED VES VND VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG
""".split())

# Decimales distintos de 2 (unidad menor de ISO 4217).
_DECIMALES_ESPECIALES = {
    **dict.fromkeys(
        "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF".split(), 0
    ),
    **dict.fromkeys("BHD IQD JOD KWD LYD OMR TND".split(), 3),
    **dict.fromkeys("CLF UYW".split(), 4),
}


def validar_moneda(codigo: str) -> str:
    """Normaliza el código a mayúsculas y verifica que sea ISO 4217."""
    normalizado = (codigo or "").strip().upper()
    if normalizado not in CODIGOS_ISO_4217:
        raise ValueError(
            f"Moneda '{codigo}' no válida: use un código ISO 4217 de tres letras, por ejemplo MXN, USD o EUR."
        )
    return normalizado


def decimales(codigo: str) -> int:
    return _DECIMALES_ESPECIALES.get(validar_moneda(codigo), 2)


def formatear_monto(monto: float, moneda: str) -> str:
    """Devuelve «57,000.00 USD». El monto se expresa en la moneda indicada, sin conversión."""
    codigo = validar_moneda(moneda)
    return f"{monto:,.{decimales(codigo)}f} {codigo}"
