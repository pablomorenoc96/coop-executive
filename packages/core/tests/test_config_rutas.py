"""Búsqueda de `.env` y carpeta de usuario."""
from pathlib import Path

from click.testing import CliRunner

from coopexecutive import config
from coopexecutive.cli import cli
from coopexecutive.config import archivos_env, get_settings
from coopexecutive.utils import rutas
from coopexecutive.utils.rutas import carpeta_usuario


def test_carpeta_usuario_por_variable_appdata_y_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("COOPEXECUTIVE_HOME", str(tmp_path / "propia"))
    assert carpeta_usuario() == tmp_path / "propia"

    monkeypatch.delenv("COOPEXECUTIVE_HOME")
    monkeypatch.setattr(rutas.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert carpeta_usuario() == tmp_path / "Roaming" / "CoopExecutive"

    monkeypatch.setattr(rutas.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert carpeta_usuario() == tmp_path / "xdg" / "coopexecutive"


def test_env_file_explicito_o_vacio(tmp_path, monkeypatch):
    archivo = tmp_path / "otro.env"
    archivo.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.setenv("COOPEXECUTIVE_ENV_FILE", str(archivo))
    assert archivos_env() == [archivo]
    monkeypatch.setenv("COOPEXECUTIVE_ENV_FILE", str(tmp_path / "no-existe.env"))
    assert archivos_env() == []
    monkeypatch.setenv("COOPEXECUTIVE_ENV_FILE", "")
    assert archivos_env() == []


def test_orden_usuario_luego_directorio_actual_y_sin_duplicados(tmp_path, monkeypatch):
    usuario = tmp_path / "usuario"
    usuario.mkdir()
    (usuario / ".env").write_text("LOG_LEVEL=DEBUG\nDEFAULT_MODEL=modelo-usuario\n", encoding="utf-8")
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    (trabajo / ".env").write_text("DEFAULT_MODEL=modelo-local\n", encoding="utf-8")
    monkeypatch.delenv("COOPEXECUTIVE_ENV_FILE")
    monkeypatch.setenv("COOPEXECUTIVE_HOME", str(usuario))
    monkeypatch.setattr(config, "raiz_repositorio", lambda: None)
    monkeypatch.chdir(trabajo)

    assert archivos_env() == [(usuario / ".env").resolve(), (trabajo / ".env").resolve()]
    config._settings = None
    ajustes = get_settings()
    assert ajustes.default_model == "modelo-local"  # el directorio actual gana
    assert ajustes.log_level == "DEBUG"  # lo demás se hereda del de usuario

    # Si la carpeta de usuario es el directorio actual, el archivo no se repite.
    monkeypatch.setenv("COOPEXECUTIVE_HOME", str(trabajo))
    assert archivos_env() == [(trabajo / ".env").resolve()]


def test_info_muestra_los_env_cargados(entorno_aislado, monkeypatch):
    archivo = entorno_aislado / "prueba.env"
    archivo.write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    res = CliRunner().invoke(cli, ["info"])
    assert "ninguno" in res.output
    monkeypatch.setenv("COOPEXECUTIVE_ENV_FILE", str(archivo))
    config._settings = None
    res = CliRunner().invoke(cli, ["info"])
    assert res.exit_code == 0, res.output
    assert "prueba.env" in res.output.replace("\n", "")


def test_sin_checkout_el_perfil_va_a_la_carpeta_de_usuario(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_repositorio", lambda: None)
    monkeypatch.setenv("COOPEXECUTIVE_HOME", str(tmp_path))
    assert config._perfil_por_omision() == Path(tmp_path) / "profile.yaml"
    assert config._base_por_omision() == Path(tmp_path) / "coop_memory.db"
