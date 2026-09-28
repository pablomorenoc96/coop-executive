from io import StringIO

import pytest
from click.testing import CliRunner
from rich.console import Console
from rich.text import Text

from coopexecutive.cli import cli
from coopexecutive.identidad import (
    INTRO_INCLUIDA,
    ancho_intro,
    generar_para_perfil,
    mostrar_intro,
)
from coopexecutive.identidad.generador import CUADRANTES, a_cuadrantes, generar_intro
from coopexecutive.memory.company_profile import CoopProfile, Identidad

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402


def _logo(ruta, color=(124, 58, 237, 255), fondo=(0, 0, 0, 0)):
    im = Image.new("RGBA", (200, 200), fondo)
    ImageDraw.Draw(im).ellipse([20, 20, 180, 180], fill=color)
    im.save(ruta)
    return ruta


def _consola(ancho: int) -> Console:
    return Console(file=StringIO(), width=ancho, color_system=None, legacy_windows=False)


def test_mapa_de_cuadrantes():
    # Un carácter es el doble de alto que de ancho: un cuadrado de 2 filas ocupa 4 columnas.
    lleno = Image.new("L", (4, 4), 255)
    assert a_cuadrantes(lleno, 2) == ["████", "████"]
    diagonal = Image.new("L", (2, 2), 0)
    diagonal.putpixel((0, 0), 255)
    diagonal.putpixel((1, 1), 255)
    assert a_cuadrantes(diagonal, 1) == ["▀▄"]
    assert CUADRANTES[0b1111] == "█" and CUADRANTES[0b0011] == "▄" and CUADRANTES[0b1100] == "▀"


def test_intro_respeta_ancho_y_colores(tmp_path):
    texto = generar_intro("Cooperativa Ejemplo", logo=_logo(tmp_path / "logo.png"), lema="Lema de prueba")
    assert ancho_intro(texto) <= 78
    assert "[#7C3AED]" in texto  # color medio del logo
    assert "Lema de prueba" in Text.from_markup(texto).plain
    assert "[bold]" in texto


def test_logo_negro_usa_color_de_la_terminal(tmp_path):
    texto = generar_intro("Org", logo=_logo(tmp_path / "negro.png", color=(0, 0, 0, 255)))
    assert "[#" not in texto


def test_logo_con_fondo_opaco(tmp_path):
    ruta = _logo(tmp_path / "opaco.png", color=(16, 185, 129, 255), fondo=(255, 255, 255, 255))
    texto = generar_intro("Org", logo=ruta, filas_logo=6)
    lineas_logo = [l for l in texto.splitlines() if l.startswith("[#10B981]")]
    assert len(lineas_logo) >= 5


def test_generar_para_perfil_respalda_la_intro_anterior(tmp_path):
    _logo(tmp_path / "logo.png")
    perfil = CoopProfile(name="Organización Ejemplo", identidad=Identidad(nombre_corto="ORG", logo="logo.png"))
    (tmp_path / "intro.txt").write_text("anterior", encoding="utf-8")
    destino = generar_para_perfil(perfil, tmp_path)
    assert destino.read_text(encoding="utf-8") != "anterior"
    respaldos = list(tmp_path.glob("intro.txt.bak-*"))
    assert len(respaldos) == 1 and respaldos[0].read_text(encoding="utf-8") == "anterior"


def test_logo_inexistente_falla_con_mensaje(tmp_path):
    perfil = CoopProfile(identidad=Identidad(logo="no_existe.png"))
    with pytest.raises(FileNotFoundError, match="no_existe.png"):
        generar_para_perfil(perfil, tmp_path)


def test_color_invalido_se_rechaza():
    with pytest.raises(ValueError, match="hexadecimal"):
        Identidad(color_logo="morado")
    assert Identidad(color_logo="#7c3aed").color_logo == "#7C3AED"


def test_mostrar_intro_incluida_o_propia(tmp_path):
    perfil = CoopProfile(name="Organización Ejemplo")
    consola = _consola(100)
    mostrar_intro(consola, perfil, tmp_path)
    incluida = Text.from_markup(INTRO_INCLUIDA.read_text(encoding="utf-8")).plain
    assert incluida.splitlines()[1].strip() in consola.file.getvalue()

    (tmp_path / "intro.txt").write_text("[bold]PROPIA[/]\n", encoding="utf-8")
    consola = _consola(100)
    mostrar_intro(consola, perfil, tmp_path)
    assert "PROPIA" in consola.file.getvalue()


def test_terminal_angosta_muestra_solo_el_nombre(tmp_path):
    perfil = CoopProfile(name="Organización Ejemplo", identidad=Identidad(nombre_corto="ORG"))
    (tmp_path / "intro.txt").write_text("█" * 90 + "\n", encoding="utf-8")
    consola = _consola(60)
    mostrar_intro(consola, perfil, tmp_path)
    assert consola.file.getvalue().strip() == "ORG"


def test_intro_incluida_cabe_en_80_columnas():
    assert ancho_intro(INTRO_INCLUIDA.read_text(encoding="utf-8")) <= 78


def test_cli_intro_generar_y_sin_subcomando(entorno_aislado):
    _logo(entorno_aislado / "logo.png")
    perfil = entorno_aislado / "profile.yaml"
    perfil.write_text(
        perfil.read_text(encoding="utf-8") + 'identidad:\n  nombre_corto: "CP"\n  logo: "logo.png"\n',
        encoding="utf-8",
    )
    runner = CliRunner()
    r = runner.invoke(cli, ["intro", "generar"])
    assert r.exit_code == 0, r.output
    assert (entorno_aislado / "intro.txt").exists()

    r = runner.invoke(cli, [])
    assert r.exit_code == 0, r.output
    assert "█" in r.output or "▄" in r.output
    assert "Commands:" in r.output or "Comandos" in r.output
