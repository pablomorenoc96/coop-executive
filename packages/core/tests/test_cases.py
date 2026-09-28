from datetime import date

import pytest

from coopexecutive.crm import cases
from coopexecutive.crm.cases import ExpedienteDuplicado
from coopexecutive.grant_tools import matrix

HOY = date(2026, 9, 27)


def test_abrir_asigna_folio_titulo_y_monto_por_definir(entorno_aislado):
    e = cases.abrir("credito", "Fondo Rural", responsable="Titular", fecha_limite=date(2026, 11, 30), hoy=HOY)
    assert e.folio == "EXP-2026-0001"
    assert e.tipo == "Crédito"
    assert e.titulo == "Crédito - Fondo Rural"
    assert e.monto_texto == "MONTO POR DEFINIR"
    assert e.moneda is None
    assert e.abierto


def test_monto_con_moneda(entorno_aislado):
    e = cases.abrir("Beca", "Programa de Posgrado", monto=12000, moneda="eur", hoy=HOY)
    assert e.monto_texto == "12,000.00 EUR"


def test_titulo_se_limita_a_250(entorno_aislado):
    e = cases.abrir("Otro", "x" * 400, hoy=HOY)
    assert len(e.titulo) == cases.LARGO_TITULO


def test_un_abierto_por_entidad_y_tipo(entorno_aislado):
    cases.abrir("Convocatoria", "Fundación Ejemplo, A.C.", hoy=HOY)
    with pytest.raises(ExpedienteDuplicado) as exc:
        cases.abrir("convocatoria", "FUNDACION EJEMPLO AC", hoy=HOY)
    assert exc.value.folio == "EXP-2026-0001"
    assert "Convocatoria - Fundación Ejemplo, A.C." in str(exc.value)
    # Otro tipo con la misma entidad sí se permite.
    assert cases.abrir("Financiador", "Fundación Ejemplo, A.C.", hoy=HOY).folio == "EXP-2026-0002"


def test_cerrar_permite_abrir_de_nuevo(entorno_aislado):
    cases.abrir("Convocatoria", "Fondo Verde", hoy=HOY)
    cases.registrar_avance("EXP-2026-0001", "No se postuló", cerrar=True)
    assert not cases.obtener("EXP-2026-0001").abierto
    assert cases.abrir("Convocatoria", "Fondo Verde", hoy=HOY).folio == "EXP-2026-0002"
    with pytest.raises(ValueError, match="cerrado"):
        cases.registrar_avance("EXP-2026-0001", "Otro avance")


def test_avances_con_origen(entorno_aislado):
    cases.abrir("Crédito", "Fondo Rural", hoy=HOY)
    cases.registrar_avance("exp-2026-0001", "En pausa", pendientes="Revisión de requisitos",
                           siguiente_accion="Consultar al asesor", origen="dato publico verificado")
    historial = cases.avances("EXP-2026-0001")
    assert len(historial) == 1
    assert historial[0].origen == "Dato público verificado"
    assert historial[0].siguiente_accion == "Consultar al asesor"
    with pytest.raises(ValueError, match="Origen"):
        cases.registrar_avance("EXP-2026-0001", "x", origen="Rumor")
    with pytest.raises(ValueError, match="obligatorio"):
        cases.registrar_avance("EXP-2026-0001", "  ")
    with pytest.raises(ValueError, match="No existe"):
        cases.registrar_avance("EXP-2026-0099", "x")


def test_evaluaciones_vinculadas(entorno_aislado):
    cases.abrir("Convocatoria", "Fondo Verde", hoy=HOY)
    res = matrix.evaluar({"convocatoria": "Fondo Verde", "elegibilidad": "pendiente"}, hoy=HOY)
    matrix.guardar(res, "EXP-2026-0001")
    vinculadas = cases.evaluaciones("EXP-2026-0001")
    assert [v.decision for v in vinculadas] == ["VERIFICAR_ELEGIBILIDAD"]
    assert vinculadas[0].hash == res.hash


def test_listar_por_estado_y_responsable(entorno_aislado):
    cases.abrir("Beca", "Programa A", responsable="Ana", hoy=HOY)
    cases.abrir("Beca", "Programa B", responsable="Luis", hoy=HOY)
    cases.registrar_avance("EXP-2026-0002", "Concluido", cerrar=True)
    assert [e.folio for e in cases.listar()] == ["EXP-2026-0001"]
    assert [e.folio for e in cases.listar(estado="cerrados")] == ["EXP-2026-0002"]
    assert len(cases.listar(estado="todos")) == 2
    assert [e.folio for e in cases.listar(responsable="lu", estado="todos")] == ["EXP-2026-0002"]
    with pytest.raises(ValueError):
        cases.listar(estado="pausados")
