"""Registro de herramientas: esquemas, confirmación de escrituras, errores y bitácora."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest

from coopexecutive import bitacora, herramientas
from coopexecutive.utils.fechas import hoy_local

HOY = hoy_local("America/Mexico_City")
PUNTOS = {"alineacion": 18, "elegibilidad": 9, "presupuesto": 13, "tiempos": 9,
          "capacidad": 13, "impacto": 13, "estrategico": 8, "reporte": 4}


def entrada_matriz(**extra) -> dict:
    datos = {
        "convocatoria": "Fondo de Energía Comunitaria",
        "financiador": "Fundación Ejemplo",
        "elegibilidad": "confirmada",
        "vigencia": "vigente",
        "fecha_cierre": (HOY + timedelta(days=40)).isoformat(),
        "evidencia_plazo": "Bases, numeral 5.",
        "criterios": {c: {"puntos": p, "evidencia": f"Bases sobre {c}."} for c, p in PUNTOS.items()},
    }
    datos.update(extra)
    return datos


def correr(nombre: str, argumentos: dict | None = None, *, autorizada: bool = False) -> herramientas.Resultado:
    return herramientas.ejecutar(nombre, argumentos or {}, canal="agente", autorizada=autorizada)


def _sin_ref(nodo) -> bool:
    if isinstance(nodo, dict):
        return "$ref" not in nodo and "$defs" not in nodo and all(_sin_ref(v) for v in nodo.values())
    if isinstance(nodo, list):
        return all(_sin_ref(v) for v in nodo)
    return True


def test_catalogo_completo_y_esquemas_sin_referencias():
    nombres = {h.nombre for h in herramientas.todas()}
    assert {"fecha_y_plazos", "evaluar_oportunidad", "registrar_financiador", "generar_documento"} <= nombres
    for h in herramientas.todas():
        esquema = h.esquema()
        assert esquema["type"] == "object"
        assert _sin_ref(esquema), h.nombre
        json.dumps(h.para_modelo())
    escritura = {h.nombre for h in herramientas.todas() if h.escribe}
    assert escritura == {"registrar_financiador", "abrir_expediente", "registrar_avance", "guardar_evaluacion",
                         "generar_documento"}
    assert not any(h.escribe for h in herramientas.todas(solo_lectura=True))


def test_criterios_de_la_matriz_en_la_descripcion():
    descripcion = herramientas.obtener("evaluar_oportunidad").descripcion
    for clave in PUNTOS:
        assert clave in descripcion


def test_fecha_y_plazos(entorno_aislado):
    cierre = (HOY + timedelta(days=5)).isoformat()
    r = correr("fecha_y_plazos", {"cierres": [cierre]})
    assert r.ok
    assert r.datos["hoy"] == HOY.isoformat()
    assert r.datos["plazos"][0]["dias"] == 5
    assert r.datos["plazos"][0]["urgente"] is True


def test_escritura_sin_autorizacion_queda_denegada_y_no_escribe(entorno_aislado):
    r = correr("registrar_financiador", {"organizacion": "Fundación Uno", "proyecto": "Techos solares",
                                         "tipo": "Fundación", "canal": "Correo"})
    assert r.estado == "denegada"
    assert "no se ejecutó" in r.para_modelo()
    assert correr("buscar_financiadores", {"texto": "Uno"}).datos["financiadores"] == []
    assert bitacora.ver(2)[1].estado == "denegada"


def test_flujo_de_procuracion_con_herramientas(entorno_aislado):
    f = correr("registrar_financiador", {"organizacion": "Fundación Uno", "proyecto": "Techos solares",
                                         "tipo": "Fundación", "canal": "Correo"}, autorizada=True)
    assert f.ok, f.datos
    assert f.datos["financiador"]["monto_solicitado_texto"] == "MONTO POR DEFINIR"

    e = correr("abrir_expediente", {"tipo": "Convocatoria", "entidad": "Fondo de Energía Comunitaria"},
               autorizada=True)
    assert e.ok, e.datos
    folio = e.datos["expediente"]["folio"]

    ev = correr("guardar_evaluacion", {**entrada_matriz(), "expediente": folio}, autorizada=True)
    assert ev.ok, ev.datos
    assert ev.datos["expediente"] == folio

    av = correr("registrar_avance", {"folio": folio, "estado": "Se evaluó la convocatoria."}, autorizada=True)
    assert av.ok, av.datos

    doc = correr("generar_documento", {"tipo": "ficha", "expediente": folio}, autorizada=True)
    assert doc.ok, doc.datos
    assert doc.datos["documento"]["expediente_folio"] == folio

    visto = correr("ver_expediente", {"folio": folio})
    assert len(visto.datos["avances"]) == 1
    assert len(visto.datos["evaluaciones"]) == 1
    assert len(visto.datos["documentos"]) == 1
    assert correr("listar_evaluaciones").datos["evaluaciones"][0]["expediente"] == folio


def test_evaluar_no_guarda(entorno_aislado):
    r = correr("evaluar_oportunidad", entrada_matriz())
    assert r.ok
    assert r.datos["guardada"] is False
    assert correr("listar_evaluaciones").datos["evaluaciones"] == []


def test_guardar_evaluacion_rechaza_expediente_inexistente(entorno_aislado):
    r = correr("guardar_evaluacion", {**entrada_matriz(), "expediente": "EXP-2026-9999"}, autorizada=True)
    assert r.estado == "error"
    assert "EXP-2026-9999" in r.datos["error"]


@pytest.mark.parametrize("nombre, argumentos, fragmento", [
    ("ver_financiador", {"folio": "FIN-2026-0001"}, "No existe"),
    ("registrar_financiador", {"organizacion": "X"}, "Entrada no válida"),
    ("no_existe", {}, "No existe la herramienta"),
])
def test_errores_legibles(entorno_aislado, nombre, argumentos, fragmento):
    r = correr(nombre, argumentos, autorizada=True)
    assert r.estado == "error"
    assert fragmento in r.datos["error"]


def test_cada_ejecucion_queda_en_la_bitacora(entorno_aislado):
    correr("ver_perfil")
    correr("fecha_y_plazos")
    registros = bitacora.ver(10)
    assert [r.accion for r in registros[:2]] == ["herramienta:fecha_y_plazos", "herramienta:ver_perfil"]
    assert all(r.canal == "agente" for r in registros)
    assert bitacora.verificar().integra
