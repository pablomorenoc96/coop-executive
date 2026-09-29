"""Cliente de modelos de lenguaje: OpenRouter, Ollama, OpenAI, Anthropic, Gemini, Groq,
Mistral, DeepSeek y cualquier endpoint compatible con OpenAI.

Los mensajes y las herramientas se escriben siempre en formato OpenAI; para Anthropic
se convierten aquí. `eventos()` emite `TextoDelta`, `LlamadaHerramienta` y `Fin`;
`stream_chat()` conserva la interfaz anterior y solo emite texto. Los fallos se lanzan
como `ErrorProveedor`, nunca se devuelven como si fueran la respuesta.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from coopexecutive.config import Settings, get_settings
from coopexecutive.providers.tipos import (
    ErrorProveedor,
    Evento,
    Fin,
    LlamadaHerramienta,
    TextoDelta,
    censurar,
)
from coopexecutive.registro import obtener

log = obtener(__name__)

REINTENTABLES = {408, 425, 429, 500, 502, 503, 504, 529}
ESPERA_MAXIMA = 30.0

_VARIABLE_CLAVE = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


@dataclass(frozen=True)
class Ruta:
    proveedor: str
    flavor: str  # 'openai_compat' o 'anthropic'
    endpoint: str
    headers: dict[str, str]
    clave: str | None
    timeout: float


def herramientas_openai(herramientas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Acepta {name, description, parameters} o el formato OpenAI y devuelve el de OpenAI."""
    salida = []
    for h in herramientas:
        if h.get("type") == "function":
            salida.append(h)
            continue
        salida.append({"type": "function", "function": {
            "name": h["name"], "description": h.get("description", ""),
            "parameters": h.get("parameters") or {"type": "object", "properties": {}},
        }})
    return salida


def herramientas_anthropic(herramientas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    salida = []
    for h in herramientas_openai(herramientas):
        f = h["function"]
        salida.append({"name": f["name"], "description": f.get("description", ""),
                       "input_schema": f.get("parameters") or {"type": "object", "properties": {}}})
    return salida


def mensajes_anthropic(mensajes: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Convierte mensajes OpenAI (incluidas llamadas y resultados de herramientas) al formato de Anthropic."""
    sistema: list[str] = []
    salida: list[dict[str, Any]] = []
    for m in mensajes:
        rol = m.get("role")
        if rol == "system":
            sistema.append(str(m.get("content") or ""))
        elif rol == "tool":
            bloque = {"type": "tool_result", "tool_use_id": m.get("tool_call_id", ""),
                      "content": str(m.get("content") or "")}
            previo = salida[-1] if salida else None
            if previo and previo["role"] == "user" and isinstance(previo["content"], list) \
                    and all(b.get("type") == "tool_result" for b in previo["content"]):
                previo["content"].append(bloque)
            else:
                salida.append({"role": "user", "content": [bloque]})
        elif rol == "assistant" and m.get("tool_calls"):
            bloques: list[dict[str, Any]] = []
            if m.get("content"):
                bloques.append({"type": "text", "text": m["content"]})
            for llamada in m["tool_calls"]:
                f = llamada.get("function", {})
                try:
                    entrada = json.loads(f.get("arguments") or "{}")
                except json.JSONDecodeError:
                    entrada = {}
                bloques.append({"type": "tool_use", "id": llamada.get("id", ""),
                                "name": f.get("name", ""), "input": entrada})
            salida.append({"role": "assistant", "content": bloques})
        else:
            salida.append({"role": rol, "content": m.get("content") or ""})
    return "\n".join(s for s in sistema if s).strip(), salida


def _detalle(cuerpo: str) -> str:
    try:
        datos = json.loads(cuerpo)
    except (json.JSONDecodeError, ValueError):
        return cuerpo.strip()[:300]
    error = datos.get("error", datos) if isinstance(datos, dict) else datos
    if isinstance(error, dict):
        return str(error.get("message") or error.get("detail") or error)[:300]
    return str(error)[:300]


def _espera(respuesta: httpx.Response | None, intento: int, base: float) -> float:
    if respuesta is not None:
        try:
            return min(float(respuesta.headers.get("retry-after", "")), ESPERA_MAXIMA)
        except ValueError:
            pass
    return min(base * (2 ** intento), ESPERA_MAXIMA)


def _llamada(datos: dict[str, str], indice: int) -> LlamadaHerramienta:
    crudo = datos["argumentos"].strip() or "{}"
    identificador = datos["id"] or f"llamada_{indice}"
    try:
        argumentos = json.loads(crudo)
    except json.JSONDecodeError:
        argumentos = None
    if not isinstance(argumentos, dict):
        return LlamadaHerramienta(id=identificador, nombre=datos["nombre"], argumentos_invalidos=crudo[:500])
    return LlamadaHerramienta(id=identificador, nombre=datos["nombre"], argumentos=argumentos)


def _vacia() -> dict[str, str]:
    return {"id": "", "nombre": "", "argumentos": ""}


class AIClient:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        settings: Settings | None = None,
        pausa_base: float = 1.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.transport = transport
        self.pausa_base = pausa_base

    # ------------------------------------------------------------------ rutas
    @staticmethod
    def _bearer(clave: str | None) -> dict[str, str]:
        hdrs = {"Content-Type": "application/json"}
        if clave:
            hdrs["Authorization"] = f"Bearer {clave}"
        return hdrs

    def ruta(self, modelo: str) -> Ruta:
        """Proveedor, endpoint y cabeceras para un modelo, según PROVIDER y las claves configuradas."""
        s = self.settings
        prov = s.provider.lower().strip()
        auto = prov in ("auto", "")
        espera = s.request_timeout_s

        if s.usa_local:
            return Ruta("local", "openai_compat", f"{s.local_base_url.rstrip('/')}/chat/completions",
                        self._bearer(None), None, s.local_timeout_s)
        if prov == "custom" or (auto and s.custom_base_url):
            base = (s.custom_base_url or "http://localhost:8000/v1").rstrip("/")
            return Ruta("custom", "openai_compat", f"{base}/chat/completions",
                        self._bearer(s.custom_api_key), s.custom_api_key, espera)
        if prov == "anthropic" or (auto and s.anthropic_api_key and modelo.startswith("claude-")):
            clave = s.anthropic_api_key
            return Ruta("anthropic", "anthropic", f"{s.anthropic_base_url.rstrip('/')}/messages", {
                "Content-Type": "application/json", "x-api-key": clave or "", "anthropic-version": "2023-06-01",
            }, clave, espera)
        directos = (
            ("openai", s.openai_api_key, s.openai_base_url, modelo.startswith(("gpt-", "o1", "o3", "o4"))),
            ("gemini", s.gemini_api_key, s.gemini_base_url, modelo.startswith("gemini-")),
            ("groq", s.groq_api_key, s.groq_base_url, "groq" in modelo or "llama-3" in modelo),
            ("deepseek", s.deepseek_api_key, s.deepseek_base_url, modelo.startswith("deepseek-")),
            ("mistral", s.mistral_api_key, s.mistral_base_url,
             modelo.startswith(("mistral-", "ministral-", "magistral-", "codestral-", "devstral-"))),
        )
        for nombre, clave, base, coincide in directos:
            if prov == nombre or (auto and clave and coincide):
                return Ruta(nombre, "openai_compat", f"{base.rstrip('/')}/chat/completions",
                            self._bearer(clave), clave, espera)
        hdrs = self._bearer(s.openrouter_api_key)
        hdrs.update({"HTTP-Referer": "https://github.com/pablomorenoc96/coop-executive", "X-Title": "CoopExecutive"})
        return Ruta("openrouter", "openai_compat", f"{s.openrouter_base_url.rstrip('/')}/chat/completions",
                    hdrs, s.openrouter_api_key, espera)

    def resolve_provider(self, target_model: str) -> tuple[str, str, dict[str, str]]:
        """Compatibilidad: (flavor, endpoint, headers)."""
        r = self.ruta(target_model)
        return r.flavor, r.endpoint, r.headers

    def _validar(self, ruta: Ruta, modelo: str) -> None:
        if ruta.proveedor in ("local", "custom"):
            return
        if ruta.proveedor == "openrouter" and not self.settings.openrouter_enabled:
            raise ErrorProveedor(
                f"No hay proveedor para «{modelo}»: OpenRouter está desactivado (OPENROUTER_ENABLED=false) "
                "y ninguna otra clave corresponde a ese modelo.", proveedor="openrouter", modelo=modelo)
        if not ruta.clave:
            variable = _VARIABLE_CLAVE[ruta.proveedor]
            ayuda = " Hay claves gratuitas en https://openrouter.ai/keys." if ruta.proveedor == "openrouter" else ""
            raise ErrorProveedor(
                f"Falta {variable} en el .env o en el entorno.{ayuda} "
                "Para trabajar sin nube: LOCAL_MODELS_ENABLED=true con Ollama.",
                proveedor=ruta.proveedor, modelo=modelo)

    def candidatos(self, modelo: str | None = None) -> list[str]:
        """Modelos a intentar, en orden."""
        s = self.settings
        if s.usa_local:
            locales = s.local_models_list or ["granite4.1:8b"]
            if modelo and "/" not in modelo:
                return list(dict.fromkeys([modelo, *locales]))
            return locales
        return list(dict.fromkeys([modelo or s.default_model, s.deep_reasoning_model]))

    # --------------------------------------------------------------- llamadas
    @staticmethod
    def _carga(ruta: Ruta, modelo: str, mensajes: list[dict[str, Any]], temperatura: float,
               herramientas: list[dict[str, Any]] | None, max_tokens: int) -> dict[str, Any]:
        if ruta.flavor == "anthropic":
            sistema, limpios = mensajes_anthropic(mensajes)
            carga: dict[str, Any] = {"model": modelo, "messages": limpios, "max_tokens": max_tokens,
                                     "temperature": temperatura, "stream": True}
            if sistema:
                carga["system"] = sistema
            if herramientas:
                carga["tools"] = herramientas_anthropic(herramientas)
            return carga
        carga = {"model": modelo, "messages": mensajes, "temperature": temperatura, "stream": True}
        if herramientas:
            carga["tools"] = herramientas_openai(herramientas)
        return carga

    def _error(self, ruta: Ruta, modelo: str, estado: int | None, cuerpo: str) -> ErrorProveedor:
        detalle = censurar(_detalle(cuerpo), [ruta.clave])
        if estado is None:
            if ruta.proveedor == "local":
                texto = (f"No se pudo conectar con Ollama en {self.settings.local_base_url} ({detalle}). "
                         "Revise que `ollama serve` esté corriendo y que el modelo esté descargado.")
            else:
                texto = f"Sin conexión con {ruta.proveedor} ({detalle})."
        elif estado in (401, 403):
            variable = _VARIABLE_CLAVE.get(ruta.proveedor, "la clave")
            texto = f"{ruta.proveedor} rechazó la clave (HTTP {estado}). Revise {variable}. {detalle}"
        elif estado == 402:
            texto = f"{ruta.proveedor} indica que no hay saldo o créditos (HTTP 402). {detalle}"
        elif estado == 404:
            texto = (f"El modelo «{modelo}» no está disponible en {ruta.proveedor} (HTTP 404). "
                     f"Revise DEFAULT_MODEL; `coopexecutive modelos` lista los gratuitos vigentes. {detalle}")
        else:
            texto = f"{ruta.proveedor} respondió HTTP {estado}. {detalle}"
        return ErrorProveedor(texto.strip(), estado=estado, proveedor=ruta.proveedor, modelo=modelo)

    async def eventos(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[Evento]:
        """Eventos de la respuesta. Reintenta con backoff y, si se agotan, pasa al siguiente modelo."""
        modelos = self.candidatos(model)
        ultimo: ErrorProveedor | None = None
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_s, transport=self.transport) as http:
            for posicion, modelo in enumerate(modelos):
                ruta = self.ruta(modelo)
                try:
                    self._validar(ruta, modelo)
                except ErrorProveedor as exc:
                    if posicion == 0:
                        raise
                    ultimo = exc
                    continue
                carga = self._carga(ruta, modelo, messages, temperature, tools, max_tokens)
                lector = self._leer_anthropic if ruta.flavor == "anthropic" else self._leer_openai
                for intento in range(self.settings.max_reintentos + 1):
                    emitido = False
                    respuesta: httpx.Response | None = None
                    estado: int | None = None
                    try:
                        async with http.stream("POST", ruta.endpoint, headers=ruta.headers, json=carga,
                                               timeout=ruta.timeout) as respuesta:
                            if respuesta.status_code == 200:
                                async for evento in lector(respuesta, modelo, ruta):
                                    emitido = True
                                    yield evento
                                return
                            estado = respuesta.status_code
                            cuerpo = (await respuesta.aread()).decode("utf-8", errors="replace")
                    except (httpx.TransportError, httpx.TimeoutException) as exc:
                        if emitido:
                            raise ErrorProveedor(f"La conexión con {ruta.proveedor} se cortó a media respuesta "
                                                 f"({type(exc).__name__}).", proveedor=ruta.proveedor,
                                                 modelo=modelo) from exc
                        estado, cuerpo, respuesta = None, type(exc).__name__, None
                    ultimo = self._error(ruta, modelo, estado, cuerpo)
                    if estado is not None and estado not in REINTENTABLES:
                        raise ultimo
                    if intento < self.settings.max_reintentos:
                        pausa = _espera(respuesta, intento, self.pausa_base)
                        log.info("%s; reintento %d en %.1f s", ultimo, intento + 1, pausa)
                        await asyncio.sleep(pausa)
                log.warning("%s; se pasa al siguiente modelo", ultimo)
        raise ultimo or ErrorProveedor("No hay modelos configurados.")

    async def _leer_openai(self, respuesta: httpx.Response, modelo: str, ruta: Ruta) -> AsyncIterator[Evento]:
        llamadas: dict[int, dict[str, str]] = {}
        motivo = "stop"
        async for linea in respuesta.aiter_lines():
            if not linea.startswith("data:"):
                continue
            dato = linea[5:].strip()
            if dato == "[DONE]":
                break
            try:
                trozo = json.loads(dato)
            except json.JSONDecodeError:
                continue
            if trozo.get("error"):
                raise ErrorProveedor(censurar(_detalle(dato), [ruta.clave]), proveedor=ruta.proveedor, modelo=modelo)
            for opcion in trozo.get("choices") or []:
                delta = opcion.get("delta") or opcion.get("message") or {}
                if delta.get("content"):
                    yield TextoDelta(delta["content"])
                for parcial in delta.get("tool_calls") or []:
                    actual = llamadas.setdefault(int(parcial.get("index", len(llamadas))), _vacia())
                    funcion = parcial.get("function") or {}
                    actual["id"] = parcial.get("id") or actual["id"]
                    actual["nombre"] += funcion.get("name") or ""
                    argumentos = funcion.get("arguments")
                    if isinstance(argumentos, dict):
                        argumentos = json.dumps(argumentos)
                    actual["argumentos"] += argumentos or ""
                if opcion.get("finish_reason"):
                    motivo = opcion["finish_reason"]
        for indice in sorted(llamadas):
            yield _llamada(llamadas[indice], indice)
        yield Fin(motivo="tool_calls" if llamadas else motivo, modelo=modelo, proveedor=ruta.proveedor)

    async def _leer_anthropic(self, respuesta: httpx.Response, modelo: str, ruta: Ruta) -> AsyncIterator[Evento]:
        bloques: dict[int, dict[str, str]] = {}
        motivo = "stop"
        async for linea in respuesta.aiter_lines():
            if not linea.startswith("data:"):
                continue
            try:
                trozo = json.loads(linea[5:].strip())
            except json.JSONDecodeError:
                continue
            tipo = trozo.get("type")
            indice = trozo.get("index", 0)
            if tipo == "error":
                raise ErrorProveedor(censurar(_detalle(json.dumps(trozo)), [ruta.clave]),
                                     proveedor=ruta.proveedor, modelo=modelo)
            if tipo == "content_block_start":
                bloque = trozo.get("content_block") or {}
                if bloque.get("type") == "tool_use":
                    bloques[indice] = {"id": bloque.get("id", ""), "nombre": bloque.get("name", ""), "argumentos": ""}
            elif tipo == "content_block_delta":
                delta = trozo.get("delta") or {}
                if delta.get("type") == "input_json_delta":
                    bloques.setdefault(indice, _vacia())["argumentos"] += delta.get("partial_json", "")
                elif delta.get("text"):
                    yield TextoDelta(delta["text"])
            elif tipo == "content_block_stop" and indice in bloques:
                yield _llamada(bloques.pop(indice), indice)
            elif tipo == "message_delta":
                razon = (trozo.get("delta") or {}).get("stop_reason")
                if razon:
                    motivo = {"tool_use": "tool_calls", "max_tokens": "length"}.get(razon, "stop")
            elif tipo == "message_stop":
                break
        yield Fin(motivo=motivo, modelo=modelo, proveedor=ruta.proveedor)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Solo el texto de la respuesta. Lanza ErrorProveedor si falla."""
        async for evento in self.eventos(messages, model=model, temperature=temperature, tools=tools):
            if isinstance(evento, TextoDelta):
                yield evento.texto

    async def completar(self, messages: list[dict[str, Any]], model: str | None = None,
                        temperature: float = 0.2) -> str:
        """Respuesta completa como texto."""
        return "".join([t async for t in self.stream_chat(messages, model=model, temperature=temperature)])
