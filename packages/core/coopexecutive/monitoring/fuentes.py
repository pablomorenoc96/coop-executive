"""Catálogo de fuentes: las incluidas en el paquete más las del espacio de trabajo."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

FUENTES_INCLUIDAS = Path(__file__).resolve().parents[1] / "knowledge" / "builtin" / "procuracion_fondos" / "fuentes.yaml"
ARCHIVO_FUENTES = "fuentes.yaml"


def _url(v: str) -> str:
    v = v.strip()
    if v and not v.startswith(("https://", "http://")):
        raise ValueError(f"«{v}» no es una dirección http(s).")
    return v


class Fuente(BaseModel):
    nombre: str
    tipo: str = ""
    region: str = ""
    idioma: str = "es"
    url: str = ""
    rss: str = ""

    @field_validator("url", "rss")
    @classmethod
    def _direccion(cls, v: str) -> str:
        return _url(v)

    @property
    def automatica(self) -> bool:
        """Solo las fuentes con canal RSS o Atom se leen de forma automática."""
        return bool(self.rss)


class Catalogo(BaseModel):
    fuentes: list[Fuente] = Field(default_factory=list)
    # Temas adicionales a los ejes de trabajo del perfil (por ejemplo, en inglés).
    temas: list[str] = Field(default_factory=list)
    # Buscador compatible con SearXNG (opcional). Solo se le envían los temas.
    buscador: str = ""
    # true: ignora las fuentes incluidas y usa solo las del espacio.
    solo_propias: bool = False

    @field_validator("buscador")
    @classmethod
    def _direccion(cls, v: str) -> str:
        return _url(v).rstrip("/")


def leer_catalogo(ruta: Path) -> Catalogo:
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        return Catalogo.model_validate(datos)
    except (yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"{ruta.name} no es válido: {exc}") from exc


def cargar_catalogo(carpeta_espacio: Path | None) -> Catalogo:
    """Une las fuentes incluidas con las del espacio; si una URL se repite, gana la del espacio."""
    propio = Catalogo()
    if carpeta_espacio is not None and (carpeta_espacio / ARCHIVO_FUENTES).is_file():
        propio = leer_catalogo(carpeta_espacio / ARCHIVO_FUENTES)
    incluidas = [] if propio.solo_propias else leer_catalogo(FUENTES_INCLUIDAS).fuentes
    propias = {f.rss or f.url for f in propio.fuentes}
    fuentes = [f for f in incluidas if (f.rss or f.url) not in propias] + propio.fuentes
    return propio.model_copy(update={"fuentes": fuentes})
