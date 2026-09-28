import json
from datetime import date, timedelta

import pytest
import yaml
from click.testing import CliRunner

from coopexecutive.cli import _consola, cli, procuracion
from coopexecutive.crm import cases, funders
from coopexecutive.orchestrator.coop_executive import CoopExecutive


def invocar(*args: str):
    return CliRunner().invoke(cli, list(args))


def test_info_muestra_perfil_activo(entorno_aislado):
    res = invocar("info")
    assert res.exit_code == 0, res.output
    assert "Cooperativa de Prueba" in res.output
    assert "Energía comunitaria" in res.output


def test_propuesta_y_listado(entorno_aislado):
    res = invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    assert res.exit_code == 0, res.output
    assert "Propuesta registrada" in res.output
    assert "#1" in res.output

    res = invocar("propuestas")
    assert res.exit_code == 0, res.output
    assert "Fondo eolico" in res.output
    assert "ABIERTA" in res.output


def test_propuestas_sin_registros(entorno_aislado):
    res = invocar("propuestas")
    assert res.exit_code == 0, res.output
    assert "No hay propuestas" in res.output


def test_propuesta_prohibida_muestra_error(entorno_aislado):
    res = invocar("propuesta", "Venta", "-d", "Vender acciones de la cooperativa.")
    assert res.exit_code == 0, res.output
    assert "Error Estatutario" in res.output
    assert "No hay propuestas" in invocar("propuestas").output


def test_votar_y_escrutinio(entorno_aislado):
    invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    for socio, voto in [("S1", "a_favor"), ("S2", "A_FAVOR"), ("S3", "EN_CONTRA")]:
        res = invocar("votar", "1", "-s", socio, "-n", f"Socio {socio}", "-v", voto)
        assert res.exit_code == 0, res.output
        assert "Voto Recibida" in res.output

    duplicado = invocar("votar", "1", "-s", "S1", "-n", "Socio S1", "-v", "EN_CONTRA")
    assert "Rechazo de Cédula" in duplicado.output

    res = invocar("escrutinio", "1", "--padron", "5")
    assert res.exit_code == 0, res.output
    assert "APROBADA" in res.output
    assert "SHA256:" in res.output


def test_escrutinio_sin_cuorum_rechaza(entorno_aislado):
    invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    invocar("votar", "1", "-s", "S1", "-n", "Socio S1", "-v", "A_FAVOR")
    res = invocar("escrutinio", "1", "--padron", "12")
    assert res.exit_code == 0, res.output
    assert "RECHAZADA" in res.output


def test_escrutinio_propuesta_inexistente(entorno_aislado):
    res = invocar("escrutinio", "99")
    assert res.exit_code == 0, res.output
    assert "no existe" in res.output


# --- Procuración -----------------------------------------------------------------

HOY = date(2026, 9, 27)
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


@pytest.fixture(autouse=True)
def consola_ancha(monkeypatch):
    """Evita que rich parta los textos que se comparan."""
    monkeypatch.setattr(_consola.console, "_width", 200)


@pytest.fixture
def con_rango(entorno_aislado):
    """Perfil con rango presupuestario definido; sin él, Presupuesto queda pendiente."""
    perfil = entorno_aislado / "profile.yaml"
    perfil.write_text(
        perfil.read_text(encoding="utf-8")
        + "procuracion:\n  rango_presupuesto:\n    minimo: 50000\n    maximo: 500000\n    moneda: MXN\n",
        encoding="utf-8",
    )


@pytest.fixture
def hoy_fijo(monkeypatch):
    monkeypatch.setattr(procuracion, "hoy_local", lambda *_: HOY)


@pytest.fixture
def respuestas_modelo(monkeypatch):
    """Sustituye al modelo: cada llamada a stream_chat devuelve la siguiente respuesta."""
    cola: list[str] = []

    async def falso(self, mensaje, history=None, specialist_focus=None):
        yield cola.pop(0)

    monkeypatch.setattr(CoopExecutive, "stream_chat", falso)
    return cola


def escribir_yaml(ruta, datos) -> str:
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return str(ruta)


def test_iniciar_crea_espacio_y_no_sobrescribe(tmp_path, monkeypatch):
    monkeypatch.delenv("COMPANY_PROFILE_PATH", raising=False)
    monkeypatch.delenv("EPISODIC_DB_PATH", raising=False)
    espacio = tmp_path / "org"
    res = invocar("iniciar", str(espacio), "--nombre", "Org de Prueba", "--tipo", "asociacion_civil")
    assert res.exit_code == 0, res.output
    assert (espacio / "profile.yaml").is_file()
    assert (espacio / "salidas").is_dir()
    assert (espacio / "coop_memory.db").is_file()
    otra = invocar("iniciar", str(espacio), "--nombre", "Otro")
    assert "ya existía" in otra.output
    info = invocar("--espacio", str(espacio), "info")
    assert info.exit_code == 0, info.output
    assert "Org de Prueba" in info.output


def test_configurar_desde_archivo_respalda(entorno_aislado):
    respuestas = escribir_yaml(entorno_aislado / "r.yaml", {
        "mision": "Llevar energía limpia a comunidades rurales.",
        "ejes": "Energía; Agua",
        "rango_minimo": 50000, "rango_maximo": 300000, "moneda": "MXN",
    })
    res = invocar("configurar", "--desde", respuestas)
    assert res.exit_code == 0, res.output
    assert "Perfil guardado" in res.output
    assert list(entorno_aislado.glob("profile.yaml.bak-*"))
    datos = yaml.safe_load((entorno_aislado / "profile.yaml").read_text(encoding="utf-8"))
    assert datos["focus_areas"] == ["Energía", "Agua"]
    assert datos["name"] == "Cooperativa de Prueba"


def test_configurar_rechaza_identificadores(entorno_aislado):
    respuestas = escribir_yaml(entorno_aislado / "r.yaml", {"estatus_fiscal": "RFC GODE561231GR8"})
    res = invocar("configurar", "--desde", respuestas)
    assert res.exit_code == 1
    assert "Perfil no válido" in res.output
    assert not list(entorno_aislado.glob("profile.yaml.bak-*"))


def test_configurar_interactivo_sin_guardar(entorno_aislado):
    res = CliRunner().invoke(cli, ["configurar"], input="\n" * 18 + "n\n")
    assert res.exit_code == 0, res.output
    assert "No se guardó" in res.output


def test_evaluar_archivo_aplicar_y_guardar(entorno_aislado, hoy_fijo, con_rango):
    archivo = escribir_yaml(entorno_aislado / "c.yaml", entrada_matriz())
    res = invocar("evaluar-convocatoria", "--archivo", archivo)
    assert res.exit_code == 0, res.output
    assert "APLICAR" in res.output
    assert "guardada con id 1" in res.output


def test_evaluar_vencida_descarta(entorno_aislado, hoy_fijo):
    datos = entrada_matriz(fecha_cierre=(HOY - timedelta(days=1)).isoformat())
    datos["criterios"]["tiempos"]["puntos"] = 0
    res = invocar("evaluar-convocatoria", "--archivo", escribir_yaml(entorno_aislado / "c.yaml", datos))
    assert res.exit_code == 0, res.output
    assert "DESCARTAR" in res.output
    assert "Vencida" in res.output


def test_evaluar_incompleta_sin_rango(entorno_aislado, hoy_fijo):
    datos = entrada_matriz()
    datos["criterios"]["presupuesto"] = {"puntos": None, "evidencia": ""}
    res = invocar("evaluar-convocatoria", "--archivo", escribir_yaml(entorno_aislado / "c.yaml", datos),
                  "--no-guardar")
    assert res.exit_code == 0, res.output
    assert "EVALUACION_INCOMPLETA" in res.output
    assert "guardada" not in res.output


def test_evaluar_error_de_validacion(entorno_aislado, hoy_fijo):
    datos = entrada_matriz()
    datos["criterios"]["alineacion"]["puntos"] = 8.5
    res = invocar("evaluar-convocatoria", "--archivo", escribir_yaml(entorno_aislado / "c.yaml", datos))
    assert res.exit_code == 1
    assert "ERROR_VALIDACION" in res.output


def test_evaluar_expediente_inexistente_y_url(entorno_aislado):
    res = invocar("evaluar-convocatoria", "--expediente", "EXP-2026-0099")
    assert res.exit_code == 1
    assert "No existe el expediente" in res.output
    res = invocar("evaluar-convocatoria", "https://ejemplo.org/bases")
    assert res.exit_code == 1
    assert "Origen no admitido" in res.output


def test_evaluar_asistido_con_modelo_simulado(entorno_aislado, hoy_fijo, con_rango, respuestas_modelo):
    invocar("expedientes", "abrir", "Fundación Ejemplo", "--tipo", "Convocatoria")
    respuestas_modelo.append("```json\n" + json.dumps(entrada_matriz()) + "\n```")
    respuestas_modelo.append("Conviene postular.\n\nCONTRAPUNTO: el plazo exige avanzar esta semana.")
    bases = entorno_aislado / "bases.txt"
    bases.write_text("Bases del Fondo de Energía Comunitaria.", encoding="utf-8")
    folio = cases.listar()[0].folio
    res = invocar("evaluar-convocatoria", str(bases), "--expediente", folio.lower(), "--si")
    assert res.exit_code == 0, res.output
    assert "Propuesta del modelo" in res.output
    assert "APLICAR" in res.output
    assert f"vinculada a {folio}" in res.output
    assert "Borrador: requiere revisión humana." in res.output
    assert [e.decision for e in cases.evaluaciones(folio)] == ["APLICAR"]


def test_evaluar_asistido_json_invalido(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append("No tengo datos suficientes.")
    res = invocar("evaluar-convocatoria", "--asistido", "Bases breves.", "--si")
    assert res.exit_code == 1
    assert "Propuesta no válida" in res.output


def test_evaluar_interactivo(entorno_aislado, hoy_fijo, con_rango):
    cierre = (HOY + timedelta(days=40)).isoformat()
    lineas = ["Beca de Posgrado", "Consejo Ejemplo", "beca", "", cierre, "Bases, numeral 3",
              "confirmada", "vigente", "ninguna"]
    for clave, puntos in PUNTOS.items():
        lineas += [str(puntos), f"Bases sobre {clave}"]
    res = CliRunner().invoke(cli, ["evaluar-convocatoria"], input="\n".join(lineas) + "\n")
    assert res.exit_code == 0, res.output
    assert "APLICAR" in res.output


def test_financiadores_por_cli(entorno_aislado):
    res = invocar("financiadores", "registrar", "Fundación Ejemplo, A.C.", "--proyecto", "Energía comunitaria",
                  "--tipo", "fundacion", "--canal", "correo", "--moneda", "usd", "--monto-solicitado", "57000")
    assert res.exit_code == 0, res.output
    assert "57,000.00 USD" in res.output
    folio = funders.buscar()[0].folio
    duplicado = invocar("financiadores", "registrar", "FUNDACION EJEMPLO AC", "--proyecto", "Otro",
                        "--tipo", "Fundación", "--canal", "Correo")
    assert duplicado.exit_code == 1
    assert folio in invocar("financiadores", "buscar", "fundacion").output
    assert "No hay financiadores" in invocar("financiadores", "buscar", "inexistente").output
    act = invocar("financiadores", "actualizar", folio, "--estatus", "Contactado")
    assert act.exit_code == 0, act.output
    assert "Contactado" in invocar("financiadores", "ver", folio).output
    assert invocar("financiadores", "actualizar", folio).exit_code == 1


def test_expedientes_por_cli(entorno_aislado):
    res = invocar("expedientes", "abrir", "Fondo Rural", "--tipo", "credito", "--responsable", "Titular")
    assert res.exit_code == 0, res.output
    assert "MONTO POR DEFINIR" in res.output
    folio = cases.listar()[0].folio
    av = invocar("expedientes", "avance", folio, "--estado", "En pausa por revisión",
                 "--siguiente", "Consultar requisitos")
    assert av.exit_code == 0, av.output
    assert "En pausa por revisión" in invocar("expedientes", "ver", folio).output
    assert "Fondo Rural" in invocar("expedientes", "listar", "--responsable", "titular").output
    assert invocar("expedientes", "abrir", "Fondo Rural", "--tipo", "Crédito").exit_code == 1


def test_ask_estricto_sustituye_montos(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append("Solicite 1,500,000 MXN.\n\nCONTRAPUNTO: falta confirmar el tope.")
    res = invocar("ask", "Cuanto pedir", "--rol", "procurador", "--estricto")
    assert res.exit_code == 0, res.output
    assert "MONTO POR DEFINIR" in res.output
    assert "Solicite MONTO POR DEFINIR." in res.output
    assert "Borrador: requiere revisión humana." in res.output


def test_ask_sin_rol_no_revisa(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append("Respuesta general.")
    res = invocar("ask", "Hola")
    assert res.exit_code == 0, res.output
    assert "Respuesta general." in res.output
    assert "Borrador" not in res.output
