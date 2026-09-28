from datetime import date

import pytest

from coopexecutive.crm import funders
from coopexecutive.crm.funders import FinanciadorDuplicado

HOY = date(2026, 9, 27)


def alta(organizacion="Fundación Ejemplo, A.C.", **extra):
    datos = dict(proyecto="Energía comunitaria", tipo="Fundación", canal="Correo", hoy=HOY)
    datos.update(extra)
    return funders.registrar(organizacion, **datos)


def test_registrar_asigna_folio_y_estatus_inicial(entorno_aislado):
    f = alta(moneda="usd", monto_solicitado=57000)
    assert f.folio == "FIN-2026-0001"
    assert f.estatus == "Prospecto"
    assert f.moneda == "USD"
    assert f.monto(f.monto_solicitado) == "57,000.00 USD"
    assert f.monto(f.monto_recibido) == "MONTO POR DEFINIR"
    assert alta("Otra Fundación").folio == "FIN-2026-0002"


@pytest.mark.parametrize("nombre", ["FUNDACION EJEMPLO AC", "fundación ejemplo, a.c.", "Fundacion  Ejemplo A.C"])
def test_duplicado_por_nombre_normalizado(entorno_aislado, nombre):
    alta()
    with pytest.raises(FinanciadorDuplicado) as exc:
        alta(nombre)
    assert exc.value.folio == "FIN-2026-0001"


def test_catalogos_sin_acentos_ni_mayusculas(entorno_aislado):
    f = alta(tipo="institucion financiera", canal="CONVOCATORIA PUBLICA")
    assert f.tipo == "Institución financiera"
    assert f.canal == "Convocatoria pública"
    with pytest.raises(ValueError, match="Opciones"):
        alta("Otra", tipo="Banco")


@pytest.mark.parametrize(
    "proyecto",
    ["Energía por $50,000", "Taller 100 mil pesos", "Cierre 15/10/2026", "Entrega 2026-10-15", "Inicia 3 de octubre"],
)
def test_proyecto_sin_montos_ni_fechas(entorno_aislado, proyecto):
    with pytest.raises(ValueError, match="propios campos"):
        alta(proyecto=proyecto)


def test_validaciones_basicas(entorno_aislado):
    with pytest.raises(ValueError, match="organización es obligatoria"):
        alta("  ")
    with pytest.raises(ValueError, match="negativo"):
        alta(monto_solicitado=-1)
    with pytest.raises(ValueError, match="anterior a hoy"):
        alta(seguimiento=date(2026, 9, 26))
    with pytest.raises(ValueError):
        alta(moneda="PESOS")


def test_buscar_por_folio_texto_y_recientes(entorno_aislado):
    alta()
    alta("Banco Rural", tipo="Institución financiera", proyecto="Crédito para equipo")
    assert [f.folio for f in funders.buscar("FIN-2026-0002")] == ["FIN-2026-0002"]
    assert [f.organizacion for f in funders.buscar("fundacion")] == ["Fundación Ejemplo, A.C."]
    assert [f.organizacion for f in funders.buscar("equipo")] == ["Banco Rural"]
    assert [f.folio for f in funders.buscar()] == ["FIN-2026-0002", "FIN-2026-0001"]
    assert funders.buscar("inexistente") == []


def test_actualizar(entorno_aislado):
    alta()
    f = funders.actualizar("fin-2026-0001", estatus="en negociacion", monto_comprometido=20000,
                           seguimiento=date(2026, 10, 1), hoy=HOY)
    assert f.estatus == "En negociación"
    assert f.monto_comprometido == 20000
    assert f.seguimiento == date(2026, 10, 1)
    with pytest.raises(ValueError, match="No existe"):
        funders.actualizar("FIN-2026-0099", estatus="Contactado")
    with pytest.raises(ValueError):
        funders.actualizar("FIN-2026-0001", estatus="Ganado")
