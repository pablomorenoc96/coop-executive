"""Coherencia de la documentación: todo `coopexecutive <comando>` citado en los README y las guías existe."""
from __future__ import annotations

import re
from pathlib import Path

import click
import pytest

from coopexecutive.cli import cli

RAIZ = Path(__file__).resolve().parents[3]
DOCUMENTOS = [RAIZ / "README.md", RAIZ / "README.es.md", *sorted((RAIZ / "docs").glob("GUIA_DE_USO*.md"))]

# Bloques de código y fragmentos en línea: fuera de ellos, «coopexecutive» es prosa.
_BLOQUE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_EN_LINEA = re.compile(r"`([^`\n]+)`")
# Opciones globales que van antes del comando (`--espacio RUTA`). `python -m coopexecutive.evals`
# y `coopexecutive[web]` no coinciden porque exigen un espacio después del nombre.
_CITA = re.compile(r"(?:^|[\s(])coopexecutive\s+(?:--espacio\s+\S+\s+)?([a-z][a-z0-9-]*)(?:[ \t]+([a-z][a-z0-9-]*))?")


def _fragmentos(texto: str) -> list[str]:
    bloques = _BLOQUE.findall(texto)
    resto = _BLOQUE.sub("", texto)
    return [*bloques, *_EN_LINEA.findall(resto)]


_OPCION = re.compile(r"(?<![\w-])--[a-z][a-z-]*")


def _opciones(resto: str) -> tuple[str, ...]:
    """Opciones largas del resto de la línea, sin comentarios ni texto entre comillas."""
    resto = re.sub(r"\"[^\"]*\"|'[^']*'", "", resto.split(" #")[0])
    return tuple(sorted(set(_OPCION.findall(resto))))


def _citas() -> list[tuple[str, str, str | None, tuple[str, ...]]]:
    citas = []
    for doc in DOCUMENTOS:
        for fragmento in _fragmentos(doc.read_text(encoding="utf-8")):
            for linea in fragmento.replace("\\\n", " ").splitlines():
                for m in _CITA.finditer(linea):
                    citas.append((doc.name, m.group(1), m.group(2), _opciones(linea[m.end(1):])))
    return citas


CITAS = _citas()


def test_hay_citas_en_cada_documento():
    for doc in DOCUMENTOS:
        assert any(nombre == doc.name for nombre, *_ in CITAS), f"{doc.name} no cita ningún comando"


@pytest.mark.parametrize(("doc", "comando", "sub", "opciones"), sorted(set(CITAS), key=str), ids=lambda v: str(v))
def test_comando_citado_existe(doc, comando, sub, opciones):
    ctx = click.Context(cli)
    encontrado = cli.get_command(ctx, comando)
    assert encontrado is not None, f"{doc}: `coopexecutive {comando}` no existe"
    if isinstance(encontrado, click.Group) and sub is not None:
        hoja = encontrado.get_command(ctx, sub)
        assert hoja is not None, f"{doc}: `coopexecutive {comando} {sub}` no existe"
        encontrado = hoja
    if isinstance(encontrado, click.Group):
        return  # el grupo solo, o con un argumento: sus opciones son las de cada subcomando
    validas = {o for p in encontrado.params for o in (*p.opts, *p.secondary_opts)}
    for opcion in opciones:
        assert opcion in validas, f"{doc}: `coopexecutive {comando} {sub or ''}` no tiene {opcion}"
