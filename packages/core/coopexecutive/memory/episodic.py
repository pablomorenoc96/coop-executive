"""Persistencia en SQLite: asamblea, evaluaciones, financiadores, expedientes y documentos.

Cada `get_db_conn()` confirma los cambios al salir sin error y los revierte si hay
una excepción. Las claves foráneas están activas.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from coopexecutive.config import get_settings


@contextmanager
def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    env_db = os.environ.get("EPISODIC_DB_PATH")
    if env_db:
        db_path = Path(env_db)
    else:
        db_path = get_settings().episodic_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db() -> None:
    with get_db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS assembly_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                decision_text TEXT NOT NULL,
                organ TEXT NOT NULL DEFAULT 'Asamblea General',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS grant_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_title TEXT NOT NULL,
                donor_agency TEXT NOT NULL,
                total_score REAL NOT NULL,
                recommendation TEXT NOT NULL,
                report_md TEXT NOT NULL,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assembly_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'subvencion',
                status TEXT NOT NULL DEFAULT 'abierta',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS assembly_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id INTEGER NOT NULL,
                member_id TEXT NOT NULL,
                member_name TEXT NOT NULL,
                choice TEXT NOT NULL,
                justification TEXT DEFAULT '',
                cast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(proposal_id, member_id),
                FOREIGN KEY (proposal_id) REFERENCES assembly_proposals(id)
            );
        """)
        _migrar(conn)


# Cada migración se aplica una sola vez; PRAGMA user_version guarda la última aplicada.
MIGRACIONES: tuple[str, ...] = (
    # 1. Núcleo de procuración: evaluaciones completas, financiadores y expedientes.
    """
    ALTER TABLE grant_evaluations ADD COLUMN resultado_json TEXT;
    ALTER TABLE grant_evaluations ADD COLUMN expediente_folio TEXT;
    ALTER TABLE grant_evaluations ADD COLUMN hash TEXT;

    CREATE TABLE IF NOT EXISTS financiadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio TEXT NOT NULL UNIQUE,
        organizacion TEXT NOT NULL,
        organizacion_normalizada TEXT NOT NULL UNIQUE,
        proyecto TEXT NOT NULL,
        tipo TEXT NOT NULL,
        canal TEXT NOT NULL,
        contacto TEXT NOT NULL DEFAULT '',
        moneda TEXT NOT NULL,
        monto_solicitado REAL,
        monto_comprometido REAL,
        monto_recibido REAL,
        estatus TEXT NOT NULL DEFAULT 'Prospecto',
        seguimiento TEXT,
        notas TEXT NOT NULL DEFAULT '',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS expedientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio TEXT NOT NULL UNIQUE,
        tipo TEXT NOT NULL,
        entidad TEXT NOT NULL,
        entidad_normalizada TEXT NOT NULL,
        titulo TEXT NOT NULL,
        objetivo TEXT NOT NULL DEFAULT '',
        responsable TEXT NOT NULL DEFAULT '',
        fecha_limite TEXT,
        monto REAL,
        moneda TEXT,
        abierto INTEGER NOT NULL DEFAULT 1,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_expediente_abierto
        ON expedientes (entidad_normalizada, tipo) WHERE abierto = 1;

    CREATE TABLE IF NOT EXISTS avances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_id INTEGER NOT NULL REFERENCES expedientes(id),
        estado TEXT NOT NULL,
        pendientes TEXT NOT NULL DEFAULT '',
        siguiente_accion TEXT NOT NULL DEFAULT '',
        origen TEXT NOT NULL,
        registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # 2. Documentos generados, con su huella y el expediente o la evaluación de origen.
    """
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_folio TEXT,
        evaluacion_id INTEGER,
        tipo TEXT NOT NULL,
        ruta TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # 3. Padrón de socios y cierre de propuestas con su resultado y huella completa.
    """
    CREATE TABLE IF NOT EXISTS socios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        alta_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        baja_en TIMESTAMP
    );
    ALTER TABLE assembly_proposals ADD COLUMN cerrada_en TIMESTAMP;
    ALTER TABLE assembly_proposals ADD COLUMN resultado_json TEXT;
    ALTER TABLE assembly_proposals ADD COLUMN hash TEXT;
    ALTER TABLE assembly_decisions ADD COLUMN proposal_id INTEGER REFERENCES assembly_proposals(id);
    """,
    # 4. Bitácora encadenada de acciones y último resultado de cada monitoreo.
    """
    CREATE TABLE IF NOT EXISTS bitacora (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registrado_en TEXT NOT NULL,
        canal TEXT NOT NULL,
        accion TEXT NOT NULL,
        parametros TEXT NOT NULL DEFAULT '{}',
        estado TEXT NOT NULL,
        resultado TEXT NOT NULL DEFAULT '',
        hash_previo TEXT NOT NULL,
        hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS monitoreos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ejecutado_en TEXT NOT NULL,
        temas TEXT NOT NULL,
        reporte_json TEXT NOT NULL
    );
    """,
)


def version_esquema(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _migrar(conn: sqlite3.Connection) -> None:
    actual = version_esquema(conn)
    for numero, script in enumerate(MIGRACIONES[actual:], start=actual + 1):
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {numero};\nCOMMIT;")
