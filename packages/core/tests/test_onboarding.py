from datetime import datetime
from pathlib import Path

import pytest
import yaml

from coopexecutive.memory import onboarding
from coopexecutive.memory.company_profile import CoopProfile, inferir_tipo

REPO = Path(__file__).resolve().parents[3]

RESPUESTAS = {
    "nombre": "Taller Solar de Prueba",
    "siglas": "TSP",
    "figura": "Persona física con actividad empresarial",
    "mision": "Instalar energía limpia en comunidades rurales.",
    "poblacion": "Productores rurales; escuelas",
    "territorio": "Valle de Ejemplo",
    "programas": "Bombeo solar",
    "ejes": ["Energía", "Automatización"],
    "metricas": "",
    "estatus_legal": "Alta vigente",
    "estatus_fiscal": "Régimen de actividad empresarial",
    "rango_minimo": "50,000",
    "rango_maximo": 500000,
    "moneda": "mxn",
    "alianzas": "",
    "financiadores": "",
    "aprobadores": "Titular",
    "mecanismos_cobro": "Transferencia",
}


@pytest.mark.parametrize(
    "figura, tipo",
    [
        ("Sociedad Cooperativa de R.L. de C.V.", "cooperativa"),
        ("S.C. de R.L.", "cooperativa"),
        ("Asociación Civil", "asociacion_civil"),
        ("Fundación Ejemplo, A.C.", "asociacion_civil"),
        ("I.A.P.", "asociacion_civil"),
        ("Persona física con actividad empresarial", "persona_fisica"),
        ("S.A.S. en trámite", "empresa"),
        ("S.A. de C.V.", "empresa"),
    ],
)
def test_inferir_tipo(figura, tipo):
    assert inferir_tipo(figura) == tipo


def test_aplicar_respuestas_completas():
    datos = onboarding.aplicar_respuestas({}, RESPUESTAS)
    perfil = CoopProfile(**datos)
    assert perfil.tipo_organizacion == "persona_fisica"
    assert perfil.target_communities == ["Productores rurales", "escuelas"]
    assert perfil.procuracion.rango_presupuesto.minimo == 50000
    assert perfil.procuracion.moneda_base == "MXN"
    assert perfil.rango_presupuesto_definido
    assert perfil.procuracion.metricas_impacto == []
    bloque = perfil.to_prompt_block()
    assert "Fondos Estatutarios" not in bloque
    assert "[PENDIENTE: métricas de impacto verificables]" in bloque


def test_campos_ausentes_se_conservan():
    base = onboarding.aplicar_respuestas({}, RESPUESTAS)
    nuevo = onboarding.aplicar_respuestas(base, {"mision": "Nueva misión."})
    assert nuevo["mission"] == "Nueva misión."
    assert nuevo["name"] == "Taller Solar de Prueba"
    assert nuevo["procuracion"]["aprobadores"] == ["Titular"]
    assert onboarding.respuestas_actuales(nuevo)["rango_maximo"] == 500000


def test_rango_vacio_queda_por_definir():
    datos = onboarding.aplicar_respuestas({}, {"rango_minimo": "", "rango_maximo": None})
    assert not CoopProfile(**datos).rango_presupuesto_definido


@pytest.mark.parametrize(
    "respuestas, mensaje",
    [
        ({"estatus_fiscal": "RFC GODE561231GR8"}, "RFC o una CURP"),
        ({"alianzas": ["Aliado", "GODE561231HDFRRN09"]}, "RFC o una CURP"),
        ({"telefono": "555"}, "desconocidos"),
        ({"rango_minimo": "mucho"}, "no es un monto"),
        ({"rango_minimo": 10, "rango_maximo": 5}, "mayor que el máximo"),
        ({"moneda": "PESOS"}, None),
    ],
)
def test_respuestas_rechazadas(respuestas, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        onboarding.aplicar_respuestas({}, respuestas)


def test_guardar_respalda_sin_sobrescribir(tmp_path):
    ruta = tmp_path / "profile.yaml"
    ahora = datetime(2026, 9, 27, 10, 30, 0)
    assert onboarding.guardar_perfil(ruta, {"name": "Primera"}, ahora) is None
    r1 = onboarding.guardar_perfil(ruta, {"name": "Segunda"}, ahora)
    r2 = onboarding.guardar_perfil(ruta, {"name": "Tercera"}, ahora)
    assert r1.name == "profile.yaml.bak-20260927-103000"
    assert r2.name == "profile.yaml.bak-20260927-103000-1"
    assert yaml.safe_load(r1.read_text(encoding="utf-8"))["name"] == "Primera"
    assert yaml.safe_load(r2.read_text(encoding="utf-8"))["name"] == "Segunda"
    assert "Tercera" in ruta.read_text(encoding="utf-8")


def test_guardar_perfil_invalido_no_toca_nada(tmp_path):
    ruta = tmp_path / "profile.yaml"
    onboarding.guardar_perfil(ruta, {"name": "Original"})
    with pytest.raises(ValueError):
        onboarding.guardar_perfil(ruta, {"tipo_organizacion": "sindicato"})
    assert list(tmp_path.iterdir()) == [ruta]


def test_crear_espacio_no_sobrescribe(tmp_path):
    espacio = onboarding.crear_espacio(tmp_path / "org", "Org Nueva", "asociacion_civil")
    assert espacio.perfil_creado
    assert (espacio.ruta / "salidas").is_dir()
    perfil = CoopProfile.load_from_yaml(espacio.ruta / "profile.yaml")
    assert perfil.tipo_organizacion == "asociacion_civil"
    assert perfil.legal_structure == "Asociación Civil"
    again = onboarding.crear_espacio(tmp_path / "org", "Otro nombre", "empresa")
    assert not again.perfil_creado
    assert CoopProfile.load_from_yaml(espacio.ruta / "profile.yaml").name == "Org Nueva"


@pytest.mark.parametrize("plantilla", sorted((REPO / "company" / "templates").glob("*.yaml")))
def test_plantillas_y_perfiles_antiguos_cargan(plantilla):
    perfil = CoopProfile.load_from_yaml(plantilla)
    assert perfil.tipo_organizacion in ("cooperativa", "asociacion_civil", "empresa", "persona_fisica")
    assert perfil.to_prompt_block()


def test_ejemplos_del_repositorio_son_validos():
    from coopexecutive.grant_tools import matrix

    ejemplos = REPO / "company" / "examples"
    respuestas = yaml.safe_load((ejemplos / "respuestas_perfil.yaml").read_text(encoding="utf-8"))
    perfil = CoopProfile(**onboarding.aplicar_respuestas({}, respuestas))
    assert perfil.tipo_organizacion == "asociacion_civil"
    assert perfil.rango_presupuesto_definido
    entrada = yaml.safe_load((ejemplos / "convocatoria_ejemplo.yaml").read_text(encoding="utf-8"))
    resultado = matrix.evaluar(entrada, hoy=datetime(2026, 9, 27).date())
    assert resultado.decision == "APLICAR"
    assert resultado.puntaje == 87


def test_perfil_antiguo_sin_campos_nuevos():
    perfil = CoopProfile(name="Coop Antigua", legal_structure="S.C. de R.L.", mission="Servir.")
    assert perfil.tipo_organizacion == "cooperativa"
    assert perfil.procuracion is None
    assert not perfil.rango_presupuesto_definido
    assert "Fondos Estatutarios" in perfil.to_prompt_block()
