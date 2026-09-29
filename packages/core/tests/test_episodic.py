"""Conexión a la base: rollback ante errores, claves foráneas y migraciones."""
import sqlite3

import pytest

from coopexecutive.memory.episodic import MIGRACIONES, get_db_conn, initialize_db


def test_error_deshace_la_transaccion(entorno_aislado):
    initialize_db()
    with pytest.raises(RuntimeError):
        with get_db_conn() as conn:
            conn.execute("INSERT INTO socios (socio_id, nombre) VALUES ('S1', 'Ana')")
            raise RuntimeError("falla a media operación")
    with get_db_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM socios").fetchone()[0] == 0


def test_sin_error_se_guarda(entorno_aislado):
    initialize_db()
    with get_db_conn() as conn:
        conn.execute("INSERT INTO socios (socio_id, nombre) VALUES ('S1', 'Ana')")
    with get_db_conn() as conn:
        assert conn.execute("SELECT nombre FROM socios").fetchone()[0] == "Ana"


def test_claves_foraneas_activas(entorno_aislado):
    initialize_db()
    with pytest.raises(sqlite3.IntegrityError):
        with get_db_conn() as conn:
            conn.execute(
                "INSERT INTO assembly_votes (proposal_id, member_id, member_name, choice) VALUES (999, 'S1', 'Ana', 'A_FAVOR')"
            )


def test_migraciones_al_dia_e_idempotentes(entorno_aislado):
    initialize_db()
    initialize_db()
    with get_db_conn() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRACIONES)
        columnas = {fila[1] for fila in conn.execute("PRAGMA table_info(assembly_proposals)")}
    assert {"cerrada_en", "resultado_json", "hash"} <= columnas
