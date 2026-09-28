"""Intro de la terminal con la identidad de la organización.

Mostrar la intro no requiere Pillow: se lee ``intro.txt`` junto al perfil o, si no
existe, la intro incluida de CoopExecutive. Generarla sí lo requiere (ver ``generador``).
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.text import Text

from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.utils.rutas import resolver_archivo

ARCHIVO_INTRO = "intro.txt"
INTRO_INCLUIDA = Path(__file__).with_name("intro_coopexecutive.txt")
NOMBRE_INCLUIDO = "CoopExecutive"


def ruta_intro(carpeta_perfil: Path) -> Path:
    return carpeta_perfil / ARCHIVO_INTRO


def generar_para_perfil(perfil: CoopProfile, carpeta_perfil: Path) -> Path:
    """Genera ``intro.txt`` con el logo, la fuente y el lema del perfil.

    Si ya existe, se respalda antes de escribir. Devuelve la ruta del archivo.
    """
    from coopexecutive.identidad.generador import generar_intro
    from coopexecutive.memory.onboarding import respaldar

    ident = perfil.identidad
    texto = generar_intro(
        texto=ident.nombre_corto.strip() or perfil.name,
        logo=resolver_archivo(ident.logo, carpeta_perfil),
        fuente=resolver_archivo(ident.fuente, carpeta_perfil),
        lema=ident.lema.strip(),
        color_logo=ident.color_logo,
        color_texto=ident.color_texto,
    )
    destino = ruta_intro(carpeta_perfil)
    respaldar(destino)
    # Fin de línea LF en todas las plataformas: el archivo es el mismo en Windows y Linux.
    destino.write_text(texto, encoding="utf-8", newline="\n")
    return destino


def ancho_intro(texto: str) -> int:
    return max((len(Text.from_markup(linea).plain) for linea in texto.splitlines()), default=0)


def mostrar_intro(console: Console, perfil: CoopProfile, carpeta_perfil: Path) -> None:
    """Muestra la intro de la organización o la de CoopExecutive.

    En una terminal más angosta que el dibujo se muestra solo el nombre.
    """
    propia = ruta_intro(carpeta_perfil)
    if propia.exists():
        texto = propia.read_text(encoding="utf-8")
        nombre = perfil.identidad.nombre_corto.strip() or perfil.name
    else:
        texto = INTRO_INCLUIDA.read_text(encoding="utf-8")
        nombre = NOMBRE_INCLUIDO
    console.print()
    if console.width < ancho_intro(texto):
        console.print(f"[bold]{nombre}[/bold]", highlight=False)
    else:
        console.print(Text.from_markup(texto.rstrip("\n")), highlight=False)
    console.print()
