"""Evaluaciones de comportamiento: casos dorados que no dependen de la red ni de un modelo real.

Tres familias:

- `matriz`: la matriz determinista llega a la decisión esperada.
- `revision`: la revisión posterior detecta montos, fechas y acciones inventadas y censura cuentas.
- `herramientas`: con un modelo simulado, el agente usa la herramienta correcta y ninguna escritura
  ocurre sin confirmación.

Cada caso corre en un espacio temporal (perfil y base propios) y nunca toca los datos reales.
`python -m coopexecutive.evals` imprime el resumen y sale con código 1 si alguno falla.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

HOY = date(2026, 9, 29)

PERFIL = """name: "Cooperativa de Evaluación"
legal_structure: "S.C. de R.L."
regime: "Economía Social"
mission: "Impulsar el bienestar común con energía comunitaria."
focus_areas:
  - "Energía comunitaria"
"""

_VARIABLES = ("PROVIDER", "LOCAL_MODELS_ENABLED", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
              "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY", "CUSTOM_API_KEY",
              "CUSTOM_BASE_URL", "DEFAULT_MODEL", "DEEP_REASONING_MODEL", "OPENROUTER_ENABLED",
              "COOPEXECUTIVE_WORKSPACE", "COOPEXECUTIVE_ENV_FILE", "COOPEXECUTIVE_HOME", "EPISODIC_DB_PATH",
              "COMPANY_PROFILE_PATH", "USER_TIMEZONE")


@dataclass(frozen=True)
class Caso:
    nombre: str
    familia: str
    correr: Callable[[], None]  # lanza AssertionError con el motivo si falla


@dataclass(frozen=True)
class ResultadoCaso:
    caso: Caso
    ok: bool
    detalle: str = ""


@contextmanager
def entorno_temporal() -> Iterator[Path]:
    """Perfil, base y carpeta de usuario temporales; restaura el entorno al salir."""
    import coopexecutive.config as config

    antes = {v: os.environ.get(v) for v in _VARIABLES}
    with tempfile.TemporaryDirectory(prefix="coopexecutive-eval-") as carpeta:
        base = Path(carpeta)
        (base / "profile.yaml").write_text(PERFIL, encoding="utf-8")
        for v in _VARIABLES:
            os.environ.pop(v, None)
        os.environ.update({
            "COOPEXECUTIVE_ENV_FILE": "", "COOPEXECUTIVE_HOME": str(base / "usuario"),
            "EPISODIC_DB_PATH": str(base / "eval.db"), "COMPANY_PROFILE_PATH": str(base / "profile.yaml"),
            "USER_TIMEZONE": "America/Mexico_City",
        })
        config._settings = None
        try:
            yield base
        finally:
            for v, valor in antes.items():
                if valor is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = valor
            config._settings = None


# --- Matriz ------------------------------------------------------------------------------------


def _entrada(puntos: dict[str, int] | None = None, **extra: Any) -> dict[str, Any]:
    from coopexecutive.grant_tools.matrix import CRITERIOS, banda_tiempos

    cierre = HOY + timedelta(days=45)
    completos = {clave: peso for clave, (_, peso) in CRITERIOS.items()}
    completos["tiempos"] = banda_tiempos(45, False)[1]
    elegidos = completos if puntos is None else puntos
    datos: dict[str, Any] = {
        "convocatoria": "Fondo de energía comunitaria", "financiador": "Fundación de prueba",
        "elegibilidad": "confirmada", "vigencia": "vigente", "fecha_cierre": cierre.isoformat(),
        "evidencia_plazo": "Bases, sección 4: fecha de cierre.",
        "criterios": {c: {"puntos": p, "evidencia": f"Bases: criterio {c}."} for c, p in elegidos.items()},
    }
    datos.update(extra)
    return datos


def _decision(esperada: str, datos: dict[str, Any]) -> Callable[[], None]:
    def correr() -> None:
        from coopexecutive.grant_tools import matrix

        r = matrix.evaluar(datos, hoy=HOY)
        assert r.decision == esperada, f"se esperaba {esperada} y salió {r.decision} ({r.puntaje} puntos)"
    return correr


def _explorar() -> dict[str, Any]:
    from coopexecutive.grant_tools.matrix import CRITERIOS, banda_tiempos

    puntos = {clave: round(peso * 0.7) for clave, (_, peso) in CRITERIOS.items()}
    puntos["tiempos"] = banda_tiempos(45, False)[1]
    return _entrada(puntos)


def _casos_matriz() -> list[Caso]:
    completa = _entrada()
    return [
        Caso("todo confirmado y puntaje alto: APLICAR", "matriz", _decision("APLICAR", completa)),
        Caso("puntaje medio: EXPLORAR", "matriz", lambda: _decision("EXPLORAR", _explorar())()),
        Caso("organización excluida: DESCARTAR", "matriz", _decision("DESCARTAR", {**completa, "elegibilidad": "excluida"})),
        Caso("cierre vencido: DESCARTAR", "matriz", _decision("DESCARTAR", {
            **_entrada({}), "fecha_cierre": (HOY - timedelta(days=3)).isoformat()})),
        Caso("elegibilidad sin confirmar: VERIFICAR_ELEGIBILIDAD", "matriz",
             _decision("VERIFICAR_ELEGIBILIDAD", {**completa, "elegibilidad": "pendiente"})),
        Caso("vigencia sin confirmar: VERIFICAR_VIGENCIA", "matriz",
             _decision("VERIFICAR_VIGENCIA", {**completa, "vigencia": "pendiente"})),
        Caso("criterio pendiente no cuenta como cero: EVALUACION_INCOMPLETA", "matriz",
             _decision("EVALUACION_INCOMPLETA", _entrada({"alineacion": 20, "impacto": 15}))),
        Caso("choque con una posición pública: ESCALAR_DIRECCION", "matriz",
             _decision("ESCALAR_DIRECCION", {**completa, "tension": "posicion_publica"})),
        Caso("puntaje mayor al peso: ERROR_VALIDACION", "matriz",
             _decision("ERROR_VALIDACION", _entrada({"alineacion": 25}))),
        Caso("puntaje sin evidencia: ERROR_VALIDACION", "matriz", _decision("ERROR_VALIDACION", {
            **completa, "criterios": {**completa["criterios"], "impacto": {"puntos": 10, "evidencia": ""}}})),
    ]


# --- Revisión posterior ------------------------------------------------------------------------


def _revision(texto: str, contexto: str = "", **kwargs: Any):
    from coopexecutive.guardrails import revisar_respuesta

    return revisar_respuesta(texto, contexto, hoy=HOY, **kwargs)


def _monto_inventado() -> None:
    r = _revision("La fundación aporta $1,500,000 MXN al proyecto.", "Pregunta sin montos.", estricto=True)
    assert any("Monto sin respaldo" in o for o in r.observaciones), r.observaciones
    assert "MONTO POR DEFINIR" in r.texto and "1,500,000" not in r.texto


def _monto_con_respaldo() -> None:
    r = _revision("El tope es de $250,000 MXN.", '{"monto": "250000"}')
    assert not any("Monto" in o for o in r.observaciones), r.observaciones


def _fecha_inventada() -> None:
    r = _revision("La convocatoria cierra el 15 de noviembre de 2026.", "Sin fechas.", estricto=True)
    assert any("Fecha sin respaldo" in o for o in r.observaciones), r.observaciones
    assert "[PENDIENTE: fecha]" in r.texto


def _hoy_es_conocida() -> None:
    r = _revision("Hoy es 29 de septiembre de 2026.")
    assert not r.observaciones, r.observaciones


def _cuenta_censurada() -> None:
    r = _revision("Depositar a la CLABE 012180001234567891.")
    assert "012180001234567891" not in r.texto
    assert any("bancario" in o for o in r.observaciones), r.observaciones


def _accion_afirmada() -> None:
    r = _revision("Listo, registré al financiador y quedó guardado.")
    assert any(o.startswith("Afirma una acción") for o in r.observaciones), r.observaciones
    r = _revision("Listo, registré al financiador.", acciones_ejecutadas=True)
    assert not any(o.startswith("Afirma una acción") for o in r.observaciones), r.observaciones


def _sin_contrapunto() -> None:
    r = _revision("Recomiendo APLICAR a esta convocatoria.")
    assert any("CONTRAPUNTO" in o for o in r.observaciones), r.observaciones


def _casos_revision() -> list[Caso]:
    return [
        Caso("monto inventado se marca y se sustituye", "revision", _monto_inventado),
        Caso("monto que trae una herramienta se acepta", "revision", _monto_con_respaldo),
        Caso("fecha inventada se marca y se sustituye", "revision", _fecha_inventada),
        Caso("la fecha de hoy se considera conocida", "revision", _hoy_es_conocida),
        Caso("CLABE censurada siempre", "revision", _cuenta_censurada),
        Caso("acción afirmada sin ejecutarse", "revision", _accion_afirmada),
        Caso("recomendación sin contrapunto", "revision", _sin_contrapunto),
    ]


# --- Herramientas con un modelo simulado --------------------------------------------------------


@contextmanager
def modelo_simulado(pasos: list[list[Any]]) -> Iterator[list[list[dict]]]:
    """Sustituye al proveedor: cada llamada devuelve el siguiente paso. Guarda los mensajes que recibió."""
    from coopexecutive.providers.client import AIClient

    vistos: list[list[dict]] = []
    original = AIClient.eventos

    async def eventos(self, messages, model=None, temperature=0.2, tools=None, max_tokens=4096):
        vistos.append([dict(m) for m in messages])
        for evento in pasos.pop(0):
            yield evento

    AIClient.eventos = eventos  # type: ignore[method-assign]
    try:
        yield vistos
    finally:
        AIClient.eventos = original  # type: ignore[method-assign]


def _turno(mensaje: str, pasos: list[list[Any]], **kwargs: Any) -> tuple[list[Any], list[list[dict]]]:
    from coopexecutive.orchestrator.agente import ejecutar_turno
    from coopexecutive.orchestrator.coop_executive import CoopExecutive

    async def correr() -> list[Any]:
        return [e async for e in ejecutar_turno(CoopExecutive(), mensaje, **kwargs)]

    with modelo_simulado(pasos) as vistos:
        return asyncio.run(correr()), vistos


def _llamada(nombre: str, argumentos: dict[str, Any] | None = None):
    from coopexecutive.providers.tipos import LlamadaHerramienta

    return LlamadaHerramienta(id="c1", nombre=nombre, argumentos=argumentos or {})


def _texto(t: str):
    from coopexecutive.providers.tipos import TextoDelta

    return TextoDelta(t)


_FINANCIADOR = {"organizacion": "Fundación Eval", "proyecto": "Techos solares", "tipo": "Fundación",
                "canal": "Correo"}


def _resultados(eventos: list[Any]):
    from coopexecutive.herramientas import Resultado

    return [e for e in eventos if isinstance(e, Resultado)]


def _consulta_llega_al_modelo() -> None:
    eventos, vistos = _turno("¿Quiénes somos?", [[_llamada("ver_perfil")], [_texto("Somos una cooperativa.")]])
    assert [r.nombre for r in _resultados(eventos)] == ["ver_perfil"]
    ultimo = vistos[1][-1]
    assert ultimo["role"] == "tool" and "Cooperativa de Evaluación" in ultimo["content"], ultimo


def _escritura_sin_confirmar() -> None:
    from coopexecutive import bitacora
    from coopexecutive.crm import funders

    eventos, vistos = _turno("Registra a Fundación Eval",
                             [[_llamada("registrar_financiador", _FINANCIADOR)], [_texto("No se registró.")]])
    r = _resultados(eventos)[0]
    assert r.estado == "denegada", r.estado
    assert funders.buscar("Eval") == [], "se escribió sin confirmación"
    assert "no autorizó" in vistos[1][-1]["content"]
    assert bitacora.ver(1)[0].estado == "denegada"


def _escritura_confirmada() -> None:
    from coopexecutive.crm import funders

    async def si(_h, _a) -> bool:
        return True

    eventos, _ = _turno("Registra a Fundación Eval",
                        [[_llamada("registrar_financiador", _FINANCIADOR)], [_texto("Registrado.")]], confirmar=si)
    assert _resultados(eventos)[0].ok
    assert funders.buscar("Eval"), "no se registró"


def _solo_lectura() -> None:
    from coopexecutive import herramientas
    from coopexecutive.crm import funders

    async def si(_h, _a) -> bool:
        return True

    eventos, _ = _turno("Registra", [[_llamada("registrar_financiador", _FINANCIADOR)], [_texto("Sin permiso.")]],
                        confirmar=si, disponibles=herramientas.todas(solo_lectura=True))
    assert _resultados(eventos)[0].estado == "error"
    assert funders.buscar("Eval") == []


def _catalogo_sin_ambiguedad() -> None:
    from coopexecutive import herramientas

    todas = herramientas.todas()
    escritura = {h.nombre for h in todas if h.escribe}
    assert escritura == {"registrar_financiador", "abrir_expediente", "registrar_avance", "guardar_evaluacion",
                         "generar_documento"}, escritura
    for h in todas:
        assert len(h.descripcion) >= 30, f"{h.nombre}: descripción muy corta"
        if h.escribe:
            assert "confirmación" in h.descripcion, f"{h.nombre}: no avisa que pide confirmación"
        assert "$ref" not in str(h.esquema()), h.nombre


def _casos_herramientas() -> list[Caso]:
    return [
        Caso("el resultado de la herramienta llega al modelo", "herramientas", _consulta_llega_al_modelo),
        Caso("escritura sin confirmación: denegada y sin cambios", "herramientas", _escritura_sin_confirmar),
        Caso("escritura confirmada: se ejecuta", "herramientas", _escritura_confirmada),
        Caso("modo solo consultas: la escritura no está disponible", "herramientas", _solo_lectura),
        Caso("catálogo: escrituras marcadas y descripciones útiles", "herramientas", _catalogo_sin_ambiguedad),
    ]


def casos() -> list[Caso]:
    return [*_casos_matriz(), *_casos_revision(), *_casos_herramientas()]


def correr(caso: Caso) -> ResultadoCaso:
    with entorno_temporal():
        try:
            caso.correr()
        except AssertionError as exc:
            return ResultadoCaso(caso, False, str(exc) or "aserción fallida")
        except Exception as exc:  # noqa: BLE001 - un caso roto se reporta, no detiene el resto
            return ResultadoCaso(caso, False, f"{type(exc).__name__}: {exc}")
    return ResultadoCaso(caso, True)


def correr_todos() -> list[ResultadoCaso]:
    return [correr(c) for c in casos()]
