"""Documentos Word con el membrete de cada organización.

El proceso es: armar el contenido, mostrar la vista previa, confirmar y guardar. El
archivo va a ``salidas/AAAA/<folio>/`` sin sobrescribir ninguno anterior, y queda
registrado con su huella SHA-256 (y el expediente, si lo hay).
"""
from __future__ import annotations

import hashlib
import io
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from coopexecutive.documents.contenido import DocumentoPlano, a_markdown
from coopexecutive.documents.formato import a_docx
from coopexecutive.memory.company_profile import Membrete
from coopexecutive.memory.episodic import get_db_conn, initialize_db

CARPETA_SIN_EXPEDIENTE = "general"

__all__ = ["DocumentoPlano", "DocumentoGuardado", "a_markdown", "guardar", "documentos_de", "recientes"]


class DocumentoGuardado(BaseModel):
    id: int
    tipo: str
    ruta: str
    sha256: str
    expediente_folio: str | None = None
    evaluacion_id: int | None = None
    creado_en: str = ""


def ruta_libre(carpeta: Path, nombre: str, extension: str = ".docx") -> Path:
    """Primera ruta que no existe: nombre.docx, nombre-2.docx, nombre-3.docx..."""
    candidata, n = carpeta / f"{nombre}{extension}", 2
    while candidata.exists():
        candidata = carpeta / f"{nombre}-{n}{extension}"
        n += 1
    return candidata


def guardar(
    plano: DocumentoPlano,
    membrete: Membrete,
    carpeta_perfil: Path,
    salidas: Path,
    hoy: date,
    *,
    autor: str = "",
    expediente_folio: str | None = None,
    evaluacion_id: int | None = None,
) -> DocumentoGuardado:
    """Escribe el Word y lo registra. Nunca reemplaza un archivo existente."""
    documento = a_docx(plano, membrete, carpeta_perfil, autor=autor)
    memoria = io.BytesIO()
    documento.save(memoria)
    contenido = memoria.getvalue()

    carpeta = salidas / str(hoy.year) / (expediente_folio or CARPETA_SIN_EXPEDIENTE)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = ruta_libre(carpeta, f"{hoy.isoformat()}_{plano.tipo}")
    # «x» falla si el archivo apareció entre la búsqueda y la escritura.
    with open(destino, "xb") as archivo:
        archivo.write(contenido)
    huella = hashlib.sha256(contenido).hexdigest()

    initialize_db()
    with get_db_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documentos (expediente_folio, evaluacion_id, tipo, ruta, sha256)
            VALUES (?, ?, ?, ?, ?)
            """,
            (expediente_folio, evaluacion_id, plano.tipo, str(destino), huella),
        )
        conn.commit()
        fila = conn.execute("SELECT * FROM documentos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return DocumentoGuardado(**dict(fila))


def documentos_de(folio: str) -> list[DocumentoGuardado]:
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute(
            "SELECT * FROM documentos WHERE expediente_folio = ? ORDER BY id", (folio.strip().upper(),)
        ).fetchall()
    return [DocumentoGuardado(**dict(f)) for f in filas]


def recientes(limite: int = 50) -> list[DocumentoGuardado]:
    """Los documentos generados más recientes, de cualquier expediente."""
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute("SELECT * FROM documentos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [DocumentoGuardado(**dict(f)) for f in filas]
