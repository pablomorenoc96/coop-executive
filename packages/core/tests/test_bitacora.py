"""Bitácora encadenada: integridad, detección de cambios, censura y exportación."""
from __future__ import annotations

import json

import pytest

from coopexecutive import bitacora
from coopexecutive.memory.episodic import get_db_conn


def test_cadena_integra(entorno_aislado):
    primero = bitacora.registrar("cli", "fecha")
    segundo = bitacora.registrar("mcp", "herramienta:ver_perfil", {"x": 1})
    assert primero.hash_previo == bitacora.GENESIS
    assert segundo.hash_previo == primero.hash
    v = bitacora.verificar()
    assert v.integra and v.total == 2


def test_detecta_edicion(entorno_aislado):
    bitacora.registrar("cli", "a")
    r = bitacora.registrar("cli", "b", estado="error", resultado="falló")
    bitacora.registrar("cli", "c")
    with get_db_conn() as conn:
        conn.execute("UPDATE bitacora SET estado = 'ok' WHERE id = ?", (r.id,))
    v = bitacora.verificar()
    assert not v.integra
    assert v.roto_en == r.id


def test_detecta_borrado(entorno_aislado):
    bitacora.registrar("cli", "a")
    r = bitacora.registrar("cli", "b")
    siguiente = bitacora.registrar("cli", "c")
    with get_db_conn() as conn:
        conn.execute("DELETE FROM bitacora WHERE id = ?", (r.id,))
    v = bitacora.verificar()
    assert v.roto_en == siguiente.id
    assert "no enlaza" in v.motivo


def test_censura_secretos_y_datos_bancarios(entorno_aislado):
    r = bitacora.registrar("http", "x", {
        "api_key": "sk-123", "Authorization": "Bearer abc", "nota": "CLABE 012345678901234567",
        "texto": "a" * 1000,
    })
    assert r.parametros["api_key"] == bitacora.SECRETO
    assert r.parametros["Authorization"] == bitacora.SECRETO
    assert "012345678901234567" not in r.parametros["nota"]
    assert len(r.parametros["texto"]) == bitacora.LARGO_MAXIMO


def test_canal_y_estado_validos(entorno_aislado):
    with pytest.raises(ValueError):
        bitacora.registrar("correo", "x")
    with pytest.raises(ValueError):
        bitacora.registrar("cli", "x", estado="raro")


def test_exportar_no_sobrescribe(entorno_aislado):
    bitacora.registrar("cli", "a")
    bitacora.registrar("cli", "b")
    destino = entorno_aislado / "bitacora.jsonl"
    assert bitacora.exportar_jsonl(destino) == 2
    lineas = [json.loads(x) for x in destino.read_text(encoding="utf-8").splitlines()]
    assert [x["accion"] for x in lineas] == ["a", "b"]
    with pytest.raises(FileExistsError):
        bitacora.exportar_jsonl(destino)


def test_registrar_sin_fallar_no_propaga(entorno_aislado, monkeypatch):
    def romper(*_a, **_k):
        raise RuntimeError("disco lleno")

    monkeypatch.setattr(bitacora, "registrar", romper)
    assert bitacora.registrar_sin_fallar("cli", "x") is None


# --- Comandos --------------------------------------------------------------------------------

def _cli(*args: str, entrada: str | None = None):
    from click.testing import CliRunner

    from coopexecutive.cli import cli

    return CliRunner().invoke(cli, list(args), input=entrada)


def test_los_comandos_quedan_en_la_bitacora(entorno_aislado):
    res = _cli("financiadores", "registrar", "Fundación Uno", "--proyecto", "Techos",
               "--tipo", "Fundación", "--canal", "Correo")
    assert res.exit_code == 0, res.output
    fallido = _cli("financiadores", "ver", "FIN-2000-0001")
    assert fallido.exit_code == 1
    registros = bitacora.ver(10)
    assert [(r.canal, r.accion, r.estado) for r in registros[:2]] == [
        ("cli", "financiadores ver", "error"),
        ("cli", "financiadores registrar", "ok"),
    ]
    assert registros[1].parametros["organizacion"] == "Fundación Uno"


def test_las_consultas_informativas_no_se_registran(entorno_aislado):
    assert _cli("info").exit_code == 0
    assert _cli("bitacora", "ver").exit_code == 0
    assert bitacora.ver(10) == []


def test_bitacora_verificar_por_cli(entorno_aislado):
    bitacora.registrar("cli", "a")
    r = bitacora.registrar("cli", "b")
    assert "íntegra" in _cli("bitacora", "verificar").output
    with get_db_conn() as conn:
        conn.execute("UPDATE bitacora SET accion = 'otra' WHERE id = ?", (r.id,))
    res = _cli("bitacora", "verificar")
    assert res.exit_code == 1
    assert "alterada" in res.output


def test_bitacora_exportar_por_cli(entorno_aislado):
    bitacora.registrar("cli", "a")
    destino = entorno_aislado / "b.jsonl"
    assert _cli("bitacora", "exportar", str(destino)).exit_code == 0
    assert destino.exists()
    assert _cli("bitacora", "exportar", str(destino)).exit_code == 1


def test_cada_comando_se_envuelve_una_vez():
    from coopexecutive.cli import cli

    vistos = set()
    pendientes = [cli]
    while pendientes:
        c = pendientes.pop()
        if hasattr(c, "commands"):
            pendientes.extend(c.commands.values())
        else:
            assert getattr(c.invoke, "__auditado__", False), c.name
            vistos.add(id(c))
    assert vistos
