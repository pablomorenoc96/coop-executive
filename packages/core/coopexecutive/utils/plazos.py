"""Días restantes a una fecha de cierre, con el mismo criterio de urgencia que la matriz."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from coopexecutive.utils.fechas import MESES, fecha_larga

DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_LARGA = re.compile(rf"^(\d{{1,2}}) de ({'|'.join(MESES)}) de(?:l)? (\d{{4}})$", re.IGNORECASE)
_NUMERICA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


@dataclass(frozen=True)
class Plazo:
    cierre: date
    dias: int
    texto: str

    @property
    def vencida(self) -> bool:
        return self.dias < 0

    @property
    def urgente(self) -> bool:
        return "URGENTE" in self.texto

    @property
    def dia_semana(self) -> str:
        return DIAS_SEMANA[self.cierre.weekday()]

    @property
    def fecha_larga(self) -> str:
        return f"{self.dia_semana} {fecha_larga(self.cierre)}"


def leer_fecha(texto: str) -> date:
    """Acepta AAAA-MM-DD, DD/MM/AAAA o «30 de octubre de 2026»."""
    limpio = texto.strip()
    try:
        return date.fromisoformat(limpio)
    except ValueError:
        pass
    m = _NUMERICA.match(limpio)
    if m:
        dia, mes, anio = (int(g) for g in m.groups())
        return date(anio, mes, dia)
    m = _LARGA.match(limpio)
    if m:
        return date(int(m.group(3)), MESES.index(m.group(2).lower()) + 1, int(m.group(1)))
    raise ValueError(f"«{texto}» no es una fecha. Use AAAA-MM-DD, DD/MM/AAAA o «30 de octubre de 2026».")


def plazo(cierre: date | str, hoy: date) -> Plazo:
    """Días naturales de `hoy` al cierre. Urgente con 13 días o menos, como en la matriz."""
    from coopexecutive.grant_tools.matrix import texto_plazo

    fecha = leer_fecha(cierre) if isinstance(cierre, str) else cierre
    dias = (fecha - hoy).days
    return Plazo(cierre=fecha, dias=dias, texto=texto_plazo(dias))
