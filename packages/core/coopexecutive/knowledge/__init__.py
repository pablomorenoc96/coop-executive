"""Búsqueda en la información de la organización y en el conocimiento incluido.

Fuentes, en este orden:
1. El perfil de la organización (`profile.yaml`).
2. La carpeta `conocimiento/` del espacio de trabajo (md, txt, html, docx y pdf).
3. Las guías incluidas en `knowledge/builtin/`.

La búsqueda es léxica (BM25 sobre palabras normalizadas), sin red ni modelo. Si
ningún pasaje comparte términos con la pregunta, la respuesta es que no consta.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from coopexecutive.utils.texto import normalizar

CARPETA_INCLUIDA = Path(__file__).resolve().parent / "builtin"
CARPETA_ESPACIO = "conocimiento"
EXTENSIONES = {".md", ".txt", ".html", ".htm", ".docx", ".pdf"}
TAMANO_PASAJE = 900
NO_CONSTA = "No consta en el perfil ni en los documentos de conocimiento."

_VACIAS = set(
    """a al ante con contra de del desde el en entre es esta este esto hacia hasta la las le les lo los
    mas me mi no nos o para pero por que qué se ser si sin sobre su sus te tiene tienen un una uno unos
    unas y ya cual cuál cuales cuáles como cómo cuando cuándo donde dónde quien quién hay son fue
    the of and to in for is on with""".split()
)


@dataclass(frozen=True)
class Pasaje:
    fuente: str
    titulo: str
    texto: str
    puntaje: float = 0.0


def _terminos(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if len(t) > 2 and t not in _VACIAS]


def _raiz(termino: str) -> str:
    """Raíz simple para que «becas» y «beca» coincidan."""
    for sufijo in ("ciones", "cion", "es", "s"):
        if termino.endswith(sufijo) and len(termino) - len(sufijo) >= 4:
            return termino[: -len(sufijo)]
    return termino


def partir(texto: str, fuente: str) -> list[Pasaje]:
    """Divide un documento en pasajes por encabezado y párrafo, de hasta ~900 caracteres."""
    pasajes: list[Pasaje] = []
    titulo = ""
    actual: list[str] = []

    def cerrar() -> None:
        cuerpo = "\n".join(actual).strip()
        if cuerpo:
            pasajes.append(Pasaje(fuente=fuente, titulo=titulo, texto=cuerpo))
        actual.clear()

    for bloque in re.split(r"\n\s*\n", texto):
        bloque = bloque.strip()
        if not bloque:
            continue
        encabezado = re.match(r"^#{1,6}\s+(.+)$", bloque.splitlines()[0])
        if encabezado:
            cerrar()
            titulo = encabezado.group(1).strip()
            bloque = "\n".join(bloque.splitlines()[1:]).strip()
            if not bloque:
                continue
        if actual and sum(len(p) for p in actual) + len(bloque) > TAMANO_PASAJE:
            cerrar()
        actual.append(bloque)
    cerrar()
    return pasajes


def _leer(ruta: Path) -> str:
    if ruta.suffix.lower() in {".md", ".txt"}:
        return ruta.read_text(encoding="utf-8", errors="replace")
    from coopexecutive.lectura import leer_archivo

    return leer_archivo(ruta)


def documentos(carpeta_espacio: Path | None = None, perfil: str = "") -> list[Pasaje]:
    """Todos los pasajes disponibles. Un archivo ilegible se omite sin detener la búsqueda."""
    pasajes: list[Pasaje] = []
    if perfil.strip():
        pasajes += partir(perfil, "Perfil de la organización")
    carpetas: list[tuple[Path, str]] = []
    if carpeta_espacio is not None and carpeta_espacio.is_dir():
        carpetas.append((carpeta_espacio, f"{CARPETA_ESPACIO}/"))
    carpetas.append((CARPETA_INCLUIDA, "incluido/"))
    for carpeta, prefijo in carpetas:
        for ruta in sorted(carpeta.rglob("*")):
            if not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES:
                continue
            try:
                texto = _leer(ruta)
            except (OSError, ValueError):
                continue
            pasajes += partir(texto, prefijo + ruta.relative_to(carpeta).as_posix())
    return pasajes


def buscar(pregunta: str, pasajes: list[Pasaje], limite: int = 4) -> list[Pasaje]:
    """Pasajes más pertinentes (BM25). Lista vacía si ninguno comparte términos."""
    consulta = {_raiz(t) for t in _terminos(pregunta)}
    if not consulta or not pasajes:
        return []
    bolsas = [Counter(_raiz(t) for t in _terminos(f"{p.titulo} {p.texto}")) for p in pasajes]
    n = len(bolsas)
    promedio = sum(sum(b.values()) for b in bolsas) / n or 1.0
    df = Counter(t for b in bolsas for t in consulta if t in b)
    k1, b_ = 1.5, 0.75
    resultados: list[Pasaje] = []
    for pasaje, bolsa in zip(pasajes, bolsas, strict=True):
        largo = sum(bolsa.values())
        puntaje = 0.0
        for termino in consulta:
            f = bolsa.get(termino, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[termino] + 0.5) / (df[termino] + 0.5))
            puntaje += idf * f * (k1 + 1) / (f + k1 * (1 - b_ + b_ * largo / promedio))
        if puntaje > 0:
            resultados.append(Pasaje(pasaje.fuente, pasaje.titulo, pasaje.texto, round(puntaje, 3)))
    resultados.sort(key=lambda p: p.puntaje, reverse=True)
    return resultados[:limite]
