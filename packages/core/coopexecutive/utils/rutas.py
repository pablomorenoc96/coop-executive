"""Rutas de archivos declaradas en el perfil."""
from __future__ import annotations

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
