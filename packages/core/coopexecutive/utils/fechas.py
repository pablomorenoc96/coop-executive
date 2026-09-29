"""Fechas en la zona horaria de la organización, sin depender del locale del sistema."""
from __future__ import annotations

from datetime import UTC, date, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _zona(zona: str | None) -> tzinfo:
    if zona is None:
        from coopexecutive.config import get_settings

        zona = get_settings().user_timezone
    try:
        return ZoneInfo(zona)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def ahora_local(zona: str | None = None) -> datetime:
    """Fecha y hora actuales con zona horaria (por omisión, la de `USER_TIMEZONE`)."""
    return datetime.now(_zona(zona))


def hoy_local(zona: str | None = None) -> date:
    """Fecha de hoy en la zona de la organización, no en la del servidor."""
    return ahora_local(zona).date()


def local_desde_utc(texto: str, zona: str | None = None) -> datetime:
    """Convierte un `CURRENT_TIMESTAMP` de SQLite (UTC, sin zona) a la zona de la organización."""
    return datetime.fromisoformat(texto).replace(tzinfo=UTC).astimezone(_zona(zona))


def fecha_larga(fecha: date) -> str:
    """Devuelve «27 de septiembre de 2026»."""
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"
