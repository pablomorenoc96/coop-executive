"""Propuesta de perfil a partir del sitio web público de la organización.

1. `rastrear()` lee la portada y hasta seis páginas del mismo dominio (nosotros,
   contacto, programas, únete, transparencia), respeta robots.txt y corta cada
   descarga en un tope de bytes.
2. Todo el texto pasa por `limpiar_datos_sensibles()` antes de mostrarse o de
   enviarse al modelo: sin cuentas, tarjetas, RFC, CURP, correos personales ni teléfonos.
3. `proponer()` pide al modelo un valor por campo con una cita textual. Si la cita
   no aparece en la página indicada, el campo queda pendiente: nada se acepta sin evidencia.

Montos, moneda y aprobadores nunca se toman del sitio. Del mecanismo de donativos
solo se conserva el tipo (transferencia, plataforma en línea…), nunca los datos.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from coopexecutive.guardrails.sensibles import limpiar_datos_sensibles
from coopexecutive.lectura import AGENTE, ErrorLectura, descargar_bytes, nuevo_cliente, texto_de_html
from coopexecutive.memory.onboarding import CAMPOS_LISTA, PREGUNTAS
from coopexecutive.utils.texto import extraer_json, normalizar

MAX_PAGINAS = 6
TOPE_PAGINA = 1_500_000
CARACTERES_POR_PAGINA = 6_000

# Palabras de la ruta o del texto del enlace que señalan páginas útiles, por prioridad.
_PISTAS = (
    ("nosotros", "quienes", "quien-somos", "acerca", "about", "historia", "mision"),
    ("programas", "proyectos", "que-hacemos", "lineas", "ejes", "servicios"),
    ("transparencia", "informes", "rendicion"),
    ("contacto", "contact"),
    ("unete", "dona", "donar", "donativos", "apoya", "voluntariado", "involucrate"),
    ("aliados", "alianzas", "socios", "partners"),
)
_ENLACE = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_ARCHIVO = re.compile(r"\.(?:jpe?g|png|gif|svg|webp|pdf|zip|docx?|xlsx?|mp4|mp3)$", re.IGNORECASE)

# Campos que nunca se proponen desde el sitio.
CAMPOS_PRIVADOS = {"rango_minimo", "rango_maximo", "moneda", "aprobadores"}
MECANISMOS = (
    "Transferencia bancaria",
    "Plataforma de donativos en línea",
    "Tarjeta de crédito o débito",
    "PayPal",
    "Depósito en ventanilla",
    "Recibo deducible de impuestos",
    "Donativo en especie",
    "Suscripción o donativo recurrente",
)


@dataclass(frozen=True)
class Pagina:
    url: str
    titulo: str
    texto: str


@dataclass
class Propuesta:
    campo: str
    valor: str | list[str] = ""
    evidencia: str = ""
    url: str = ""

    @property
    def pendiente(self) -> bool:
        return not self.valor


@dataclass
class Rastreo:
    paginas: list[Pagina] = field(default_factory=list)
    omitidas: list[str] = field(default_factory=list)


def _mismo_sitio(a: str, b: str) -> bool:
    def host(u: str) -> str:
        return (urlparse(u).hostname or "").lower().removeprefix("www.")

    return host(a) == host(b)


def _prioridad(url: str, texto: str) -> int | None:
    ruta = normalizar(urlparse(url).path.replace("/", " ").replace("-", " "))
    ancla = normalizar(re.sub(r"<[^>]+>", " ", texto))
    for i, grupo in enumerate(_PISTAS):
        for pista in grupo:
            pista_n = normalizar(pista.replace("-", " "))
            if pista_n in ruta or pista_n in ancla:
                return i
    return None


def enlaces_utiles(html: str, base: str, limite: int = MAX_PAGINAS) -> list[str]:
    candidatos: dict[str, int] = {}
    for href, texto in _ENLACE.findall(html):
        url = urljoin(base, href.strip()).split("#")[0].rstrip("/")
        if not url.startswith(("http://", "https://")) or not _mismo_sitio(url, base):
            continue
        if _ARCHIVO.search(urlparse(url).path) or url == base.rstrip("/"):
            continue
        prioridad = _prioridad(url, texto)
        if prioridad is not None and prioridad < candidatos.get(url, 99):
            candidatos[url] = prioridad
    return sorted(candidatos, key=lambda u: (candidatos[u], len(u)))[:limite]


def _robots(url: str, cliente: httpx.Client, bloquear_privadas: bool) -> RobotFileParser:
    reglas = RobotFileParser()
    partes = urlparse(url)
    try:
        contenido, _ = descargar_bytes(
            f"{partes.scheme}://{partes.netloc}/robots.txt", cliente, tope=200_000,
            bloquear_privadas=bloquear_privadas,
        )
        reglas.parse(contenido.decode("utf-8", errors="replace").splitlines())
    except (httpx.HTTPError, ErrorLectura):
        reglas.parse([])  # sin robots.txt: se permite todo
    return reglas


def _pagina(url: str, cliente: httpx.Client, bloquear_privadas: bool) -> tuple[Pagina, str]:
    contenido, _ = descargar_bytes(url, cliente, tope=TOPE_PAGINA, bloquear_privadas=bloquear_privadas)
    html = contenido.decode("utf-8", errors="replace")
    titulo = _TITULO.search(html)
    texto = limpiar_datos_sensibles(texto_de_html(html))
    nombre = limpiar_datos_sensibles(re.sub(r"\s+", " ", titulo.group(1)).strip()) if titulo else ""
    return Pagina(url=url, titulo=nombre, texto=texto), html


def rastrear(
    url: str,
    *,
    cliente: httpx.Client | None = None,
    max_paginas: int = MAX_PAGINAS,
    bloquear_privadas: bool = False,
) -> Rastreo:
    """Portada y hasta `max_paginas` páginas internas útiles, ya sin datos sensibles."""
    if not urlparse(url).scheme:
        url = "https://" + url
    propio = cliente is None
    cliente = cliente or nuevo_cliente()
    rastreo = Rastreo()
    try:
        reglas = _robots(url, cliente, bloquear_privadas)
        if not reglas.can_fetch(AGENTE, url):
            raise ErrorLectura("El archivo robots.txt del sitio no permite leer la portada.")
        try:
            portada, html = _pagina(url, cliente, bloquear_privadas)
        except httpx.HTTPError as exc:
            raise ErrorLectura(f"No se pudo leer {url}: {exc or type(exc).__name__}") from exc
        rastreo.paginas.append(portada)
        for enlace in enlaces_utiles(html, url, max_paginas):
            if not reglas.can_fetch(AGENTE, enlace):
                rastreo.omitidas.append(f"{enlace} (robots.txt)")
                continue
            try:
                pagina, _ = _pagina(enlace, cliente, bloquear_privadas)
            except (httpx.HTTPError, ErrorLectura) as exc:
                rastreo.omitidas.append(f"{enlace} ({exc or type(exc).__name__})")
                continue
            rastreo.paginas.append(pagina)
    finally:
        if propio:
            cliente.close()
    return rastreo


# --- Propuesta -------------------------------------------------------------------

_DESCRIPCION = {
    "nombre": "nombre completo de la organización",
    "siglas": "siglas o nombre corto",
    "figura": "figura jurídica (asociación civil, cooperativa, fundación, etc.)",
    "mision": "misión, en una o dos frases",
    "poblacion": "lista de poblaciones que atiende",
    "territorio": "territorio donde trabaja",
    "programas": "lista de programas o proyectos",
    "ejes": "lista de ejes o líneas de trabajo",
    "metricas": "lista de resultados con cifras tal como aparecen en el sitio",
    "estatus_legal": "estatus legal (por ejemplo, constituida en tal año), sin identificadores",
    "estatus_fiscal": "estatus fiscal (por ejemplo, donataria autorizada), sin RFC",
    "alianzas": "lista de aliados",
    "financiadores": "lista de financiadores o donantes institucionales",
    "mecanismos_cobro": f"lista de tipos de mecanismo para recibir donativos; solo de: {', '.join(MECANISMOS)}",
}


def campos_del_sitio(numeros: set[int] | None = None) -> list[str]:
    campos = []
    for pregunta in PREGUNTAS:
        if numeros is None or pregunta.numero in numeros:
            campos += [c for c in pregunta.campos if c not in CAMPOS_PRIVADOS]
    return campos


def instrucciones(paginas: list[Pagina], campos: list[str]) -> str:
    textos = "\n\n".join(
        f"### Página {i}: {p.url}\nTítulo: {p.titulo}\n{p.texto[:CARACTERES_POR_PAGINA]}"
        for i, p in enumerate(paginas, 1)
    )
    lista = "\n".join(f'- "{c}": {_DESCRIPCION[c]}' for c in campos)
    return (
        "Extrae del texto de estas páginas los datos del perfil de la organización. Reglas:\n"
        "- Usa solo lo que dice el texto. Si un dato no aparece, deja el valor vacío.\n"
        "- En cada campo copia en «evidencia» una cita textual breve (máximo 200 caracteres) "
        "y en «url» la dirección de la página de donde sale.\n"
        "- No escribas cuentas, CLABE, tarjetas, RFC, CURP, correos ni teléfonos.\n"
        "- Las listas van como arreglos de textos cortos.\n\n"
        f"Campos:\n{lista}\n\n"
        'Responde solo con un objeto JSON: {"campo": {"valor": ..., "evidencia": "...", "url": "..."}}.\n\n'
        f"{textos}"
    )


def _cita_valida(evidencia: str, url: str, paginas: list[Pagina]) -> bool:
    cita = normalizar(evidencia)
    if len(cita) < 3:
        return False
    return any(p.url.rstrip("/") == url.rstrip("/") and cita in normalizar(p.texto + " " + p.titulo) for p in paginas)


def _valor(campo: str, crudo: object) -> str | list[str]:
    if campo in CAMPOS_LISTA:
        if isinstance(crudo, str):
            crudo = [parte for parte in re.split(r"[;\n]", crudo)]
        elementos = [limpiar_datos_sensibles(str(v)).strip() for v in (crudo or []) if str(v).strip()]
        if campo == "mecanismos_cobro":
            validos = {normalizar(m): m for m in MECANISMOS}
            elementos = [validos[normalizar(e)] for e in elementos if normalizar(e) in validos]
        return list(dict.fromkeys(elementos))
    return limpiar_datos_sensibles(str(crudo or "")).strip()


def interpretar(respuesta: dict, paginas: list[Pagina], campos: list[str]) -> dict[str, Propuesta]:
    """Valida la respuesta del modelo: sin cita comprobable en la página, el campo queda pendiente."""
    propuestas: dict[str, Propuesta] = {}
    for campo in campos:
        dato = respuesta.get(campo)
        propuesta = Propuesta(campo=campo)
        if isinstance(dato, dict):
            valor = _valor(campo, dato.get("valor"))
            evidencia = limpiar_datos_sensibles(str(dato.get("evidencia") or "")).strip()
            url = str(dato.get("url") or "").strip()
            if valor and _cita_valida(evidencia, url, paginas):
                propuesta = Propuesta(campo=campo, valor=valor, evidencia=evidencia, url=url)
        propuestas[campo] = propuesta
    return propuestas


def proponer(
    paginas: list[Pagina],
    responder: Callable[[str], str],
    numeros: set[int] | None = None,
) -> dict[str, Propuesta]:
    """Pide la propuesta al modelo (`responder` recibe el prompt y devuelve texto)."""
    campos = campos_del_sitio(numeros)
    if not paginas or not campos:
        return {c: Propuesta(campo=c) for c in campos}
    try:
        datos = extraer_json(responder(instrucciones(paginas, campos)))
    except (ValueError, json.JSONDecodeError):
        datos = {}
    return interpretar(datos, paginas, campos)
