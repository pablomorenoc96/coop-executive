"""Bitácora de acciones con huellas SHA-256 encadenadas.

Cada fila guarda el canal (cli, mcp, http o agente), la acción, los parámetros
censurados, el estado y un resumen del resultado. Su huella incluye la huella de la
fila anterior, así que borrar o editar una fila rompe la cadena y `verificar()` lo
detecta. Los parámetros nunca guardan claves, cuentas bancarias ni identificadores
fiscales.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from coopexecutive.guardrails.sensibles import limpiar_datos_sensibles
from coopexecutive.memory.episodic import get_db_conn, initialize_db

log = logging.getLogger(__name__)

CANALES = ("cli", "mcp", "http", "agente")
ESTADOS = ("ok", "error", "denegada")
GENESIS = "0" * 64
LARGO_MAXIMO = 300
SECRETO = "***"
_CLAVE_SECRETA = re.compile(r"clave|token|password|contrase|secret|api_?key|authorization", re.IGNORECASE)


@dataclass(frozen=True)
class Registro:
    id: int
    registrado_en: str
    canal: str
    accion: str
    parametros: dict[str, Any]
    estado: str
    resultado: str
    hash_previo: str
    hash: str


@dataclass(frozen=True)
class Verificacion:
    total: int
    roto_en: int | None = None
    motivo: str = ""

    @property
    def integra(self) -> bool:
        return self.roto_en is None


def _recortar(texto: str) -> str:
    return texto if len(texto) <= LARGO_MAXIMO else texto[: LARGO_MAXIMO - 3] + "..."


def censurar(valor: Any, clave: str = "") -> Any:
    """Copia de `valor` sin secretos ni datos sensibles, con textos recortados."""
    if clave and _CLAVE_SECRETA.search(clave):
        return SECRETO
    if isinstance(valor, dict):
        return {str(k): censurar(v, str(k)) for k, v in valor.items()}
    if isinstance(valor, list | tuple | set):
        return [censurar(v) for v in valor]
    if isinstance(valor, date | Path):
        valor = str(valor)
    if isinstance(valor, str):
        return _recortar(limpiar_datos_sensibles(valor))
    if valor is None or isinstance(valor, bool | int | float):
        return valor
    return _recortar(limpiar_datos_sensibles(str(valor)))


def _huella(registrado_en: str, canal: str, accion: str, parametros: str, estado: str, resultado: str,
            hash_previo: str) -> str:
    canonico = json.dumps(
        [registrado_en, canal, accion, parametros, estado, resultado, hash_previo],
        ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def registrar(canal: str, accion: str, parametros: dict[str, Any] | None = None, *, estado: str = "ok",
              resultado: str = "") -> Registro:
    if canal not in CANALES:
        raise ValueError(f"Canal no válido: {canal}.")
    if estado not in ESTADOS:
        raise ValueError(f"Estado no válido: {estado}.")
    params = json.dumps(censurar(parametros or {}), ensure_ascii=False, sort_keys=True)
    resultado = _recortar(limpiar_datos_sensibles(resultado))
    ahora = datetime.now(UTC).isoformat(timespec="seconds")
    initialize_db()
    with get_db_conn() as conn:
        # Reserva la escritura antes de leer la última huella: dos procesos no pueden encadenar la misma.
        conn.execute("BEGIN IMMEDIATE")
        ultima = conn.execute("SELECT hash FROM bitacora ORDER BY id DESC LIMIT 1").fetchone()
        previo = ultima["hash"] if ultima else GENESIS
        huella = _huella(ahora, canal, accion, params, estado, resultado, previo)
        cursor = conn.execute(
            "INSERT INTO bitacora (registrado_en, canal, accion, parametros, estado, resultado, hash_previo, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ahora, canal, accion, params, estado, resultado, previo, huella),
        )
        nuevo = int(cursor.lastrowid)
    return Registro(nuevo, ahora, canal, accion, json.loads(params), estado, resultado, previo, huella)


def registrar_sin_fallar(canal: str, accion: str, parametros: dict[str, Any] | None = None, *,
                         estado: str = "ok", resultado: str = "") -> Registro | None:
    """Como `registrar`, pero un fallo de la bitácora no detiene la acción: solo queda en el registro."""
    try:
        return registrar(canal, accion, parametros, estado=estado, resultado=resultado)
    except Exception as exc:  # noqa: BLE001 - la bitácora nunca debe tumbar el comando
        log.warning("No se pudo escribir en la bitácora: %s", exc)
        return None


def _registro(fila: Any) -> Registro:
    return Registro(
        id=fila["id"], registrado_en=fila["registrado_en"], canal=fila["canal"], accion=fila["accion"],
        parametros=json.loads(fila["parametros"] or "{}"), estado=fila["estado"], resultado=fila["resultado"],
        hash_previo=fila["hash_previo"], hash=fila["hash"],
    )


def ver(limite: int = 50, canal: str | None = None) -> list[Registro]:
    """Los registros más recientes primero."""
    initialize_db()
    with get_db_conn() as conn:
        if canal:
            filas = conn.execute("SELECT * FROM bitacora WHERE canal = ? ORDER BY id DESC LIMIT ?",
                                 (canal, limite)).fetchall()
        else:
            filas = conn.execute("SELECT * FROM bitacora ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [_registro(f) for f in filas]


def verificar() -> Verificacion:
    """Recalcula la cadena completa y señala la primera fila alterada."""
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute("SELECT * FROM bitacora ORDER BY id").fetchall()
    previo = GENESIS
    for fila in filas:
        if fila["hash_previo"] != previo:
            return Verificacion(len(filas), fila["id"], "no enlaza con la fila anterior (se borró o se editó una fila)")
        esperada = _huella(fila["registrado_en"], fila["canal"], fila["accion"], fila["parametros"],
                           fila["estado"], fila["resultado"], fila["hash_previo"])
        if fila["hash"] != esperada:
            return Verificacion(len(filas), fila["id"], "su contenido no coincide con su huella")
        previo = fila["hash"]
    return Verificacion(len(filas))


def exportar_jsonl(destino: Path) -> int:
    """Escribe todos los registros, del más antiguo al más reciente. Nunca sobrescribe un archivo."""
    initialize_db()
    with get_db_conn() as conn:
        filas = conn.execute("SELECT * FROM bitacora ORDER BY id").fetchall()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "x", encoding="utf-8", newline="\n") as archivo:
        for fila in filas:
            archivo.write(json.dumps(_registro(fila).__dict__, ensure_ascii=False) + "\n")
    return len(filas)
