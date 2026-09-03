"""Persistencia en SQLite para decisiones de asamblea, acuerdos, convocatorias y votaciones democráticas."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from coopexecutive.config import get_settings


@contextmanager
def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    env_db = os.environ.get("EPISODIC_DB_PATH")
    if env_db:
        db_path = Path(env_db)
    else:
        db_path = get_settings().episodic_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
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
