"""Marco lógico, presupuesto y dossier: nada se inventa."""
import json

import yaml
from click.testing import CliRunner

from coopexecutive.cli import cli
from coopexecutive.crm import cases
from coopexecutive.grant_tools.budget_builder import BudgetItem, GrantBudget, presupuesto_desde_datos
from coopexecutive.grant_tools.dossier_generator import ProposalDossier
from coopexecutive.grant_tools.logical_framework import marco_desde_datos


def invocar(*args: str):
    return CliRunner().invoke(cli, list(args))


def escribir(ruta, datos) -> str:
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return str(ruta)


# --- Modelos ---------------------------------------------------------------------


def test_marco_completa_los_cuatro_niveles_con_pendientes():
    marco = marco_desde_datos("Agua", {"filas": [{"nivel": "componente", "resumen": "Red instalada"}]})
    assert [f.level for f in marco.rows] == ["Fin", "Propósito", "Componentes", "Actividades"]
    md = marco.to_markdown()
    assert "Red instalada" in md
    assert "[PENDIENTE: ODS vinculados]" in md
    assert "[PENDIENTE: teoría del cambio]" in md


def test_presupuesto_sin_costo_queda_por_cotizar():
    b = GrantBudget("Agua", "MXN", [
        BudgetItem("Personal", "Coordinación", "meses", 12, unit_cost=10000, matching_amount=20000),
        BudgetItem("Equipo", "Bomba", "pieza", 2),
    ], indirect_cap_pct=7)
    assert b.items[0].requested_amount == 100000
    assert not b.completo
    assert b.indirectos_maximos is None
    md = b.to_markdown()
    assert "COSTO POR COTIZAR" in md
    assert "MONTO POR DEFINIR (parcial:" in md
    assert "Partidas por cotizar:** Bomba" in md


def test_presupuesto_completo_calcula_indirectos_solo_con_tope():
    b = presupuesto_desde_datos("Agua", {"partidas": [
        {"rubro": "Personal", "concepto": "Técnico", "cantidad": 10, "costo_unitario": 1000},
    ]}, tope_indirectos=10)
    assert b.completo and b.grand_total == 10000
    assert b.indirectos_maximos == 1000
    assert presupuesto_desde_datos("Agua", {"partidas": []}).indirectos_maximos is None


def test_dossier_sin_datos_no_inventa_donante_ni_fondos():
    md = ProposalDossier("Agua", "Asociación X", es_cooperativa=False).to_markdown()
    assert "[PENDIENTE: financiador]" in md
    assert "Banco Interamericano" not in md
    assert "SALVAGUARDAS Y CONTROL INTERNO" in md
    assert "estatutarios" not in md


# --- Comandos --------------------------------------------------------------------


def test_marco_logico_sin_datos_es_esqueleto(entorno_aislado):
    res = invocar("marco-logico", "Agua potable")
    assert res.exit_code == 0, res.output
    assert "PENDIENTE" in res.output
    assert "ODS 7" not in res.output


def test_marco_logico_desde_yaml_y_salida_sin_sobrescribir(entorno_aislado):
    datos = escribir(entorno_aislado / "m.yaml", {
        "problema": "Falta de agua", "filas": [{"nivel": "Fin", "resumen": "Salud comunitaria"}],
    })
    salida = entorno_aislado / "marco.md"
    res = invocar("proyecto", "marco-logico", "Agua", "--desde", datos, "--salida", str(salida))
    assert res.exit_code == 0, res.output
    assert "Salud comunitaria" in salida.read_text(encoding="utf-8")
    otra = invocar("marco-logico", "Agua", "--desde", datos, "--salida", str(salida))
    assert otra.exit_code == 1
    assert "ya existe" in otra.output


def test_marco_logico_yaml_invalido(entorno_aislado):
    datos = escribir(entorno_aislado / "m.yaml", {"filas": [{"nivel": "Meta"}]})
    res = invocar("marco-logico", "Agua", "--desde", datos)
    assert res.exit_code == 1
    assert "nivel desconocido" in res.output


def test_marco_logico_plantilla(entorno_aislado):
    res = invocar("marco-logico", "Agua", "--plantilla")
    assert res.exit_code == 0
    assert "teoria_cambio" in res.output


def test_marco_logico_asistido_revisa_en_estricto(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append(json.dumps({
        "problema": "Se requieren $2,500,000 para cubrir la brecha.",
        "filas": [{"nivel": "Fin", "resumen": "Salud", "indicadores": ["Cobertura al 31/12/2027"]}],
    }))
    res = invocar("marco-logico", "Agua", "--asistido")
    assert res.exit_code == 0, res.output
    # El monto sale del cuerpo y solo se cita en la observación de la revisión.
    assert "Se requieren MONTO POR DEFINIR" in res.output
    assert "Revisión automática" in res.output
    assert "Monto sin respaldo" in res.output


def test_presupuesto_asistido_descarta_costos_del_modelo(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append(json.dumps({"partidas": [
        {"rubro": "Equipo", "concepto": "Paneles", "unidad": "pieza", "cantidad": 10, "costo_unitario": 9999},
    ]}))
    res = invocar("presupuesto", "Solar", "--asistido")
    assert res.exit_code == 0, res.output
    assert "Paneles" in res.output
    assert "9,999" not in res.output
    assert "Partidas por cotizar: Paneles" in res.output


def test_presupuesto_desde_yaml_con_tope(entorno_aislado):
    datos = escribir(entorno_aislado / "p.yaml", {"moneda": "USD", "partidas": [
        {"rubro": "Personal", "concepto": "Técnico", "cantidad": 2, "costo_unitario": 500},
    ]})
    res = invocar("presupuesto", "Solar", "--desde", datos, "--tope-indirectos", "10")
    assert res.exit_code == 0, res.output
    assert "USD" in res.output
    assert "Costos indirectos" in res.output


def test_dossier_toma_financiador_del_expediente(entorno_aislado):
    exp = cases.abrir("Convocatoria", "Fundación Aurora")
    res = invocar("dossier", "Agua", "--expediente", exp.folio)
    assert res.exit_code == 0, res.output
    assert "Fundación Aurora" in res.output
    assert "Banco Interamericano" not in res.output
    assert "SALVAGUARDAS COOPERATIVAS" in res.output
    assert invocar("dossier", "Agua", "--expediente", "EXP-2026-9999").exit_code == 1


def test_dossier_con_marco_y_presupuesto(entorno_aislado):
    marco = escribir(entorno_aislado / "m.yaml", {"filas": [{"nivel": "Fin", "resumen": "Salud"}]})
    presupuesto = escribir(entorno_aislado / "p.yaml", {"partidas": [{"rubro": "Equipo", "concepto": "Bomba"}]})
    res = invocar("dossier", "Agua", "--donante", "Fondo Verde", "--marco", marco, "--presupuesto", presupuesto)
    assert res.exit_code == 0, res.output
    assert "Salud" in res.output
    assert "Bomba" in res.output
    assert "MONTO POR DEFINIR" in res.output
