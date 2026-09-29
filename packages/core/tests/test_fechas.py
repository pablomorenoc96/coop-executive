from datetime import UTC, date, datetime

from coopexecutive.utils import fechas
from coopexecutive.utils.fechas import ahora_local, fecha_larga, hoy_local, local_desde_utc


def test_fecha_larga_sin_locale():
    assert fecha_larga(date(2026, 9, 27)) == "27 de septiembre de 2026"
    assert fecha_larga(date(2027, 1, 1)) == "1 de enero de 2027"


def test_ahora_local_tiene_zona():
    ahora = ahora_local("America/Mexico_City")
    assert ahora.tzinfo is not None
    assert ahora.utcoffset().total_seconds() == -6 * 3600


def test_zona_invalida_usa_utc():
    assert ahora_local("Zona/Inexistente").utcoffset().total_seconds() == 0


def test_zona_por_omision_sale_de_la_configuracion(entorno_aislado):
    assert str(ahora_local().tzinfo) == "America/Mexico_City"


def test_local_desde_utc_de_sqlite():
    local = local_desde_utc("2026-09-28 00:11:40", "America/Mexico_City")
    assert local.strftime("%Y-%m-%d %H:%M") == "2026-09-27 18:11"


def test_hoy_local_depende_de_la_zona(monkeypatch):
    # Las 03:00 UTC del 28/9 todavía son el 27/9 en la Ciudad de México.
    fijo = datetime(2026, 9, 28, 3, 0, tzinfo=UTC)

    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return fijo.astimezone(tz)

    monkeypatch.setattr(fechas, "datetime", Reloj)
    assert hoy_local("America/Mexico_City") == date(2026, 9, 27)
    assert hoy_local("UTC") == date(2026, 9, 28)
