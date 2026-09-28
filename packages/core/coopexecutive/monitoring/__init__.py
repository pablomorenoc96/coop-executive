"""Monitoreo de convocatorias abiertas.

Lee los canales de las fuentes, se queda con los avisos que coinciden con los
temas de la organización, extrae la fecha de cierre y aplica las mismas reglas
de plazo que la matriz. El resultado tiene tres listas: priorizadas (hasta 3),
por revisar y cerradas. Un aviso sin fecha de cierre explícita queda como
VIGENCIA NO VERIFICADA: nunca se supone que sigue abierto.

A la web solo salen las solicitudes a los canales públicos y, si hay buscador,
los temas. Ningún dato del perfil ni de los financiadores sale del equipo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import httpx

from coopexecutive.grant_tools.matrix import texto_plazo
from coopexecutive.guardrails import VIGENCIA_NO_VERIFICADA
from coopexecutive.monitoring.cierre import extraer_cierre
from coopexecutive.monitoring.fuentes import Catalogo, Fuente, cargar_catalogo
from coopexecutive.monitoring.lector import Entrada, descargar, leer_canal, nuevo_cliente, texto_plano
from coopexecutive.monitoring.temas import Tema, coincidencias, preparar_temas
from coopexecutive.utils.texto import normalizar

__all__ = ["Aviso", "Reporte", "cargar_catalogo", "monitorear"]

MAX_PRIORIZADAS = 3
ANTIGUEDAD_MAXIMA_DIAS = 120
DIAS_MINIMOS = 7  # con menos días no alcanza para preparar una solicitud completa


@dataclass
class Aviso:
    titulo: str
    enlace: str
    fuente: str
    resumen: str
    publicado: date | None
    cierre: date | None
    dias: int | None
    coincidencias: list[str]
    temas: list[str]

    @property
    def vigencia_verificada(self) -> bool:
        return self.cierre is not None

    @property
    def plazo(self) -> str:
        if self.cierre is None:
            return VIGENCIA_NO_VERIFICADA
        return f"{texto_plazo(self.dias)}. Cierre: {self.cierre.isoformat()}"


@dataclass
class Reporte:
    hoy: date
    temas: list[str]
    priorizadas: list[Aviso] = field(default_factory=list)
    por_revisar: list[Aviso] = field(default_factory=list)
    cerradas: list[Aviso] = field(default_factory=list)
    consultadas: list[str] = field(default_factory=list)
    manuales: list[Fuente] = field(default_factory=list)
    fallidas: list[tuple[str, str]] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    leidos: int = 0
    antiguos: int = 0


def _aviso(entrada: Entrada, fuente: str, temas: list[Tema], hoy: date) -> Aviso | None:
    texto = f"{entrada.titulo}. {entrada.texto}"
    halladas = coincidencias(texto, temas)
    if not halladas:
        return None
    cierre = extraer_cierre(texto)
    resumen = entrada.texto if len(entrada.texto) <= 280 else entrada.texto[:277].rsplit(" ", 1)[0] + "..."
    return Aviso(
        titulo=entrada.titulo or "(sin título)",
        enlace=entrada.enlace,
        fuente=fuente,
        resumen=resumen,
        publicado=entrada.publicado,
        cierre=cierre,
        dias=(cierre - hoy).days if cierre else None,
        coincidencias=halladas.palabras,
        temas=halladas.temas,
    )


def _orden(aviso: Aviso) -> tuple:
    """Primero con fecha y tiempo suficiente, luego sin fecha y al final los urgentes.

    Dentro de cada grupo pesan más los temas completos que las palabras sueltas.
    """
    if aviso.dias is None:
        grupo = 1
    else:
        grupo = 0 if aviso.dias >= DIAS_MINIMOS else 2
    dias = aviso.dias if aviso.dias is not None else 0
    return (grupo, -len(aviso.temas), -len(aviso.coincidencias), dias, aviso.titulo)


def _buscar(catalogo: Catalogo, temas: list[str], cliente: httpx.Client, cache: Path | None,
            usar_cache: bool) -> list[Entrada]:
    """Consulta al buscador SearXNG del espacio. Solo viaja el tema."""
    entradas: list[Entrada] = []
    for tema in temas:
        params = {"q": f"convocatoria {tema}", "format": "json"}
        datos = descargar(f"{catalogo.buscador}/search", cliente, cache, usar_cache=usar_cache, params=params)
        try:
            resultados = json.loads(datos.contenido).get("results", [])
        except (ValueError, AttributeError) as exc:
            raise ValueError("el buscador no devolvió JSON; active format=json en su configuración") from exc
        for r in resultados:
            entradas.append(Entrada(
                titulo=texto_plano(r.get("title", "")),
                enlace=r.get("url", ""),
                texto=texto_plano(r.get("content", "")),
                publicado=None,
            ))
    return entradas


def monitorear(
    temas: list[str],
    hoy: date,
    carpeta_espacio: Path | None = None,
    *,
    cache: Path | None = None,
    usar_cache: bool = True,
    cliente: httpx.Client | None = None,
) -> Reporte:
    catalogo = cargar_catalogo(carpeta_espacio)
    todos_los_temas = list(dict.fromkeys([*temas, *catalogo.temas]))
    reporte = Reporte(hoy=hoy, temas=todos_los_temas)
    if not todos_los_temas:
        raise ValueError(
            "No hay temas para filtrar. Agregue ejes de trabajo (focus_areas) al perfil, "
            "temas en fuentes.yaml o use --tema."
        )
    preparados = preparar_temas(todos_los_temas)
    limite_antiguedad = hoy - timedelta(days=ANTIGUEDAD_MAXIMA_DIAS)
    propio = cliente is None
    cliente = cliente or nuevo_cliente()
    avisos: dict[str, Aviso] = {}
    try:
        lotes: list[tuple[str, list[Entrada]]] = []
        for fuente in catalogo.fuentes:
            if not fuente.automatica:
                reporte.manuales.append(fuente)
                continue
            try:
                descarga = descargar(fuente.rss, cliente, cache, usar_cache=usar_cache)
                lotes.append((fuente.nombre, leer_canal(descarga.contenido)))
                reporte.consultadas.append(fuente.nombre)
                if descarga.aviso:
                    reporte.notas.append(f"{fuente.nombre}: {descarga.aviso}")
            except (httpx.HTTPError, ValueError) as exc:
                reporte.fallidas.append((fuente.nombre, _explicar(exc)))
        if catalogo.buscador:
            try:
                lotes.append(("Buscador", _buscar(catalogo, todos_los_temas, cliente, cache, usar_cache)))
                reporte.consultadas.append("Buscador")
            except (httpx.HTTPError, ValueError) as exc:
                reporte.fallidas.append(("Buscador", _explicar(exc)))
    finally:
        if propio:
            cliente.close()

    for nombre, entradas in lotes:
        for entrada in entradas:
            reporte.leidos += 1
            if entrada.publicado is not None and entrada.publicado < limite_antiguedad:
                reporte.antiguos += 1
                continue
            aviso = _aviso(entrada, nombre, preparados, hoy)
            if aviso is None:
                continue
            clave = entrada.enlace or normalizar(entrada.titulo)
            avisos.setdefault(clave, aviso)

    abiertas = sorted((a for a in avisos.values() if a.dias is None or a.dias >= 0), key=_orden)
    reporte.priorizadas = abiertas[:MAX_PRIORIZADAS]
    reporte.por_revisar = abiertas[MAX_PRIORIZADAS:]
    reporte.cerradas = sorted((a for a in avisos.values() if a.dias is not None and a.dias < 0),
                              key=lambda a: a.cierre, reverse=True)
    return reporte


def _explicar(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "tiempo de espera agotado"
    if isinstance(exc, httpx.HTTPError):
        return str(exc) or type(exc).__name__
    return str(exc)
