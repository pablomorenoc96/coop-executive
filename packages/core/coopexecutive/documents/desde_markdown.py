"""Convierte un texto en Markdown (el que redacta el modelo) en un `DocumentoPlano`.

Admite lo que usan las redacciones: encabezados, párrafos, listas con viñeta o
número, tablas con barras y negritas o cursivas simples (se quitan los asteriscos).
Lo demás se conserva como párrafo.
"""
from __future__ import annotations

import re

from coopexecutive.documents.contenido import Bloque, DocumentoPlano, Lista, Parrafo, Tabla, Titulo

_ENCABEZADO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_VINETA = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+)$")
_SEPARADOR = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
_SUBTITULO = re.compile(r"^\*\*([^*]+)\*\*$")
_ENFASIS =re.compile(r"(\*\*|__)(.+?)\1|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")


def _limpio(texto: str) -> str:
    return _ENFASIS.sub(lambda m: m.group(2) or m.group(3), texto).strip()


def _celdas(linea: str) -> list[str]:
    return [_limpio(c) for c in linea.strip().strip("|").split("|")]


def a_plano(markdown: str, tipo: str, titulo: str = "") -> DocumentoPlano:
    """El primer encabezado de nivel 1 es el título si no se indica otro."""
    bloques: list[Bloque] = []
    subtitulo = ""
    parrafo: list[str] = []
    lista: list[str] = []
    tabla: list[list[str]] = []

    def cerrar() -> None:
        if parrafo:
            bloques.append(Parrafo("\n".join(parrafo)))
            parrafo.clear()
        if lista:
            bloques.append(Lista(list(lista)))
            lista.clear()
        if tabla:
            encabezados, *filas = tabla
            ancho = len(encabezados)
            filas = [(f + [""] * ancho)[:ancho] for f in filas]
            bloques.append(Tabla(encabezados, filas))
            tabla.clear()

    for linea in markdown.replace("\r\n", "\n").split("\n"):
        texto = linea.strip()
        if not texto or texto in {"---", "***", "___"}:
            cerrar()
            continue
        if texto.startswith("|"):
            if parrafo or lista:
                cerrar()
            if not _SEPARADOR.match(texto):
                tabla.append(_celdas(texto))
            continue
        if tabla:
            cerrar()
        encabezado = _ENCABEZADO.match(texto)
        if encabezado:
            cerrar()
            nivel, contenido = len(encabezado.group(1)), _limpio(encabezado.group(2))
            if nivel == 1 and not titulo:
                titulo = contenido
            else:
                bloques.append(Titulo(contenido, max(1, nivel - 1)))
            continue
        vineta = _VINETA.match(linea)
        if vineta:
            if parrafo:
                cerrar()
            lista.append(_limpio(vineta.group(1)))
            continue
        if lista:
            cerrar()
        # Una línea en negritas justo después del título es el subtítulo (así lo escribe `a_markdown`).
        negrita = _SUBTITULO.match(texto)
        if negrita and titulo and not bloques and not parrafo and not subtitulo:
            subtitulo = negrita.group(1).strip()
            continue
        parrafo.append(_limpio(texto))
    cerrar()
    return DocumentoPlano(tipo=tipo, titulo=titulo or tipo.replace("_", " ").capitalize(),
                          subtitulo=subtitulo, bloques=bloques)
