import json
from datetime import date, timedelta

import pytest

from coopexecutive.grant_tools import matrix
from coopexecutive.grant_tools.matrix import CRITERIOS, PESOS, banda_tiempos, evaluar, texto_plazo
from coopexecutive.memory.episodic import get_db_conn

HOY = date(2026, 9, 27)

PUNTOS_BASE = {
    "alineacion": 18,
    "elegibilidad": 9,
    "presupuesto": 13,
    "tiempos": 9,
    "capacidad": 13,
    "impacto": 13,
    "estrategico": 8,
    "reporte": 4,
}  # 87


def entrada(puntos: dict | None = None, **extra) -> dict:
    puntos = {**PUNTOS_BASE, **(puntos or {})}
    datos = {
        "convocatoria": "Fondo de Energía Comunitaria",
        "financiador": "Fundación Ejemplo",
        "monto": "250,000.00 MXN",
        "elegibilidad": "confirmada",
        "vigencia": "vigente",
        "fecha_cierre": (HOY + timedelta(days=40)).isoformat(),
        "evidencia_plazo": "Bases, numeral 5.",
        "criterios": {
            clave: {"puntos": valor, "evidencia": f"Evidencia de {clave}." if valor not in (None, "") else ""}
            for clave, valor in puntos.items()
        },
    }
    datos.update(extra)
    return datos


def con_total(total: int, **extra) -> dict:
    """Entrada completa cuyo puntaje suma `total`, con Tiempos en 10 (cierre a 40 días)."""
    puntos = dict(PESOS)
    exceso = sum(puntos.values()) - total
    for clave in puntos:
        if clave == "tiempos" or exceso == 0:
            continue
        baja = min(puntos[clave], exceso)
        puntos[clave] -= baja
        exceso -= baja
    assert sum(puntos.values()) == total
    return entrada(puntos, **extra)


# --- Plazos ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "dias, banda, texto",
    [
        (-1, (0, 2), "Vencida"),
        (0, (0, 2), "Cierra hoy (URGENTE)"),
        (1, (0, 2), "Falta 1 día (URGENTE)"),
        (6, (0, 2), "Faltan 6 días (URGENTE)"),
        (7, (3, 5), "Faltan 7 días (URGENTE)"),
        (13, (3, 5), "Faltan 13 días (URGENTE)"),
        (14, (6, 8), "Faltan 14 días"),
        (28, (6, 8), "Faltan 28 días"),
        (29, (9, 10), "Faltan 29 días"),
        (None, (0, 10), "Fecha de cierre por confirmar"),
    ],
)
def test_bandas_y_textos_de_plazo(dias, banda, texto):
    assert banda_tiempos(dias) == banda
    assert texto_plazo(dias) == texto


def test_fecha_de_cierre_calcula_dias_desde_hoy():
    res = evaluar(entrada(), hoy=HOY)
    assert res.dias_restantes == 40
    assert res.plazo == "Faltan 40 días"


def test_tiempos_fuera_de_banda_es_error():
    res = evaluar(entrada({"tiempos": 9}, fecha_cierre=(HOY + timedelta(days=10)).isoformat()), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert any("3 a 5" in e for e in res.errores)


def test_fecha_y_dias_inconsistentes_es_error():
    res = evaluar(entrada(dias_restantes=12), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert any("implica 40 días" in e for e in res.errores)


def test_plazo_sin_evidencia_es_error():
    res = evaluar(entrada(evidencia_plazo=""), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert any("evidencia de la fecha" in e for e in res.errores)


# --- Validación de puntajes ---------------------------------------------------------


@pytest.mark.parametrize("valor", [8.5, "8.5", True, 21, -1, "ocho"])
def test_puntajes_invalidos(valor):
    res = evaluar(entrada({"alineacion": valor}), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert any(e.startswith("Alineación") for e in res.errores)


@pytest.mark.parametrize("valor", [18, "18", 18.0])
def test_puntajes_enteros_equivalentes(valor):
    assert evaluar(entrada({"alineacion": valor}), hoy=HOY).puntaje == 87


def test_puntaje_sin_evidencia_es_error():
    datos = entrada()
    datos["criterios"]["impacto"]["evidencia"] = "  "
    res = evaluar(datos, hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert any("no tiene evidencia" in e for e in res.errores)


def test_criterio_vacio_queda_pendiente_y_no_vale_cero():
    res = evaluar(entrada({"reporte": ""}), hoy=HOY)
    assert res.decision == "EVALUACION_INCOMPLETA"
    assert res.puntaje == 83
    assert res.puntaje_maximo_evaluado == 95
    assert any("Requisitos de Auditoría" in p for p in res.pendientes)
    assert "Faltan: Requisitos de Auditoría y Reporte" in res.siguiente_paso


def test_cero_con_evidencia_si_cuenta():
    res = evaluar(entrada({"reporte": 0}), hoy=HOY)
    assert res.decision == "APLICAR"
    assert res.puntaje == 83
    assert res.puntaje_maximo_evaluado == 100


def test_criterio_desconocido_es_error():
    datos = entrada()
    datos["criterios"]["innovacion"] = {"puntos": 5, "evidencia": "x"}
    assert evaluar(datos, hoy=HOY).decision == "ERROR_VALIDACION"


def test_entrada_con_formato_invalido():
    res = evaluar(entrada(tipo="subsidio"), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"
    assert res.convocatoria == "Fondo de Energía Comunitaria"
    assert res.hash


def test_rango_de_presupuesto_no_definido_deja_pendiente():
    res = evaluar(entrada(), hoy=HOY, rango_presupuesto_definido=False)
    presupuesto = next(c for c in res.criterios if c.clave == "presupuesto")
    assert presupuesto.puntos is None
    assert presupuesto.evidencia == "MONTO POR DEFINIR"
    assert res.decision == "EVALUACION_INCOMPLETA"


# --- Precedencia ---------------------------------------------------------------------


def test_error_precede_a_exclusion():
    res = evaluar(entrada({"alineacion": 8.5}, elegibilidad="excluida"), hoy=HOY)
    assert res.decision == "ERROR_VALIDACION"


def test_exclusion_precede_a_vencida():
    res = evaluar(entrada({"tiempos": 1}, elegibilidad="excluida", vigencia="vencida"), hoy=HOY)
    assert res.decision == "DESCARTAR"
    assert res.siguiente_paso.startswith("Archivar")


def test_vencida_descarta_con_contrapunto():
    cierre = (HOY - timedelta(days=1)).isoformat()
    res = evaluar(entrada({"tiempos": 0}, fecha_cierre=cierre), hoy=HOY)
    assert res.decision == "DESCARTAR"
    assert res.plazo == "Vencida"
    assert "siguiente edición" in res.contrapunto
    assert "reapertura" in res.siguiente_paso


def test_elegibilidad_pendiente_precede_a_vigencia():
    res = evaluar(entrada(elegibilidad="pendiente", vigencia="pendiente"), hoy=HOY)
    assert res.decision == "VERIFICAR_ELEGIBILIDAD"


def test_vigencia_pendiente():
    assert evaluar(entrada(vigencia="pendiente"), hoy=HOY).decision == "VERIFICAR_VIGENCIA"


def test_posicion_publica_precede_a_incompleta():
    res = evaluar(entrada({"reporte": None}, tension="posicion_publica"), hoy=HOY)
    assert res.decision == "ESCALAR_DIRECCION"


@pytest.mark.parametrize(
    "total, decision",
    [(100, "APLICAR"), (80, "APLICAR"), (79, "EXPLORAR"), (60, "EXPLORAR"), (59, "CONDICIONAL"),
     (40, "CONDICIONAL"), (39, "DESCARTAR"), (10, "DESCARTAR")],
)
def test_umbrales(total, decision):
    res = evaluar(con_total(total), hoy=HOY)
    assert res.puntaje == total
    assert res.decision == decision
    assert res.contrapunto


@pytest.mark.parametrize("total", [87, 65])
def test_tension_pendiente_baja_a_condicional(total):
    res = evaluar(con_total(total, tension="pendiente", tension_detalle="alianza en revisión"), hoy=HOY)
    assert res.decision == "CONDICIONAL"
    assert "alianza en revisión" in res.contrapunto


def test_contrapunto_senala_criterio_mas_debil():
    res = evaluar(entrada({"reporte": 1}), hoy=HOY)
    assert "Requisitos de Auditoría y Reporte" in res.contrapunto


def test_contrapunto_de_descarte_senala_criterio_mas_fuerte():
    res = evaluar(con_total(20), hoy=HOY)
    assert res.decision == "DESCARTAR"
    assert "A favor de reconsiderarla" in res.contrapunto


# --- Resultado -------------------------------------------------------------------------


def test_hash_es_reproducible_y_sensible_a_cambios():
    a = evaluar(entrada(), hoy=HOY)
    b = evaluar(entrada(), hoy=HOY)
    c = evaluar(entrada({"reporte": 3}), hoy=HOY)
    assert a.hash == b.hash == a.calcular_hash()
    assert len(a.hash) == 64
    assert a.hash != c.hash


def test_markdown_sin_emojis_y_con_huella():
    res = evaluar(entrada(), hoy=HOY)
    md = res.to_markdown()
    assert "## Decisión: APLICAR" in md
    assert "## Contrapunto" in md
    assert f"Huella SHA-256: `{res.hash}`" in md
    assert all(ord(ch) < 0x2600 for ch in md)
    assert len(res.criterios) == len(CRITERIOS)


def test_guardar_escribe_en_grant_evaluations(entorno_aislado):
    res = evaluar(entrada(), hoy=HOY)
    id_evaluacion = matrix.guardar(res, "EXP-2026-0001")
    with get_db_conn() as conn:
        fila = conn.execute("SELECT * FROM grant_evaluations WHERE id = ?", (id_evaluacion,)).fetchone()
    assert fila["recommendation"] == "APLICAR"
    assert fila["total_score"] == 87
    assert fila["hash"] == res.hash
    assert fila["expediente_folio"] == "EXP-2026-0001"
    assert json.loads(fila["resultado_json"])["decision"] == "APLICAR"
