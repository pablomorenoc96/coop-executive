"""Rutas de archivos declaradas en el perfil."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def resolver_archivo(ruta: str, carpeta_perfil: Path) -> Path | None:
    """Ruta absoluta de un archivo del perfil; las relativas parten de la carpeta del perfil.

    Vacío significa que no se declaró. Si se declaró y no existe, falla con la ruta completa.
    """
    if not ruta.strip():
        return None
    candidata = Path(ruta.strip()).expanduser()
    if not candidata.is_absolute():
        candidata = carpeta_perfil / candidata
    if not candidata.exists():
        raise FileNotFoundError(f"No existe el archivo {candidata}.")
    return candidata


def raiz_repositorio() -> Path | None:
    """Raíz del repositorio si el paquete corre desde un checkout; None si está instalado como wheel."""
    raiz = Path(__file__).resolve().parents[4]
    return raiz if (raiz / "packages" / "core" / "pyproject.toml").is_file() else None


def carpeta_usuario() -> Path:
    """Carpeta de configuración del usuario: `%APPDATA%/CoopExecutive` o `~/.config/coopexecutive`.

    `COOPEXECUTIVE_HOME` la sustituye (útil en pruebas y en equipos compartidos).
    """
    propia = os.environ.get("COOPEXECUTIVE_HOME")
    if propia:
        return Path(propia).expanduser()
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "CoopExecutive"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "coopexecutive"


def para_mostrar(ruta: Path | str) -> str:
    """Ruta relativa a la carpeta actual si está dentro de ella; si no, la absoluta."""
    absoluta = Path(ruta).resolve()
    try:
        return str(absoluta.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(absoluta)
