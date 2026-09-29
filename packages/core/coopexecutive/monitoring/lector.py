"""Descarga con caché y lectura de canales RSS y Atom.

A cada portal solo se le pide su canal público; no se envía ningún dato de la
organización. Si la descarga falla y hay una copia en caché, se usa la copia.
"""
from __future__ import annotations

import hashlib
import html
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as ET

from coopexecutive import __version__
from coopexecutive.lectura import descargar_bytes

AGENTE = f"Mozilla/5.0 (compatible; CoopExecutive/{__version__}; +https://github.com/pablomorenoc96/coop-executive)"
TIEMPO_ESPERA = 20.0
HORAS_CACHE = 12
TAMANO_MAXIMO = 5_000_000  # bytes; un canal normal pesa menos de 1 MB

_ATOM = "{http://www.w3.org/2005/Atom}"
_CONTENIDO = "{http://purl.org/rss/1.0/modules/content/}encoded"


@dataclass
class Entrada:
    titulo: str
    enlace: str
    texto: str
    publicado: date | None


@dataclass
class Descarga:
    contenido: bytes
    desde_cache: bool = False
    aviso: str = ""


def nuevo_cliente() -> httpx.Client:
    return httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=True, headers={"User-Agent": AGENTE})


def descargar(
    url: str,
    cliente: httpx.Client,
    cache: Path | None,
    *,
    usar_cache: bool = True,
    horas_cache: float = HORAS_CACHE,
    params: dict | None = None,
) -> Descarga:
    """Contenido de la URL. Usa la caché si es reciente o si la red falla."""
    clave = url + ("?" + str(sorted(params.items())) if params else "")
    archivo = cache / f"{hashlib.sha256(clave.encode()).hexdigest()[:24]}.cache" if cache else None
    if usar_cache and archivo is not None and archivo.is_file():
        if time.time() - archivo.stat().st_mtime < horas_cache * 3600:
            return Descarga(archivo.read_bytes(), desde_cache=True)
    try:
        contenido, _ = descargar_bytes(url, cliente, tope=TAMANO_MAXIMO, params=params)
    except httpx.HTTPError as exc:
        if archivo is not None and archivo.is_file():
            guardada = datetime.fromtimestamp(archivo.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            return Descarga(archivo.read_bytes(), desde_cache=True,
                            aviso=f"sin respuesta ({_motivo(exc)}); se usó la copia del {guardada}")
        raise
    if archivo is not None:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(contenido)
    return Descarga(contenido)


def _motivo(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return str(exc) if type(exc) is httpx.HTTPError else type(exc).__name__


def texto_plano(fragmento: str) -> str:
    sin_etiquetas = re.sub(r"<[^>]+>", " ", fragmento or "")
    return re.sub(r"\s+", " ", html.unescape(sin_etiquetas)).strip()


def _fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    valor = valor.strip()
    try:
        return parsedate_to_datetime(valor).date()  # RSS: RFC 822
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).date()  # Atom: ISO 8601
    except ValueError:
        return None


def leer_canal(contenido: bytes) -> list[Entrada]:
    """Entradas de un canal RSS 2.0 o Atom. Lanza ValueError si no es un canal."""
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as exc:
        raise ValueError("la respuesta no es un canal RSS o Atom") from exc
    except DefusedXmlException as exc:
        raise ValueError("el canal declara entidades o DTD externos; no se procesa") from exc
    entradas: list[Entrada] = []
    for item in raiz.iter("item"):
        texto = " ".join(filter(None, [item.findtext("description"), item.findtext(_CONTENIDO)]))
        entradas.append(Entrada(
            titulo=texto_plano(item.findtext("title") or ""),
            enlace=(item.findtext("link") or "").strip(),
            texto=texto_plano(texto),
            publicado=_fecha(item.findtext("pubDate")),
        ))
    for item in raiz.iter(f"{_ATOM}entry"):
        enlace = item.find(f"{_ATOM}link")
        texto = " ".join(filter(None, [item.findtext(f"{_ATOM}summary"), item.findtext(f"{_ATOM}content")]))
        entradas.append(Entrada(
            titulo=texto_plano(item.findtext(f"{_ATOM}title") or ""),
            enlace=(enlace.get("href", "") if enlace is not None else "").strip(),
            texto=texto_plano(texto),
            publicado=_fecha(item.findtext(f"{_ATOM}updated") or item.findtext(f"{_ATOM}published")),
        ))
    if not entradas and raiz.tag not in ("rss", f"{_ATOM}feed") and raiz.find("channel") is None:
        raise ValueError("la respuesta no es un canal RSS o Atom")
    return entradas
