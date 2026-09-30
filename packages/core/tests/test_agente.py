"""Turno con herramientas: consultas, confirmación de escrituras, errores y reintento sin herramientas."""
from __future__ import annotations

import asyncio
import json

import httpx
from click.testing import CliRunner

from coopexecutive import bitacora
from coopexecutive.cli import cli
from coopexecutive.crm import funders
from coopexecutive.herramientas import Resultado
from coopexecutive.orchestrator.agente import Aviso, ejecutar_turno
from coopexecutive.orchestrator.coop_executive import CoopExecutive
from coopexecutive.providers import ErrorProveedor
from coopexecutive.providers.client import AIClient
from coopexecutive.providers.tipos import LlamadaHerramienta, TextoDelta

FINANCIADOR = {"organizacion": "Fundación Uno", "proyecto": "Techos solares", "tipo": "Fundación", "canal": "Correo"}


def turno(mensaje: str, confirmar=None, **extra) -> list:
    async def correr():
        executive = CoopExecutive()
        kwargs = {"confirmar": confirmar} if confirmar else {}
        return [e async for e in ejecutar_turno(executive, mensaje, **kwargs, **extra)]

    return asyncio.run(correr())


def llamada(nombre: str, argumentos: dict | None = None, id_: str = "c1") -> LlamadaHerramienta:
    return LlamadaHerramienta(id=id_, nombre=nombre, argumentos=argumentos or {})


def test_consulta_y_respuesta(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("fecha_y_plazos")], "Hoy es la fecha indicada."])
    eventos = turno("¿Qué día es hoy?")
    resultados = [e for e in eventos if isinstance(e, Resultado)]
    assert [r.nombre for r in resultados] == ["fecha_y_plazos"]
    assert resultados[0].ok
    assert "".join(e.texto for e in eventos if isinstance(e, TextoDelta)) == "Hoy es la fecha indicada."


def test_el_modelo_recibe_el_resultado(entorno_aislado, monkeypatch):
    vistos: list[list[dict]] = []
    pasos = [[llamada("ver_perfil")], [TextoDelta("Listo.")]]

    async def eventos(self, messages, model=None, temperature=0.2, tools=None, max_tokens=4096):
        vistos.append([dict(m) for m in messages])
        for e in pasos.pop(0):
            yield e

    monkeypatch.setattr(AIClient, "eventos", eventos)
    turno("¿Quiénes somos?")
    segundo = vistos[1]
    assert segundo[-2]["role"] == "assistant"
    assert segundo[-2]["tool_calls"][0]["function"]["name"] == "ver_perfil"
    assert segundo[-1]["role"] == "tool"
    assert "Cooperativa de Prueba" in json.loads(segundo[-1]["content"])["nombre"]


def test_escritura_confirmada(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("registrar_financiador", FINANCIADOR)], "Registrado."])
    pedidas = []

    async def si(h, args):
        pedidas.append(h.nombre)
        return True

    eventos = turno("Registra a Fundación Uno", confirmar=si)
    assert pedidas == ["registrar_financiador"]
    assert [e for e in eventos if isinstance(e, Resultado)][0].ok
    assert funders.buscar("Uno")


def test_escritura_negada_no_escribe(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("registrar_financiador", FINANCIADOR)], "No se registró."])
    eventos = turno("Registra a Fundación Uno")  # sin confirmar: se niega
    r = [e for e in eventos if isinstance(e, Resultado)][0]
    assert r.estado == "denegada"
    assert funders.buscar("Uno") == []
    assert bitacora.ver(1)[0].estado == "denegada"


def test_herramienta_fuera_de_la_lista(entorno_aislado, respuestas_modelo):
    from coopexecutive import herramientas

    respuestas_modelo.extend([[llamada("registrar_financiador", FINANCIADOR)], "Sin permiso."])
    eventos = turno("Registra", disponibles=herramientas.todas(solo_lectura=True))
    r = [e for e in eventos if isinstance(e, Resultado)][0]
    assert r.estado == "error"
    assert "no está disponible" in r.datos["error"]
    assert funders.buscar("Uno") == []


def test_argumentos_invalidos(entorno_aislado, respuestas_modelo):
    mala = LlamadaHerramienta(id="c1", nombre="ver_perfil", argumentos_invalidos="{roto")
    respuestas_modelo.extend([[mala], "Perdón."])
    r = [e for e in turno("x") if isinstance(e, Resultado)][0]
    assert r.estado == "error"
    assert "JSON" in r.datos["error"]


def test_limite_de_pasos(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("fecha_y_plazos", id_=f"c{i}")] for i in range(3)])
    eventos = turno("x", max_pasos=3)
    assert isinstance(eventos[-1], Aviso)
    assert "límite de 3 pasos" in eventos[-1].texto


def test_reintenta_sin_herramientas_si_el_proveedor_las_rechaza(entorno_aislado, monkeypatch):
    herramientas_por_llamada = []

    async def eventos(self, messages, model=None, temperature=0.2, tools=None, max_tokens=4096):
        herramientas_por_llamada.append(tools)
        if tools:
            raise ErrorProveedor("tools no soportado", estado=400)
        yield TextoDelta("Respuesta sin herramientas.")

    monkeypatch.setattr(AIClient, "eventos", eventos)
    eventos_turno = turno("x")
    assert herramientas_por_llamada[0] and herramientas_por_llamada[1] is None
    assert any(isinstance(e, Aviso) for e in eventos_turno)


def test_otros_errores_del_proveedor_se_propagan(entorno_aislado, monkeypatch):
    async def eventos(self, messages, model=None, temperature=0.2, tools=None, max_tokens=4096):
        raise ErrorProveedor("sin crédito", estado=402)
        yield  # pragma: no cover

    monkeypatch.setattr(AIClient, "eventos", eventos)
    try:
        turno("x")
    except ErrorProveedor as exc:
        assert exc.estado == 402
    else:  # pragma: no cover
        raise AssertionError("debió propagarse")


def test_ask_sin_terminal_niega_la_escritura(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("registrar_financiador", FINANCIADOR)], "Registré a Fundación Uno."])
    res = CliRunner().invoke(cli, ["ask", "Registra a Fundación Uno"], input="")
    assert res.exit_code == 0, res.output
    assert "Acciones ejecutadas" in res.output
    assert "denegada" in res.output
    assert "Afirma una acción que no se ejecutó" in res.output
    assert funders.buscar("Uno") == []


def test_ask_con_confirmacion(entorno_aislado, respuestas_modelo):
    respuestas_modelo.extend([[llamada("registrar_financiador", FINANCIADOR)], "Registré a Fundación Uno."])
    res = CliRunner().invoke(cli, ["ask", "Registra a Fundación Uno"], input="s\n")
    assert res.exit_code == 0, res.output
    assert "Afirma una acción" not in res.output
    assert funders.buscar("Uno")


def test_ask_sin_herramientas_usa_solo_texto(entorno_aislado, respuestas_modelo):
    respuestas_modelo.append("Solo texto.")
    res = CliRunner().invoke(cli, ["ask", "Hola", "--sin-herramientas"])
    assert res.exit_code == 0, res.output
    assert "Solo texto." in res.output
    assert "Acciones ejecutadas" not in res.output


def test_sse_openai_con_herramienta(entorno_aislado, monkeypatch):
    """El cliente real junta los fragmentos de una llamada a herramienta de OpenAI."""
    cuerpo = "\n".join([
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"fecha_y_plazos",'
        '"arguments":""}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"cierres\\": []}"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        "data: [DONE]",
        "",
    ])
    segundo = 'data: {"choices":[{"delta":{"content":"Listo."}}]}\ndata: [DONE]\n'
    respuestas = [cuerpo, segundo]

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=respuestas.pop(0), headers={"content-type": "text/event-stream"})

    monkeypatch.setenv("PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-prueba-123456")
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-prueba")
    import coopexecutive.config as config

    config._settings = None
    monkeypatch.setattr(AIClient, "__init__", _con_transporte(AIClient.__init__, httpx.MockTransport(responder)))
    eventos = turno("¿Qué día es hoy?")
    r = [e for e in eventos if isinstance(e, Resultado)][0]
    assert r.nombre == "fecha_y_plazos" and r.ok
    assert "".join(e.texto for e in eventos if isinstance(e, TextoDelta)) == "Listo."


def _con_transporte(original, transporte):
    def iniciar(self, *args, **kwargs):
        kwargs.setdefault("transport", transporte)
        original(self, *args, **kwargs)

    return iniciar
