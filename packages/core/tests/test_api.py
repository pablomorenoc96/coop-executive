"""API local y panel: token, Host, Origin, cabeceras, consultas, escrituras con confirmación y chat."""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from coopexecutive import bitacora  # noqa: E402
from coopexecutive.crm import funders  # noqa: E402
from coopexecutive.providers.tipos import LlamadaHerramienta  # noqa: E402
from coopexecutive.web.app import ESTATICOS, crear_app  # noqa: E402

TOKEN = "token-de-prueba"
BASE = "http://127.0.0.1:8765"
FINANCIADOR = {"organizacion": "Fundación Uno", "proyecto": "Techos solares", "tipo": "Fundación", "canal": "Correo"}


@pytest.fixture
def cliente(entorno_aislado):
    return TestClient(crear_app(TOKEN, 8765), base_url=BASE, headers={"Authorization": f"Bearer {TOKEN}"})


def _eventos(texto: str) -> list[tuple[str, dict]]:
    salida = []
    for bloque in texto.strip().split("\n\n"):
        tipo = re.search(r"^event: (.*)$", bloque, re.M).group(1)
        datos = json.loads(re.search(r"^data: (.*)$", bloque, re.M).group(1))
        salida.append((tipo, datos))
    return salida


def test_sin_token_no_hay_datos(entorno_aislado):
    anonimo = TestClient(crear_app(TOKEN, 8765), base_url=BASE)
    assert anonimo.get("/api/estado").status_code == 401
    assert anonimo.get("/api/estado", headers={"Authorization": "Bearer otro"}).status_code == 401
    # La página no trae datos: se sirve sin token.
    pagina = anonimo.get("/")
    assert pagina.status_code == 200
    assert "Content-Security-Policy" in pagina.headers
    assert pagina.headers["X-Content-Type-Options"] == "nosniff"
    assert pagina.headers["Referrer-Policy"] == "no-referrer"


def test_host_ajeno_rechazado(entorno_aislado):
    ajeno = TestClient(crear_app(TOKEN, 8765), base_url="http://evil.example:8765",
                       headers={"Authorization": f"Bearer {TOKEN}"})
    assert ajeno.get("/api/estado").status_code == 400


def test_origin_ajeno_rechazado(cliente):
    r = cliente.post("/api/herramientas/ver_perfil", json={}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    ok = cliente.post("/api/herramientas/ver_perfil", json={}, headers={"Origin": BASE})
    assert ok.status_code == 200


def test_estado_y_consultas_vacias(cliente):
    e = cliente.get("/api/estado").json()
    assert e["organizacion"] == "Cooperativa de Prueba"
    assert e["conteos"] == {"financiadores": 0, "expedientes_abiertos": 0, "evaluaciones": 0, "documentos": 0}
    assert e["bitacora"]["integra"]
    assert cliente.get("/api/financiadores").json()["financiadores"] == []
    assert cliente.get("/api/monitoreo").json()["monitoreo"] is None
    assert cliente.get("/api/asamblea").json()["propuestas"] == []
    assert cliente.get("/api/expedientes/EXP-2000-0001").status_code == 404
    assert cliente.get("/api/bitacora?canal=correo").status_code == 422
    # Las lecturas del panel no llenan la bitácora.
    assert bitacora.ver(10) == []


def test_escritura_exige_confirmacion(cliente):
    r = cliente.post("/api/herramientas/registrar_financiador", json={"argumentos": FINANCIADOR})
    assert r.status_code == 409
    assert r.json()["requiere_confirmacion"]
    assert funders.buscar("Uno") == []
    ok = cliente.post("/api/herramientas/registrar_financiador", json={"argumentos": FINANCIADOR, "confirmar": True})
    assert ok.status_code == 200, ok.text
    assert ok.json()["estado"] == "ok"
    folio = ok.json()["financiador"]["folio"]
    assert cliente.get(f"/api/financiadores/{folio}").json()["financiador"]["organizacion"] == "Fundación Uno"
    registro = bitacora.ver(1)[0]
    assert (registro.canal, registro.accion) == ("http", "herramienta:registrar_financiador")
    assert cliente.get("/api/bitacora").json()["verificacion"]["integra"]


def test_herramienta_inexistente_y_entrada_invalida(cliente):
    assert cliente.post("/api/herramientas/borrar_todo", json={}).status_code == 404
    r = cliente.post("/api/herramientas/ver_financiador", json={"argumentos": {}})
    assert r.status_code == 400
    assert "no válida" in r.json()["error"]


def test_chat_con_confirmacion(cliente, respuestas_modelo, monkeypatch):
    import coopexecutive.web.app as web_app

    monkeypatch.setattr(web_app, "ESPERA_CONFIRMACION", 10)
    respuestas_modelo.extend([
        [LlamadaHerramienta(id="c1", nombre="registrar_financiador", argumentos=FINANCIADOR)],
        "Registré a Fundación Uno.",
    ])
    pendientes = cliente.app.state.pendientes

    def autorizar_cuando_se_pida():
        # TestClient entrega el cuerpo al final: se autoriza desde otro hilo en cuanto el servidor espera.
        import time

        for _ in range(400):
            time.sleep(0.02)
            if pendientes:
                cliente.post(f"/api/chat/confirmar/{next(iter(pendientes))}", json={"autorizar": True})
                return

    hilo = threading.Thread(target=autorizar_cuando_se_pida)
    hilo.start()
    r = cliente.post("/api/chat", json={"mensaje": "Registra a Fundación Uno"})
    hilo.join()
    assert r.status_code == 200
    eventos = _eventos(r.text)
    tipos = [t for t, _ in eventos]
    assert tipos[0] == "confirmacion"
    assert "accion" in tipos and tipos[-1] == "fin"
    assert next(d for t, d in eventos if t == "accion")["estado"] == "ok"
    assert funders.buscar("Uno")
    assert next(d for t, d in eventos if t == "fin")["observaciones"] == []


def test_chat_sin_respuesta_no_escribe(cliente, respuestas_modelo, monkeypatch):
    import coopexecutive.web.app as web_app

    monkeypatch.setattr(web_app, "ESPERA_CONFIRMACION", 0.2)
    respuestas_modelo.extend([
        [LlamadaHerramienta(id="c1", nombre="registrar_financiador", argumentos=FINANCIADOR)],
        "Registré a Fundación Uno.",
    ])
    eventos = _eventos(cliente.post("/api/chat", json={"mensaje": "Registra"}).text)
    assert next(d for t, d in eventos if t == "accion")["estado"] == "denegada"
    assert funders.buscar("Uno") == []
    assert any(o.startswith("Afirma una acción") for o in next(d for t, d in eventos if t == "fin")["observaciones"])


def test_confirmacion_inexistente(cliente):
    assert cliente.post("/api/chat/confirmar/nada", json={"autorizar": True}).status_code == 404


def test_panel_sin_recursos_externos():
    for archivo in Path(ESTATICOS).iterdir():
        contenido = archivo.read_text(encoding="utf-8")
        assert "https://" not in contenido and "http://" not in contenido, archivo.name
        assert "innerHTML" not in contenido, archivo.name
