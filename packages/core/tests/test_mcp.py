"""Servidor MCP: catálogo, anotaciones, ejecución, bitácora y stdout limpio."""
from __future__ import annotations

import subprocess
import sys

import anyio
import pytest

pytest.importorskip("mcp")

from mcp import Client  # noqa: E402

from coopexecutive import bitacora  # noqa: E402
from coopexecutive.crm import funders  # noqa: E402
from coopexecutive.mcp_server import crear_servidor  # noqa: E402

ESCRITURA = {"registrar_financiador", "abrir_expediente", "registrar_avance", "guardar_evaluacion",
             "generar_documento"}


def _con_cliente(solo_lectura: bool, accion):
    async def correr():
        async with Client(crear_servidor(solo_lectura=solo_lectura)) as cliente:
            return await accion(cliente)

    return anyio.run(correr)


def test_lista_con_anotaciones(entorno_aislado):
    herramientas = _con_cliente(False, lambda c: c.list_tools()).tools
    por_nombre = {t.name: t for t in herramientas}
    assert ESCRITURA <= set(por_nombre)
    assert por_nombre["ver_perfil"].annotations.read_only_hint is True
    assert por_nombre["registrar_financiador"].annotations.read_only_hint is False
    assert por_nombre["monitorear_convocatorias"].annotations.open_world_hint is True
    assert por_nombre["ver_perfil"].input_schema["type"] == "object"


def test_solo_lectura_oculta_las_escrituras(entorno_aislado):
    nombres = {t.name for t in _con_cliente(True, lambda c: c.list_tools()).tools}
    assert nombres and not (nombres & ESCRITURA)


def test_llamada_de_consulta(entorno_aislado):
    r = _con_cliente(False, lambda c: c.call_tool("ver_perfil", {}))
    assert not r.is_error
    assert "Cooperativa de Prueba" in r.content[0].text
    assert r.structured_content["estado"] == "ok"
    ultimo = bitacora.ver(1)[0]
    assert (ultimo.canal, ultimo.accion, ultimo.estado) == ("mcp", "herramienta:ver_perfil", "ok")


def test_escritura_y_errores(entorno_aislado):
    registro = _con_cliente(False, lambda c: c.call_tool("registrar_financiador", {
        "organizacion": "Fundación Uno", "proyecto": "Techos", "tipo": "Fundación", "canal": "Correo"}))
    assert not registro.is_error
    assert funders.buscar("Uno")
    invalida = _con_cliente(False, lambda c: c.call_tool("ver_financiador", {}))
    assert invalida.is_error and "no válida" in invalida.content[0].text


def test_solo_lectura_rechaza_escrituras(entorno_aislado):
    r = _con_cliente(True, lambda c: c.call_tool("registrar_financiador", {"organizacion": "X"}))
    assert r.is_error and "no está disponible" in r.content[0].text
    assert funders.buscar("X") == []


def test_stdout_solo_lleva_el_protocolo(entorno_aislado):
    """Arranca el comando real: la respuesta a `initialize` es lo único que sale por stdout."""
    inicio = ('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18",'
              '"capabilities":{},"clientInfo":{"name":"prueba","version":"0"}}}\n')
    proceso = subprocess.run(
        [sys.executable, "-m", "coopexecutive", "mcp"], input=inicio, capture_output=True, text=True,
        encoding="utf-8", timeout=60,
    )
    lineas = [x for x in proceso.stdout.splitlines() if x.strip()]
    assert lineas, proceso.stderr
    assert all(x.startswith("{") for x in lineas), proceso.stdout
    assert '"serverInfo"' in lineas[0]
