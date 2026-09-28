import sqlite3

import pytest

import coopexecutive.config as config
from coopexecutive.config import get_settings, usar_espacio
from coopexecutive.memory.episodic import MIGRACIONES, get_db_conn, initialize_db, version_esquema


@pytest.fixture
def sin_rutas_explicitas(monkeypatch):
    monkeypatch.delenv("COMPANY_PROFILE_PATH", raising=False)
    monkeypatch.delenv("EPISODIC_DB_PATH", raising=False)
    monkeypatch.setattr(config, "_settings", None)


def test_espacio_define_perfil_base_y_salidas(tmp_path, sin_rutas_explicitas):
    usar_espacio(tmp_path / "org")
    s = get_settings()
    assert s.workspace == (tmp_path / "org").resolve()
    assert s.company_profile_path == s.workspace / "profile.yaml"
    assert s.episodic_db_path == s.workspace / "coop_memory.db"
    assert s.salidas_dir == s.workspace / "salidas"


def test_variables_explicitas_tienen_prioridad(tmp_path, monkeypatch, sin_rutas_explicitas):
    monkeypatch.setenv("EPISODIC_DB_PATH", str(tmp_path / "otra.db"))
    usar_espacio(tmp_path / "org")
    s = get_settings()
    assert s.episodic_db_path == tmp_path / "otra.db"
    assert s.company_profile_path == s.workspace / "profile.yaml"


def test_sin_espacio_todo_sigue_igual(sin_rutas_explicitas, monkeypatch):
    monkeypatch.delenv("COOPEXECUTIVE_WORKSPACE", raising=False)
    s = get_settings()
    assert s.workspace is None
    assert s.salidas_dir == s.company_profile_path.parent / "salidas"


def test_migraciones_idempotentes(entorno_aislado):
    initialize_db()
    initialize_db()
    with get_db_conn() as conn:
        assert version_esquema(conn) == len(MIGRACIONES)
        tablas = {f["name"] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        columnas = {f["name"] for f in conn.execute("PRAGMA table_info(grant_evaluations)")}
    assert {"financiadores", "expedientes", "avances"} <= tablas
    assert {"resultado_json", "expediente_folio", "hash"} <= columnas


def test_indice_de_expediente_abierto(entorno_aislado):
    initialize_db()
    with get_db_conn() as conn:
        insertar = (
            "INSERT INTO expedientes (folio, tipo, entidad, entidad_normalizada, titulo) "
            "VALUES (?, 'Beca', 'X', 'x', 'Beca - X')"
        )
        conn.execute(insertar, ("EXP-2026-0001",))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insertar, ("EXP-2026-0002",))
