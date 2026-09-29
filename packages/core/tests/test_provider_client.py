"""Cliente de modelos con un transporte simulado: reintentos, errores, local y llamadas a herramientas."""
import asyncio
import json

import httpx
import pytest

from coopexecutive.config import Settings
from coopexecutive.providers import AIClient, ErrorProveedor, Fin, LlamadaHerramienta, TextoDelta
from coopexecutive.providers.client import mensajes_anthropic


def _sse(*trozos: dict | str) -> bytes:
    lineas = []
    for t in trozos:
        lineas.append("data: " + (t if isinstance(t, str) else json.dumps(t)))
    return ("\n\n".join(lineas) + "\n\n").encode()


def _texto_openai(texto: str) -> bytes:
    return _sse({"choices": [{"delta": {"content": texto}}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]}, "[DONE]")


def _cliente(manejador, **entorno) -> AIClient:
    ajustes = Settings(**{"OPENROUTER_API_KEY": "sk-or-secreta-123", **entorno})
    return AIClient(transport=httpx.MockTransport(manejador), settings=ajustes, pausa_base=0)


def _eventos(cliente: AIClient, **kw) -> list:
    async def correr():
        return [e async for e in cliente.eventos([{"role": "user", "content": "hola"}], **kw)]
    return asyncio.run(correr())


def test_texto_y_fin():
    cliente = _cliente(lambda req: httpx.Response(200, content=_texto_openai("Buenos días")))
    eventos = _eventos(cliente)
    assert eventos[0] == TextoDelta("Buenos días")
    assert isinstance(eventos[-1], Fin) and eventos[-1].motivo == "stop"
    assert eventos[-1].proveedor == "openrouter"


def test_reintenta_429_y_respeta_retry_after():
    llamadas = []

    def manejador(req):
        llamadas.append(req)
        if len(llamadas) < 3:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"message": "lento"}})
        return httpx.Response(200, content=_texto_openai("listo"))

    eventos = _eventos(_cliente(manejador))
    assert len(llamadas) == 3
    assert eventos[0] == TextoDelta("listo")


def test_agota_reintentos_y_pasa_al_modelo_de_respaldo():
    modelos = []

    def manejador(req):
        modelo = json.loads(req.content)["model"]
        modelos.append(modelo)
        if modelo == "principal:free":
            return httpx.Response(503, json={"error": {"message": "caído"}})
        return httpx.Response(200, content=_texto_openai("respaldo"))

    cliente = _cliente(manejador, DEFAULT_MODEL="principal:free", DEEP_REASONING_MODEL="respaldo:free",
                       MAX_REINTENTOS=2)
    eventos = _eventos(cliente)
    assert modelos == ["principal:free"] * 3 + ["respaldo:free"]
    assert eventos[0] == TextoDelta("respaldo")


def test_401_no_reintenta_y_censura_la_clave():
    llamadas = []

    def manejador(req):
        llamadas.append(req)
        return httpx.Response(401, json={"error": {"message": "clave sk-or-secreta-123 inválida"}})

    with pytest.raises(ErrorProveedor) as exc:
        _eventos(_cliente(manejador))
    assert len(llamadas) == 1
    assert exc.value.estado == 401
    assert "sk-or-secreta-123" not in str(exc.value)
    assert "OPENROUTER_API_KEY" in str(exc.value)


def test_error_de_conexion_se_lanza_no_se_devuelve_como_texto():
    def manejador(req):
        raise httpx.ConnectError("sin red", request=req)

    cliente = _cliente(manejador, MAX_REINTENTOS=1)
    with pytest.raises(ErrorProveedor, match="Sin conexión"):
        _eventos(cliente)


def test_falta_clave_falla_antes_de_enviar():
    enviados = []
    cliente = AIClient(transport=httpx.MockTransport(lambda r: enviados.append(r)), settings=Settings(), pausa_base=0)
    with pytest.raises(ErrorProveedor, match="OPENROUTER_API_KEY"):
        _eventos(cliente)
    assert enviados == []


def test_clave_de_ejemplo_cuenta_como_vacia():
    assert Settings(OPENROUTER_API_KEY="sk-or-v1-tu-clave-aqui").openrouter_api_key is None


def test_openrouter_desactivado():
    cliente = AIClient(settings=Settings(OPENROUTER_ENABLED="false", OPENROUTER_API_KEY="sk-or-x-123456"))
    with pytest.raises(ErrorProveedor, match="OPENROUTER_ENABLED"):
        _eventos(cliente)


def test_local_usa_los_modelos_de_ollama_y_su_tiempo():
    vistos = []

    def manejador(req):
        vistos.append((str(req.url), json.loads(req.content)["model"], req.extensions["timeout"]["read"]))
        return httpx.Response(200, content=_texto_openai("local"))

    cliente = AIClient(transport=httpx.MockTransport(manejador), pausa_base=0, settings=Settings(
        LOCAL_MODELS_ENABLED="true", LOCAL_MODELS="granite4.1:8b,qwen3.8:27b", LOCAL_TIMEOUT_S="42"))
    _eventos(cliente)
    url, modelo, espera = vistos[0]
    assert url == "http://localhost:11434/v1/chat/completions"
    assert modelo == "granite4.1:8b"  # nunca el modelo de OpenRouter
    assert espera == 42


def test_llamada_a_herramienta_openai_en_fragmentos():
    cuerpo = _sse(
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "dias_", "arguments": ""}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "restantes", "arguments": '{"fe'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'cha": "2026-10-30"}'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        "[DONE]",
    )
    herramientas = [{"name": "dias_restantes", "description": "x", "parameters": {"type": "object"}}]
    enviados = []

    def manejador(req):
        enviados.append(json.loads(req.content))
        return httpx.Response(200, content=cuerpo)

    eventos = _eventos(_cliente(manejador), tools=herramientas)
    assert enviados[0]["tools"][0]["type"] == "function"
    llamada = eventos[0]
    assert llamada == LlamadaHerramienta(id="c1", nombre="dias_restantes", argumentos={"fecha": "2026-10-30"})
    assert eventos[-1].motivo == "tool_calls"


def test_llamada_a_herramienta_anthropic():
    cuerpo = _sse(
        {"type": "message_start", "message": {}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Reviso."}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "ver_perfil"}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{}"}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
        {"type": "message_stop"},
    )
    enviados = []

    def manejador(req):
        enviados.append(json.loads(req.content))
        return httpx.Response(200, content=cuerpo)

    cliente = AIClient(transport=httpx.MockTransport(manejador), pausa_base=0,
                       settings=Settings(ANTHROPIC_API_KEY="sk-ant-prueba-123"))
    mensajes = [{"role": "system", "content": "Eres útil."}, {"role": "user", "content": "perfil"}]

    async def correr():
        return [e async for e in cliente.eventos(mensajes, model="claude-sonnet-5-5",
                                                 tools=[{"name": "ver_perfil", "parameters": {"type": "object"}}])]

    eventos = asyncio.run(correr())
    assert enviados[0]["system"] == "Eres útil."
    assert enviados[0]["tools"][0]["input_schema"] == {"type": "object"}
    assert eventos[0] == TextoDelta("Reviso.")
    assert eventos[1] == LlamadaHerramienta(id="t1", nombre="ver_perfil", argumentos={})
    assert eventos[-1].motivo == "tool_calls"


def test_argumentos_invalidos_no_rompen():
    cuerpo = _sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c", "function": {
        "name": "x", "arguments": "{roto"}}]}}]}, "[DONE]")
    eventos = _eventos(_cliente(lambda r: httpx.Response(200, content=cuerpo)))
    assert eventos[0].argumentos_invalidos == "{roto"


def test_conversion_de_resultados_de_herramientas_a_anthropic():
    sistema, mensajes = mensajes_anthropic([
        {"role": "system", "content": "S"},
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "a", "type": "function", "function": {"name": "f", "arguments": '{"x": 1}'}},
            {"id": "b", "type": "function", "function": {"name": "g", "arguments": "{}"}},
        ]},
        {"role": "tool", "tool_call_id": "a", "content": "1"},
        {"role": "tool", "tool_call_id": "b", "content": "2"},
    ])
    assert sistema == "S"
    assert mensajes[1]["content"][0] == {"type": "tool_use", "id": "a", "name": "f", "input": {"x": 1}}
    assert [b["tool_use_id"] for b in mensajes[2]["content"]] == ["a", "b"]


def test_stream_chat_conserva_la_interfaz_de_texto():
    cliente = _cliente(lambda req: httpx.Response(200, content=_texto_openai("solo texto")))

    async def correr():
        return [t async for t in cliente.stream_chat([{"role": "user", "content": "x"}])]

    assert asyncio.run(correr()) == ["solo texto"]
