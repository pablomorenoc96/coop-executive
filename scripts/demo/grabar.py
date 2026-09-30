"""Graba assets/demo.gif y assets/demo_en.gif con la salida real de la CLI.

Cada paso corre de verdad en un espacio temporal, sin modelo ni red: lo que se ve es lo que
imprime el programa. Solo cambian el pie de cada paso (español o inglés) y el ritmo.

Uso, desde la raíz del repositorio (necesita ffmpeg en el PATH):

    uv run --project packages/core --all-extras python scripts/demo/grabar.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text

RAIZ = Path(__file__).resolve().parents[2]
EJEMPLOS = RAIZ / "company" / "examples"
COLUMNAS, FILAS = 96, 30
TAM, INTERLINEA, MARGEN, BARRA, PIE = 15, 19, 18, 34, 44
FPS = 12

TEMA = TerminalTheme(
    (22, 27, 34), (230, 237, 243),
    [(22, 27, 34), (255, 123, 114), (86, 211, 100), (227, 179, 65), (121, 192, 255), (210, 168, 255),
     (86, 212, 221), (201, 209, 217)],
    [(110, 118, 129), (255, 161, 152), (126, 231, 135), (242, 204, 96), (165, 214, 255), (226, 197, 255),
     (129, 226, 234), (240, 246, 252)],
)
FONDO, TEXTO, APAGADO, ACENTO = (13, 17, 23), (230, 237, 243), (139, 148, 158), (86, 211, 100)


@dataclass(frozen=True)
class Paso:
    comando: str               # lo que se ve escrito en la terminal
    argumentos: list[str] | None  # None: solo se escribe (p. ej. export); no corre nada
    es: str
    en: str
    lineas_por_cuadro: int = 3
    pausa: float = 2.6


PASOS = [
    Paso('coopexecutive iniciar mi-org --nombre "Energía Solidaria del Valle" --tipo asociacion_civil',
         ["iniciar", "mi-org", "--nombre", "Energía Solidaria del Valle", "--tipo", "asociacion_civil"],
         "Un espacio por organización: perfil, base de datos y salidas fuera del repositorio.",
         "One workspace per organisation: profile, database and outputs outside the repository.", pausa=2.2),
    Paso("export COOPEXECUTIVE_WORKSPACE=mi-org", None,
         "Los comandos siguientes trabajan sobre ese espacio.",
         "The next commands work on that workspace.", pausa=1.2),
    Paso("coopexecutive configurar --desde respuestas_perfil.yaml", ["configurar", "--desde", "respuestas_perfil.yaml"],
         "El perfil se llena con sus respuestas; lo que falta queda [PENDIENTE], nunca inventado.",
         "The profile is filled from your answers; missing data stays [PENDIENTE], never invented.", 4, 3.2),
    Paso('coopexecutive expedientes abrir "Fundación Ejemplo" --tipo Convocatoria',
         ["expedientes", "abrir", "Fundación Ejemplo", "--tipo", "Convocatoria"],
         "Cada oportunidad tiene su expediente; sin monto confirmado dice MONTO POR DEFINIR.",
         "Each opportunity gets a case file; without a confirmed amount it says MONTO POR DEFINIR."),
    Paso("coopexecutive evaluar-convocatoria --archivo convocatoria.yaml --expediente EXP-2026-0001",
         ["evaluar-convocatoria", "--archivo", "convocatoria.yaml", "--expediente", "EXP-2026-0001"],
         "Matriz de 100 puntos calculada en código: cada puntaje con evidencia, contrapunto y huella SHA-256.",
         "100-point matrix computed in code: every score with evidence, a counterpoint and a SHA-256 hash.", 4, 3.4),
    Paso("coopexecutive evaluar-convocatoria --archivo segunda.yaml",
         ["evaluar-convocatoria", "--archivo", "segunda.yaml"],
         "Una segunda convocatoria, con menos puntaje y cierre cercano.",
         "A second call, with a lower score and a close deadline.", 8, 1.4),
    Paso("coopexecutive comparar-convocatorias", ["comparar-convocatorias"],
         "Compara lo evaluado con los días recalculados para hoy y dice qué atender primero.",
         "Compares saved evaluations with days recomputed for today and says what to handle first.", 3, 3.4),
    Paso('coopexecutive fecha --cierre 2026-10-09 --cierre "30 de octubre de 2026"',
         ["fecha", "--cierre", "2026-10-09", "--cierre", "30 de octubre de 2026"],
         "Fecha de hoy en su zona horaria y días naturales a cada cierre.",
         "Today in your time zone and calendar days to each deadline."),
    Paso("coopexecutive documento ficha --expediente EXP-2026-0001 --si",
         ["documento", "ficha", "--expediente", "EXP-2026-0001", "--si"],
         "Word con el membrete de la organización, guardado sin sobrescribir y ligado al expediente.",
         "A Word file with the organisation's letterhead, never overwritten and linked to the case."),
    Paso("coopexecutive bitacora ver", ["bitacora", "ver"],
         "Cada acción queda en una bitácora encadenada con SHA-256.",
         "Every action is kept in a SHA-256 chained audit log.", 3, 2.4),
    Paso("coopexecutive bitacora verificar", ["bitacora", "verificar"],
         "Si alguien altera o borra un registro, la verificación lo detecta.",
         "If a record is altered or deleted, verification catches it.", pausa=3.4),
]


def _fuente(negrita: bool = False, mono: bool = True, tam: int = TAM) -> ImageFont.FreeTypeFont:
    nombre = ("DejaVuSansMono" if mono else "DejaVuSans") + ("-Bold" if negrita else "")
    for carpeta in (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path("/usr/share/fonts/truetype/dejavu"),
                    Path("/Library/Fonts")):
        if (carpeta / f"{nombre}.ttf").is_file():
            return ImageFont.truetype(str(carpeta / f"{nombre}.ttf"), tam)
    return ImageFont.truetype(f"{nombre}.ttf", tam)


MONO, MONO_B = _fuente(), _fuente(True)
PIE_F, TITULO_F = _fuente(mono=False, tam=15), _fuente(True, mono=False, tam=13)
ANCHO_CAR = MONO.getlength("M")
CONSOLA = Console(width=COLUMNAS, color_system="truecolor")
ANCHO = int(MARGEN * 2 + ANCHO_CAR * COLUMNAS)
ALTO = BARRA + MARGEN + INTERLINEA * FILAS + MARGEN // 2 + PIE


def correr(paso: Paso, espacio: Path) -> list[Text]:
    entorno = {**os.environ, "COLUMNS": str(COLUMNAS), "FORCE_COLOR": "1", "TERM": "xterm-256color",
               "PYTHONIOENCODING": "utf-8", "COOPEXECUTIVE_ENV_FILE": "", "COOPEXECUTIVE_HOME": str(espacio / ".usuario"),
               "USER_TIMEZONE": "America/Mexico_City"}
    for variable in ("COOPEXECUTIVE_WORKSPACE", "EPISODIC_DB_PATH", "COMPANY_PROFILE_PATH"):
        entorno.pop(variable, None)
    if paso.argumentos[0] != "iniciar":
        entorno["COOPEXECUTIVE_WORKSPACE"] = "mi-org"
    r = subprocess.run([sys.executable, "-m", "coopexecutive", *paso.argumentos], cwd=espacio, env=entorno,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"Falló «{paso.comando}»:\n{r.stdout}\n{r.stderr}")
    salida = r.stdout.rstrip("\n")
    if str(espacio) in salida:
        raise SystemExit(f"La salida de «{paso.comando}» muestra la ruta temporal; no se graba.")
    return [Text.from_ansi(linea) for linea in salida.split("\n")]


def _color(estilo, fondo: bool = False) -> tuple[int, int, int] | None:
    color = estilo.bgcolor if fondo else estilo.color
    if color is None or color.is_default:
        return None
    return tuple(color.get_truecolor(TEMA, foreground=not fondo))


def dibujar(lineas: list[Text], pie: str, numero: str) -> Image.Image:
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ANCHO, BARRA], fill=(33, 38, 45))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([14 + i * 20, 11, 26 + i * 20, 23], fill=c)
    titulo = "coopexecutive"
    d.text(((ANCHO - TITULO_F.getlength(titulo)) / 2, 9), titulo, font=TITULO_F, fill=APAGADO)
    y = BARRA + MARGEN
    for linea in lineas[-FILAS:]:
        x = MARGEN
        for segmento in linea.render(CONSOLA):
            estilo = segmento.style
            fuente = MONO_B if estilo and estilo.bold else MONO
            color = (_color(estilo) if estilo else None) or TEXTO
            if estilo and estilo.dim:
                color = tuple(int(c * 0.6) for c in color)
            texto = segmento.text
            ancho = ANCHO_CAR * len(texto)
            fondo = _color(estilo, fondo=True) if estilo else None
            if fondo:
                d.rectangle([x, y - 2, x + ancho, y + INTERLINEA - 3], fill=fondo)
            for j, caracter in enumerate(texto):  # carácter por carácter: la rejilla no se desalinea
                d.text((x + j * ANCHO_CAR, y), caracter, font=fuente, fill=color)
            if estilo and estilo.underline:
                d.line([x, y + TAM + 1, x + ancho, y + TAM + 1], fill=color)
            x += ancho
        y += INTERLINEA
    arriba = ALTO - PIE
    d.rectangle([0, arriba, ANCHO, ALTO], fill=(22, 27, 34))
    d.line([0, arriba, ANCHO, arriba], fill=(48, 54, 61))
    d.text((MARGEN, arriba + 13), numero, font=PIE_F, fill=ACENTO)
    d.text((MARGEN + 52, arriba + 13), pie, font=PIE_F, fill=TEXTO)
    return img


def _prompt(texto: str, cursor: bool) -> Text:
    t = Text("$ ", style="bold green")
    t.append(texto, style="bold white")
    if cursor:
        t.append("▌", style="white")
    return t


def cuadros(salidas: list[list[Text]], idioma: str):
    """Genera (imagen, segundos) para cada estado visible de la pantalla."""
    pantalla: list[Text] = []
    for n, (paso, salida) in enumerate(zip(PASOS, salidas, strict=True), start=1):
        pie, numero = (paso.es if idioma == "es" else paso.en), f"{n}/{len(PASOS)}"
        for fin in range(0, len(paso.comando) + 1, 3):
            yield dibujar([*pantalla, _prompt(paso.comando[:fin], True)], pie, numero), 1 / FPS
        pantalla.append(_prompt(paso.comando, False))
        yield dibujar(pantalla, pie, numero), 0.35
        for i in range(0, len(salida), paso.lineas_por_cuadro):
            pantalla.extend(salida[i:i + paso.lineas_por_cuadro])
            yield dibujar(pantalla, pie, numero), 1 / FPS
        pantalla.append(Text(""))
        yield dibujar(pantalla, pie, numero), paso.pausa


def armar_gif(salidas: list[list[Text]], idioma: str, destino: Path, trabajo: Path) -> None:
    carpeta = trabajo / idioma
    carpeta.mkdir()
    lista = []
    for i, (img, segundos) in enumerate(cuadros(salidas, idioma)):
        archivo = carpeta / f"{i:04d}.png"
        img.save(archivo)
        lista.append(f"file '{archivo.as_posix()}'\nduration {segundos:.3f}")
    lista.append(f"file '{archivo.as_posix()}'")  # el concat de ffmpeg ignora la duración del último
    (carpeta / "lista.txt").write_text("\n".join(lista) + "\n", encoding="utf-8")
    filtro = "fps=12,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(carpeta / "lista.txt"),
                    "-vf", filtro, "-loop", "0", str(destino)], check=True)
    print(f"{destino.relative_to(RAIZ)}: {destino.stat().st_size / 1e6:.1f} MB, {len(lista) - 1} cuadros")


def main() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("Hace falta ffmpeg en el PATH.")
    with tempfile.TemporaryDirectory(prefix="coopexecutive-demo-") as tmp:
        espacio = Path(tmp)
        shutil.copy(EJEMPLOS / "respuestas_perfil.yaml", espacio / "respuestas_perfil.yaml")
        shutil.copy(EJEMPLOS / "convocatoria_ejemplo.yaml", espacio / "convocatoria.yaml")
        segunda = (EJEMPLOS / "convocatoria_ejemplo.yaml").read_text(encoding="utf-8")
        for antes, despues in [("Fondo de Energía Comunitaria 2026", "Programa Regional de Innovación Social"),
                               ('"Fundación Ejemplo"', '"Agencia de Cooperación Ejemplo"'),
                               ("dias_restantes: 40", "dias_restantes: 9"), ("puntos: 18", "puntos: 14"),
                               ("tiempos:      {puntos: 9,  evidencia: \"Faltan más de 28 días para el cierre.\"}",
                                "tiempos:      {puntos: 4,  evidencia: \"Faltan 9 días para el cierre.\"}")]:
            assert antes in segunda, antes
            segunda = segunda.replace(antes, despues)
        (espacio / "segunda.yaml").write_text(segunda, encoding="utf-8")
        salidas = [correr(p, espacio) if p.argumentos else [] for p in PASOS]
        trabajo = espacio / "cuadros"
        trabajo.mkdir()
        armar_gif(salidas, "es", RAIZ / "assets" / "demo.gif", trabajo)
        armar_gif(salidas, "en", RAIZ / "assets" / "demo_en.gif", trabajo)


if __name__ == "__main__":
    main()
