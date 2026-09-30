"""API local y panel web.

Solo escucha en 127.0.0.1. Cada arranque genera un token que viaja en el fragmento
de la URL (`#token=…`, nunca llega al servidor en la petición de la página) y que el
panel envía como `Authorization: Bearer`. Se rechazan los `Host` ajenos (rebinding
de DNS) y los `Origin` de otros sitios en las peticiones que no son GET. Las
herramientas que escriben exigen `confirmar: true`; en el chat, la confirmación la
da la persona desde el panel.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import secrets
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from coopexecutive import __version__, bitacora, herramientas
from coopexecutive.herramientas import Herramienta, Resultado
from coopexecutive.registro import obtener

registro = obtener(__name__)

ESTATICOS = Path(__file__).resolve().parent / "static"
ARCHIVOS = {"": ("index.html", "text/html"), "app.js": ("app.js", "text/javascript"),
            "app.css": ("app.css", "text/css")}
ESPERA_CONFIRMACION = 300  # segundos
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


class EntradaHerramienta(BaseModel):
    argumentos: dict[str, Any] = Field(default_factory=dict)
    confirmar: bool = False


class EntradaChat(BaseModel):
    mensaje: str = Field(min_length=1, max_length=8000)
    historial: list[dict[str, str]] = Field(default_factory=list, max_length=40)
    rol: str | None = None
    solo_lectura: bool = False


class EntradaConfirmacion(BaseModel):
    autorizar: bool


def _consulta(nombre: str, **argumentos: Any) -> dict[str, Any]:
    """Ejecuta una herramienta de solo lectura sin pasar por la bitácora (las lecturas del panel no son acciones)."""
    h = herramientas.obtener(nombre)
    assert h is not None and not h.escribe
    try:
        return h.funcion(h.Entrada.model_validate(argumentos))
    except ValidationError as exc:
        raise HTTPException(422, "Parámetros no válidos.") from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _sse(evento: str, datos: dict[str, Any]) -> str:
    return f"event: {evento}\ndata: {json.dumps(datos, ensure_ascii=False, default=str)}\n\n"


def crear_app(token: str, puerto: int = 8765) -> FastAPI:
    from coopexecutive.memory.episodic import initialize_db

    initialize_db()
    app = FastAPI(title="CoopExecutive", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    origenes = {f"http://127.0.0.1:{puerto}", f"http://localhost:{puerto}"}
    pendientes: dict[str, asyncio.Future[bool]] = {}
    app.state.pendientes = pendientes

    @app.middleware("http")
    async def seguridad(request: Request, siguiente):
        ruta = request.url.path
        if ruta.startswith("/api/"):
            if request.method != "GET":
                origen = request.headers.get("origin")
                if origen is not None and origen not in origenes:
                    return JSONResponse({"detail": "Origen no permitido."}, status_code=403)
            recibido = request.headers.get("authorization", "")
            if not hmac.compare_digest(recibido.encode(), f"Bearer {token}".encode()):
                return JSONResponse({"detail": "Falta el token del panel; abra el enlace que mostró la terminal."},
                                    status_code=401)
        respuesta = await siguiente(request)
        respuesta.headers["Content-Security-Policy"] = CSP
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        respuesta.headers["X-Frame-Options"] = "DENY"
        if ruta.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    # --- Páginas ------------------------------------------------------------------------------

    def _estatico(nombre: str) -> FileResponse:
        archivo, tipo = ARCHIVOS[nombre]
        return FileResponse(ESTATICOS / archivo, media_type=f"{tipo}; charset=utf-8")

    @app.get("/", include_in_schema=False)
    def inicio() -> FileResponse:
        return _estatico("")

    @app.get("/app.js", include_in_schema=False)
    def script() -> FileResponse:
        return _estatico("app.js")

    @app.get("/app.css", include_in_schema=False)
    def estilos() -> FileResponse:
        return _estatico("app.css")

    # --- Consultas ----------------------------------------------------------------------------

    @app.get("/api/estado")
    def estado() -> dict[str, Any]:
        from coopexecutive.config import get_settings

        settings = get_settings()
        perfil = _consulta("ver_perfil")
        fecha = _consulta("fecha_y_plazos")
        v = bitacora.verificar()
        if settings.usa_local:
            proveedor, modelo = "local (Ollama)", ", ".join(settings.local_models_list)
        else:
            proveedor, modelo = settings.provider, settings.default_model
        return {
            "version": __version__, "organizacion": perfil["nombre"], "figura": perfil["figura"],
            "hoy": fecha["hoy"], "hoy_texto": fecha["hoy_texto"], "proveedor": proveedor, "modelo": modelo,
            "conteos": {
                "financiadores": len(_consulta("buscar_financiadores", limite=100)["financiadores"]),
                "expedientes_abiertos": len(_consulta("listar_expedientes", limite=200)["expedientes"]),
                "evaluaciones": len(_consulta("listar_evaluaciones", limite=50)["evaluaciones"]),
                "documentos": len(_consulta("listar_documentos", limite=200)["documentos"]),
            },
            "bitacora": {"integra": v.integra, "total": v.total},
        }

    @app.get("/api/perfil")
    def perfil() -> dict[str, Any]:
        return _consulta("ver_perfil")

    @app.get("/api/financiadores")
    def financiadores(texto: str = "", limite: int = 50) -> dict[str, Any]:
        return _consulta("buscar_financiadores", texto=texto, limite=limite)

    @app.get("/api/financiadores/{folio}")
    def financiador(folio: str) -> dict[str, Any]:
        return _consulta("ver_financiador", folio=folio)

    @app.get("/api/expedientes")
    def expedientes(estado: str = "abiertos", limite: int = 100) -> dict[str, Any]:
        return _consulta("listar_expedientes", estado=estado, limite=limite)

    @app.get("/api/expedientes/{folio}")
    def expediente(folio: str) -> dict[str, Any]:
        return _consulta("ver_expediente", folio=folio)

    @app.get("/api/evaluaciones")
    def evaluaciones(limite: int = 20) -> dict[str, Any]:
        return _consulta("listar_evaluaciones", limite=limite)

    @app.get("/api/documentos")
    def documentos(limite: int = 50) -> dict[str, Any]:
        return _consulta("listar_documentos", limite=limite)

    @app.get("/api/monitoreo")
    def monitoreo() -> dict[str, Any]:
        return _consulta("ultimo_monitoreo")

    @app.get("/api/asamblea")
    def asamblea() -> dict[str, Any]:
        return _consulta("listar_propuestas_asamblea")

    @app.get("/api/bitacora")
    def ver_bitacora(limite: int = 50, canal: str | None = None) -> dict[str, Any]:
        if canal is not None and canal not in bitacora.CANALES:
            raise HTTPException(422, "Canal no válido.")
        v = bitacora.verificar()
        registros = [
            {"id": r.id, "registrado_en": r.registrado_en, "canal": r.canal, "accion": r.accion,
             "parametros": r.parametros, "estado": r.estado, "resultado": r.resultado, "hash": r.hash}
            for r in bitacora.ver(max(1, min(limite, 500)), canal)
        ]
        return {"registros": registros, "verificacion": {"integra": v.integra, "total": v.total,
                                                          "roto_en": v.roto_en, "motivo": v.motivo}}

    # --- Herramientas -------------------------------------------------------------------------

    @app.get("/api/herramientas")
    def listar_herramientas() -> dict[str, Any]:
        return {"herramientas": [
            {"nombre": h.nombre, "descripcion": h.descripcion, "escribe": h.escribe, "red": h.red,
             "esquema": h.esquema()} for h in herramientas.todas()
        ]}

    @app.post("/api/herramientas/{nombre}")
    async def usar_herramienta(nombre: str, entrada: EntradaHerramienta) -> JSONResponse:
        h = herramientas.obtener(nombre)
        if h is None:
            raise HTTPException(404, f"No existe la herramienta «{nombre}».")
        if h.escribe and not entrada.confirmar:
            return JSONResponse({"requiere_confirmacion": True, "resumen": h.resumen(entrada.argumentos)},
                                status_code=409)
        r = await asyncio.to_thread(herramientas.ejecutar, nombre, entrada.argumentos, canal="http",
                                    autorizada=entrada.confirmar)
        return JSONResponse({"estado": r.estado, **json.loads(json.dumps(r.datos, default=str))},
                            status_code=200 if r.ok else 400)

    # --- Chat ---------------------------------------------------------------------------------

    @app.post("/api/chat/confirmar/{id_confirmacion}")
    def confirmar(id_confirmacion: str, entrada: EntradaConfirmacion) -> dict[str, Any]:
        futuro = pendientes.get(id_confirmacion)
        if futuro is None or futuro.done():
            raise HTTPException(404, "No hay una confirmación pendiente con ese identificador.")
        futuro.get_loop().call_soon_threadsafe(futuro.set_result, entrada.autorizar)
        return {"ok": True}

    @app.post("/api/chat")
    async def chat(entrada: EntradaChat) -> StreamingResponse:
        from coopexecutive.orchestrator.coop_executive import ROLES

        if entrada.rol is not None and entrada.rol not in ROLES:
            raise HTTPException(422, "Rol no válido.")
        historial = [m for m in entrada.historial if m.get("role") in ("user", "assistant") and m.get("content")]
        return StreamingResponse(_turno_chat(entrada, historial, pendientes), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app


async def _turno_chat(entrada: EntradaChat, historial: list[dict[str, str]],
                      pendientes: dict[str, asyncio.Future[bool]]) -> AsyncIterator[str]:
    """Corre el turno en una tarea y reenvía sus eventos como SSE; las confirmaciones esperan al panel."""
    from coopexecutive.guardrails import revisar_respuesta
    from coopexecutive.orchestrator.agente import contexto_de, ejecutar_turno, resumen_acciones
    from coopexecutive.orchestrator.coop_executive import CoopExecutive
    from coopexecutive.providers import ErrorProveedor
    from coopexecutive.providers.tipos import TextoDelta
    from coopexecutive.utils.fechas import hoy_local

    cola: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    async def pedir(h: Herramienta, argumentos: dict[str, Any]) -> bool:
        id_confirmacion = uuid.uuid4().hex
        futuro: asyncio.Future[bool] = loop.create_future()
        pendientes[id_confirmacion] = futuro
        await cola.put(_sse("confirmacion", {"id": id_confirmacion, "herramienta": h.nombre,
                                             "descripcion": h.descripcion, "argumentos": argumentos}))
        try:
            return await asyncio.wait_for(futuro, ESPERA_CONFIRMACION)
        except TimeoutError:
            return False
        finally:
            pendientes.pop(id_confirmacion, None)

    async def correr() -> None:
        texto = ""
        resultados: list[Resultado] = []
        try:
            executive = CoopExecutive()
            disponibles = herramientas.todas(solo_lectura=entrada.solo_lectura)
            async for evento in ejecutar_turno(executive, entrada.mensaje, historial, rol=entrada.rol,
                                               confirmar=pedir, disponibles=disponibles, canal="http"):
                if isinstance(evento, TextoDelta):
                    texto += evento.texto
                    await cola.put(_sse("texto", {"texto": evento.texto}))
                elif isinstance(evento, Resultado):
                    resultados.append(evento)
                    await cola.put(_sse("accion", {
                        "herramienta": evento.nombre, "estado": evento.estado, "escribe": evento.escribe,
                        "resumen": str(evento.datos.get("error") or evento.datos.get("resumen") or ""),
                    }))
                else:
                    await cola.put(_sse("aviso", {"texto": evento.texto}))
            escritas = any(r.ok and r.escribe for r in resultados)
            contexto = f"{entrada.mensaje}\n{executive.profile.to_prompt_block()}\n{contexto_de(resultados)}"
            revision = revisar_respuesta(texto, contexto, acciones_ejecutadas=escritas,
                                         hoy=hoy_local(executive.settings.user_timezone))
            await cola.put(_sse("fin", {"observaciones": revision.observaciones,
                                        "acciones": resumen_acciones(resultados)}))
        except ErrorProveedor as exc:
            await cola.put(_sse("error", {"mensaje": str(exc)}))
        except Exception:  # noqa: BLE001 - el panel debe recibir un cierre aunque algo falle
            registro.exception("Falló un turno del chat del panel.")
            await cola.put(_sse("error", {"mensaje": "Error interno; revise la terminal."}))
        finally:
            await cola.put(None)

    tarea = asyncio.create_task(correr())
    try:
        while (parte := await cola.get()) is not None:
            yield parte
    finally:
        if not tarea.done():
            tarea.cancel()
