"""Coincidencia de avisos con los temas de la organización, en español e inglés.

Cada tema se parte en palabras significativas («Energía eólica» -> energia, eolica).
Una palabra coincide si alguna de sus formas aparece al inicio de una palabra del
aviso; así «energ» encuentra energía, energético y energy. Las equivalencias en
inglés permiten leer portales internacionales con temas escritos en español.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from coopexecutive.utils.texto import normalizar

VACIAS = {
    "para", "como", "entre", "sobre", "desde", "hacia", "con", "sin", "por", "del", "las", "los",
    "una", "uno", "and", "the", "for", "with", "from", "into",
}

# Raíz en español -> raíces equivalentes (se comparan como prefijos de palabra).
EQUIVALENCIAS = {
    "energ": ["energ"],
    "eolic": ["wind", "eolic"],
    "solar": ["solar", "photovolt", "fotovolt"],
    "renovabl": ["renewabl", "clean energ"],
    "automatiz": ["automat"],
    "potencia": ["power"],
    "control": ["control"],
    "electr": ["electr"],
    "ingenier": ["engineer"],
    "tecnic": ["technic", "technolog"],
    "innovaci": ["innovat"],
    "tecnolog": ["technolog", "tech"],
    "cienci": ["scien", "research"],
    "investigaci": ["research"],
    "clima": ["climat"],
    "ambient": ["environment"],
    "agua": ["water"],
    "agric": ["agricult", "farm"],
    "rural": ["rural"],
    "comunit": ["communit"],
    "comunidad": ["communit"],
    "cooperativ": ["cooperativ", "co op"],
    "econom": ["econom"],
    "emprend": ["entrepreneur", "startup", "start up"],
    "empresa": ["business", "enterprise", "sme"],
    "pyme": ["sme", "small business"],
    "educaci": ["educat"],
    "formaci": ["training"],
    "capacitaci": ["training"],
    "beca": ["scholarship", "fellowship"],
    "posgrado": ["postgraduate", "graduate", "master", "phd", "doctoral"],
    "maestri": ["master"],
    "doctorado": ["phd", "doctoral"],
    "titulaci": ["degree", "graduation"],
    "salud": ["health"],
    "genero": ["gender", "women"],
    "mujer": ["women", "female"],
    "juvent": ["youth", "young"],
    "jovenes": ["youth", "young"],
    "derech": ["rights"],
    "digital": ["digital"],
    "ciberseg": ["cyber"],
    "cultur": ["cultur", "arts"],
    "vivienda": ["housing"],
    "migra": ["migra", "refugee"],
    "indigen": ["indigenous"],
}


@dataclass(frozen=True)
class Palabra:
    etiqueta: str            # palabra del tema tal como se escribió
    formas: tuple[str, ...]  # prefijos que la representan


@dataclass(frozen=True)
class Tema:
    nombre: str
    palabras: tuple[Palabra, ...]


@dataclass(frozen=True)
class Coincidencia:
    palabras: list[str]  # palabras halladas
    temas: list[str]     # temas con todas sus palabras halladas

    def __bool__(self) -> bool:
        return bool(self.palabras)


def _formas(palabra: str) -> tuple[str, ...]:
    formas = {palabra}
    for raiz, equivalentes in EQUIVALENCIAS.items():
        if palabra.startswith(raiz):
            formas.add(raiz)
            formas.update(equivalentes)
    return tuple(sorted(formas))


def preparar_temas(temas: list[str]) -> list[Tema]:
    """Cada tema con sus palabras significativas; los temas sin ellas se omiten."""
    preparados: list[Tema] = []
    for tema in temas:
        # Se compara la forma normalizada y se muestra la original («formación»).
        originales = {normalizar(p): p.lower() for p in re.findall(r"\w+", tema)}
        palabras = [p for p in originales if len(p) >= 4 and p not in VACIAS]
        if palabras:
            preparados.append(Tema(tema.strip(), tuple(Palabra(originales[p], _formas(p)) for p in palabras)))
    return preparados


def coincidencias(texto: str, temas: list[Tema]) -> Coincidencia:
    """Palabras de los temas que aparecen en el texto y temas completos."""
    limpio = " " + normalizar(texto)
    halladas: dict[str, bool] = {}
    completos: list[str] = []
    for tema in temas:
        presentes = []
        for palabra in tema.palabras:
            if palabra.etiqueta not in halladas:
                halladas[palabra.etiqueta] = any(
                    re.search(rf" {re.escape(forma)}", limpio) for forma in palabra.formas
                )
            presentes.append(halladas[palabra.etiqueta])
        if all(presentes):
            completos.append(tema.nombre)
    return Coincidencia([p for p, si in halladas.items() if si], completos)
