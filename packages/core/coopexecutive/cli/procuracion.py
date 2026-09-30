"""Comandos de procuración: espacio de trabajo, autoconfiguración y evaluación de oportunidades."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import ValidationError
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from coopexecutive.cli._consola import console, fallar
from coopexecutive.cli._modelo import consultar, ejecutar, extraer_json
from coopexecutive.config import ARCHIVO_PERFIL, get_settings, usar_espacio
from coopexecutive.crm import cases
from coopexecutive.governance.voting import create_proposal
from coopexecutive.grant_tools import matrix
from coopexecutive.grant_tools.matrix import CRITERIOS, EntradaMatriz, ResultadoMatriz
from coopexecutive.guardrails import MONTO_POR_DEFINIR, agregar_leyenda, pendiente, revisar_respuesta
from coopexecutive.lectura import ErrorLectura, leer_archivo, leer_url
from coopexecutive.memory import desde_sitio, onboarding
from coopexecutive.memory.company_profile import TIPOS_ORGANIZACION, CoopProfile
from coopexecutive.memory.episodic import initialize_db
from coopexecutive.utils.fechas import hoy_local
from coopexecutive.utils.rutas import para_mostrar

# --- iniciar -------------------------------------------------------------------


@click.command("iniciar")
@click.argument("ruta", required=False, type=click.Path(file_okay=False, path_type=Path))
@click.option("--nombre", required=True, help="Nombre de la organización.")
@click.option(
    "--tipo",
    type=click.Choice(list(TIPOS_ORGANIZACION)),
    default="cooperativa",
    show_default=True,
    help="Tipo de organización.",
)
@click.pass_context
def iniciar(ctx: click.Context, ruta: Path | None, nombre: str, tipo: str) -> None:
    """Crear un espacio de trabajo: carpeta, perfil mínimo, base de datos y salidas/."""
    ruta = ruta or (ctx.obj or {}).get("espacio") or Path.cwd()
    try:
        espacio = onboarding.crear_espacio(ruta, nombre, tipo)  # type: ignore[arg-type]
    except (OSError, ValueError) as exc:
        fallar(str(exc))
    usar_espacio(espacio.ruta)
    initialize_db()
    settings = get_settings()
    perfil = "creado" if espacio.perfil_creado else "ya existía; no se modificó"
    console.print(Panel(
        f"[bold green]Espacio listo[/bold green]\n\n"
        f"Carpeta: {para_mostrar(espacio.ruta)}\n"
        f"Perfil ({ARCHIVO_PERFIL}): {perfil}\n"
        f"Base de datos: {settings.episodic_db_path.name}\n\n"
        f"Siguiente paso: [cyan]coopexecutive --espacio \"{para_mostrar(espacio.ruta)}\" configurar[/cyan]",
        title="Espacio de trabajo",
        border_style="green",
    ))


# --- configurar ----------------------------------------------------------------

ETIQUETAS: dict[str, str] = {
    "nombre": "Nombre",
    "siglas": "Siglas o nombre corto",
    "figura": "Figura jurídica",
    "mision": "Misión",
    "poblacion": "Población atendida (separe con ;)",
    "territorio": "Territorio",
    "programas": "Programas (separe con ;)",
    "ejes": "Ejes de trabajo (separe con ;)",
    "metricas": "Métricas verificables (separe con ;)",
    "estatus_legal": "Estatus legal",
    "estatus_fiscal": "Estatus fiscal",
    "rango_minimo": "Monto mínimo (vacío si está por definir)",
    "rango_maximo": "Monto máximo (vacío si está por definir)",
    "moneda": "Moneda (código ISO, por ejemplo MXN)",
    "alianzas": "Alianzas (separe con ;)",
    "financiadores": "Financiadores con los que ha trabajado (separe con ;)",
    "aprobadores": "Quién aprueba las solicitudes (separe con ;)",
    "mecanismos_cobro": "Medios para recibir donativos o pagos (separe con ;)",
}


def _como_texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, list):
        return "; ".join(str(v) for v in valor)
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


ORIGEN_USUARIO = "Dato del usuario"
_EN_EL_SITIO = re.compile(r"^(esta|está)?\s*en (nuestro|el) sitio( web)?\.?$", re.IGNORECASE)


def _responder_modelo(pedido: str) -> str:
    texto, _ = ejecutar(consultar(pedido, None))
    return texto


class _Sitio:
    """Lee el sitio una sola vez, sea por --sitio o porque una respuesta dice «está en nuestro sitio»."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url
        self.paginas: list[desde_sitio.Pagina] | None = None

    def leer(self) -> list[desde_sitio.Pagina]:
        if self.paginas is None:
            if not self.url:
                self.url = click.prompt("  Enlace del sitio web de la organización").strip()
            with console.status("Leyendo el sitio..."):
                try:
                    rastreo = desde_sitio.rastrear(self.url)
                except ErrorLectura as exc:
                    fallar(str(exc), "No se pudo leer el sitio")
            self.paginas = rastreo.paginas
            console.print(f"[dim]Páginas leídas: {', '.join(p.url for p in rastreo.paginas)}[/dim]",
                          highlight=False)
            for omitida in rastreo.omitidas:
                console.print(f"[dim]Omitida: {omitida}[/dim]", highlight=False)
        return self.paginas

    def proponer(self, numeros: set[int] | None = None) -> dict[str, desde_sitio.Propuesta]:
        paginas = self.leer()
        with console.status("Preparando la propuesta..."):
            return desde_sitio.proponer(paginas, _responder_modelo, numeros)


def _revisar_propuesta(campo: str, propuesta: desde_sitio.Propuesta | None, actual: Any,
                       respuestas: dict[str, Any], origenes: dict[str, str]) -> None:
    """«sí» acepta, otro texto corrige y Enter deja el campo como estaba (pendiente si estaba vacío)."""
    if propuesta is None or propuesta.pendiente:
        console.print(f"  {ETIQUETAS[campo]}: [yellow]Pendiente[/yellow] [dim](sin evidencia en el sitio)[/dim]")
        valor = click.prompt("    Escriba el dato o Enter para no cambiarlo", default="", show_default=False)
        if valor.strip():
            respuestas[campo], origenes[campo] = valor, ORIGEN_USUARIO
        return
    console.print(f"  {ETIQUETAS[campo]}: [bold]{_como_texto(propuesta.valor)}[/bold]", highlight=False)
    console.print(f"    [dim]Evidencia: «{propuesta.evidencia}» ({propuesta.url})[/dim]", highlight=False)
    if actual not in (None, "", []):
        console.print(f"    [dim]Valor actual: {_como_texto(actual)}[/dim]", highlight=False)
    valor = click.prompt("    «sí» acepta, otro texto corrige, Enter no lo cambia",
                         default="", show_default=False).strip()
    if valor.lower() in {"sí", "si", "s"}:
        respuestas[campo], origenes[campo] = propuesta.valor, propuesta.url
    elif valor:
        respuestas[campo], origenes[campo] = valor, ORIGEN_USUARIO


def _preguntar(actuales: dict[str, Any], sitio: _Sitio) -> tuple[dict[str, Any], dict[str, str]]:
    respuestas: dict[str, Any] = {}
    origenes: dict[str, str] = {}
    console.print("[dim]Enter conserva el valor entre corchetes. Lo que no sepa, déjelo vacío. "
                  "Si el dato está publicado, responda «está en nuestro sitio».[/dim]")
    for pregunta in onboarding.PREGUNTAS:
        console.print(f"\n[bold cyan]{pregunta.numero}. {pregunta.texto}[/bold cyan]")
        for campo in pregunta.campos:
            valor = click.prompt(
                f"  {ETIQUETAS[campo]}", default=_como_texto(actuales.get(campo)), show_default=True
            )
            if not _EN_EL_SITIO.match(valor.strip()):
                respuestas[campo] = valor
                continue
            propuestas = sitio.proponer({pregunta.numero})
            pendientes = [c for c in pregunta.campos if c not in respuestas]
            for otro in pendientes:
                if otro in desde_sitio.CAMPOS_PRIVADOS:
                    respuestas[otro] = click.prompt(f"  {ETIQUETAS[otro]}", default=_como_texto(actuales.get(otro)))
                else:
                    _revisar_propuesta(otro, propuestas.get(otro), actuales.get(otro), respuestas, origenes)
            break
    return respuestas, origenes


def _desde_sitio(actuales: dict[str, Any], sitio: _Sitio) -> tuple[dict[str, Any], dict[str, str]]:
    propuestas = sitio.proponer()
    respuestas: dict[str, Any] = {}
    origenes: dict[str, str] = {}
    console.print("\n[dim]Cada propuesta cita la página de donde sale. Montos, moneda y aprobadores "
                  "no se toman del sitio.[/dim]")
    for pregunta in onboarding.PREGUNTAS:
        console.print(f"\n[bold cyan]{pregunta.numero}. {pregunta.texto}[/bold cyan]")
        for campo in pregunta.campos:
            if campo in desde_sitio.CAMPOS_PRIVADOS:
                respuestas[campo] = click.prompt(
                    f"  {ETIQUETAS[campo]}", default=_como_texto(actuales.get(campo)), show_default=True
                )
                continue
            _revisar_propuesta(campo, propuestas.get(campo), actuales.get(campo), respuestas, origenes)
    return respuestas, origenes


@click.command("configurar")
@click.option(
    "--desde",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Archivo YAML con las respuestas; guarda sin preguntar.",
)
@click.option("--sitio", default=None,
              help="Enlace del sitio web de la organización: propone cada respuesta con su evidencia.")
def configurar(desde: Path | None, sitio: str | None) -> None:
    """Completar el perfil con diez preguntas o a partir del sitio web. Respalda el perfil antes de escribir."""
    if desde is not None and sitio is not None:
        fallar("Use --desde o --sitio, no ambos.")
    ruta = get_settings().company_profile_path
    origenes: dict[str, str] = {}
    try:
        datos = onboarding.leer_perfil_crudo(ruta)
        if desde is not None:
            respuestas = yaml.safe_load(desde.read_text(encoding="utf-8")) or {}
            if not isinstance(respuestas, dict):
                fallar(f"{desde.name} debe contener pares campo: valor.")
        elif sitio is not None:
            respuestas, origenes = _desde_sitio(onboarding.respuestas_actuales(datos), _Sitio(sitio))
        else:
            respuestas, origenes = _preguntar(onboarding.respuestas_actuales(datos), _Sitio())
        nuevo = onboarding.aplicar_respuestas(datos, respuestas, origenes)
    except (ValueError, yaml.YAMLError) as exc:
        fallar(str(exc), "Perfil no válido")

    perfil = CoopProfile(**nuevo)
    console.print(Panel(Markdown(perfil.to_prompt_block()), title="Resumen del perfil", border_style="cyan"))
    if desde is None and not click.confirm("¿Guardar el perfil?", default=True):
        console.print("[dim]No se guardó ningún cambio.[/dim]")
        return
    respaldo = onboarding.guardar_perfil(ruta, nuevo)
    mensaje = f"[bold green]Perfil guardado[/bold green] en {para_mostrar(ruta)}"
    if respaldo is not None:
        mensaje += f"\nRespaldo del perfil anterior: {respaldo.name}"
    console.print(mensaje)


# --- evaluar-convocatoria ----------------------------------------------------------

def _instrucciones_json(bases: str) -> str:
    criterios = "\n".join(
        f'    "{clave}": {{"puntos": entero de 0 a {peso} o null, "evidencia": "cita o dato de las bases"}},'
        for clave, (_, peso) in CRITERIOS.items()
    )
    return (
        "Lee las bases de la oportunidad y propón la entrada de la matriz de evaluación. "
        "Responde SOLO con un objeto JSON, sin texto adicional, con esta forma:\n\n"
        "{\n"
        '  "convocatoria": "nombre de la oportunidad",\n'
        '  "financiador": "quién otorga el recurso",\n'
        '  "tipo": "convocatoria | beca | premio | credito | otro",\n'
        '  "monto": "monto con moneda ISO tal como aparece, o vacío",\n'
        '  "fecha_cierre": "AAAA-MM-DD o null",\n'
        '  "evidencia_plazo": "cita de las bases sobre la fecha de cierre, o vacío",\n'
        '  "elegibilidad": "confirmada | excluida | pendiente",\n'
        '  "vigencia": "vigente | vencida | pendiente",\n'
        '  "tension": "ninguna | resuelta | pendiente | posicion_publica",\n'
        '  "tension_detalle": "",\n'
        '  "criterios": {\n'
        f"{criterios}\n"
        "  }\n"
        "}\n\n"
        "Reglas: usa null cuando no haya evidencia (no pongas cero). No inventes montos ni fechas. "
        "Los puntos de tiempos dependen de los días que faltan desde la fecha de hoy.\n\n"
        f"Bases:\n{bases}"
    )


def _mostrar_propuesta(entrada: EntradaMatriz) -> None:
    tabla = Table(title=f"Propuesta del modelo: {entrada.convocatoria}", header_style="bold cyan")
    tabla.add_column("Criterio")
    tabla.add_column("Puntos", justify="center")
    tabla.add_column("Evidencia", ratio=1)
    for clave, (nombre, peso) in CRITERIOS.items():
        cal = entrada.criterios.get(clave)
        puntos = "pendiente" if cal is None or cal.puntos in (None, "") else f"{cal.puntos} / {peso}"
        tabla.add_row(nombre, puntos, cal.evidencia if cal else "")
    console.print(tabla)
    console.print(
        f"Cierre: {entrada.fecha_cierre or 'por confirmar'} | Elegibilidad: {entrada.elegibilidad} | "
        f"Vigencia: {entrada.vigencia} | Tensión: {entrada.tension}"
    )


def _entrada_interactiva() -> dict[str, Any]:
    datos: dict[str, Any] = {
        "convocatoria": click.prompt("Nombre de la oportunidad"),
        "financiador": click.prompt("Financiador", default="", show_default=False),
        "tipo": click.prompt(
            "Tipo", type=click.Choice(["convocatoria", "beca", "premio", "credito", "otro"]), default="convocatoria"
        ),
        "monto": click.prompt("Monto con moneda (vacío si no se conoce)", default="", show_default=False),
    }
    cierre = click.prompt("Fecha de cierre AAAA-MM-DD (vacío si no se conoce)", default="", show_default=False)
    if cierre.strip():
        datos["fecha_cierre"] = cierre.strip()
        datos["evidencia_plazo"] = click.prompt("Fuente de la fecha de cierre")
    for campo, opciones, omision in (
        ("elegibilidad", ["confirmada", "excluida", "pendiente"], "pendiente"),
        ("vigencia", ["vigente", "vencida", "pendiente"], "pendiente"),
        ("tension", ["ninguna", "resuelta", "pendiente", "posicion_publica"], "ninguna"),
    ):
        datos[campo] = click.prompt(campo.capitalize(), type=click.Choice(opciones), default=omision)
    if datos["tension"] in ("pendiente", "posicion_publica"):
        datos["tension_detalle"] = click.prompt("Describa la tensión")
    console.print("[dim]Deje vacío un criterio sin evidencia: queda pendiente, no vale cero.[/dim]")
    criterios: dict[str, dict[str, str]] = {}
    for clave, (nombre, peso) in CRITERIOS.items():
        puntos = click.prompt(f"{nombre} (0 a {peso})", default="", show_default=False)
        evidencia = click.prompt("  Evidencia", default="", show_default=False) if puntos.strip() else ""
        criterios[clave] = {"puntos": puntos, "evidencia": evidencia}
    datos["criterios"] = criterios
    return datos


def _leer_bases(origen: str) -> str:
    """Texto de las bases: una URL (página o PDF), un archivo local o el texto mismo."""
    limpio = origen.strip()
    try:
        if re.match(r"^https?://", limpio, re.IGNORECASE):
            return leer_url(limpio)
        ruta = Path(limpio)
        if len(limpio) < 1024 and ruta.is_file():
            return leer_archivo(ruta)
    except ErrorLectura as exc:
        fallar(str(exc), "No se pudieron leer las bases")
    return origen


def _analisis_redactado(resultado: ResultadoMatriz, bases: str) -> None:
    pedido = (
        "Redacta un análisis breve (máximo 300 palabras) del resultado de la matriz que aparece abajo. "
        "No cambies la decisión, el puntaje ni el plazo; explícalos. Usa solo datos de las bases o del perfil. "
        "Termina con una sección CONTRAPUNTO y con el siguiente paso.\n\n"
        f"{resultado.to_markdown()}"
    )
    try:
        texto, perfil = asyncio.run(consultar(pedido))
    except Exception as exc:  # el resultado de la matriz ya se mostró; el análisis es opcional
        console.print(f"[yellow]No se pudo redactar el análisis: {exc}[/yellow]")
        return
    contexto = f"{bases}\n{perfil}\n{resultado.to_markdown()}"
    revision = revisar_respuesta(texto, contexto, hoy=resultado.fecha_evaluacion)
    console.print(Panel(Markdown(agregar_leyenda(revision.texto)), title="Análisis", border_style="cyan"))
    if revision.observaciones:
        console.print(Panel("\n".join(f"- {o}" for o in revision.observaciones),
                            title="Revisión automática", border_style="yellow"))


@click.command("evaluar-convocatoria")
@click.argument("origen", required=False)
@click.option("--archivo", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="YAML con la entrada de la matriz (puntajes y evidencias).")
@click.option("--asistido", "asistido", default=None,
              help="Texto o archivo con las bases: el modelo propone los puntajes y usted confirma.")
@click.option("--expediente", default=None, help="Folio EXP-AAAA-NNNN al que se vincula la evaluación.")
@click.option("--guardar/--no-guardar", default=True, show_default=True, help="Guardar el resultado en la base.")
@click.option("--si", "aceptar", is_flag=True, help="Aceptar la propuesta del modelo sin preguntar.")
@click.option("--proponer-asamblea", is_flag=True,
              help="Si la decisión es APLICAR, somete la postulación a la asamblea.")
def evaluar_convocatoria(
    origen: str | None,
    archivo: Path | None,
    asistido: str | None,
    expediente: str | None,
    guardar: bool,
    aceptar: bool,
    proponer_asamblea: bool,
) -> None:
    """Evaluar una oportunidad con la matriz de 100 puntos.

    Sin argumentos pregunta cada dato. Con --archivo lee un YAML. Con un ORIGEN o
    --asistido, el modelo propone puntajes con evidencia; la matriz decide.
    """
    if proponer_asamblea and not guardar:
        fallar("--proponer-asamblea requiere guardar la evaluación: la propuesta cita su huella.")
    if expediente:
        vinculado = cases.obtener(expediente)
        if vinculado is None:
            fallar(f"No existe el expediente {expediente}.")
        expediente = vinculado.folio

    settings = get_settings()
    perfil = CoopProfile.load_from_yaml(settings.company_profile_path)
    hoy = hoy_local(settings.user_timezone)
    fuente = asistido or origen
    bases = ""

    if archivo is not None:
        try:
            datos: Any = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            fallar(f"{archivo.name} no es un YAML válido: {exc}")
    elif fuente:
        bases = _leer_bases(fuente)
        console.print("[dim]Pidiendo al modelo una propuesta de puntajes...[/dim]")
        try:
            respuesta, _ = ejecutar(consultar(_instrucciones_json(bases)))
            datos = extraer_json(respuesta)
            propuesta = EntradaMatriz.model_validate(datos)
        except (ValueError, ValidationError) as exc:
            fallar(f"La propuesta del modelo no es válida: {exc}", "Propuesta no válida")
        _mostrar_propuesta(propuesta)
        if not aceptar and not click.confirm("¿Evaluar con esta propuesta?", default=True):
            console.print("[dim]Evaluación cancelada.[/dim]")
            return
    else:
        datos = _entrada_interactiva()

    resultado = matrix.evaluar(datos, hoy=hoy, rango_presupuesto_definido=perfil.rango_presupuesto_definido)
    color = {"APLICAR": "green", "EXPLORAR": "cyan", "CONDICIONAL": "yellow"}.get(resultado.decision, "red")
    console.print(Panel(Markdown(resultado.to_markdown()), title=f"Decisión: {resultado.decision}",
                        border_style=color))

    if resultado.decision == "ERROR_VALIDACION":
        raise click.exceptions.Exit(1)
    if guardar:
        id_evaluacion = matrix.guardar(resultado, expediente)
        vinculo = f", vinculada a {expediente}" if expediente else ""
        console.print(f"[green]Evaluación guardada con id {id_evaluacion}{vinculo}.[/green]")
        if proponer_asamblea:
            _proponer_asamblea(perfil, resultado, id_evaluacion, expediente)
    if fuente:
        _analisis_redactado(resultado, bases)


def _proponer_asamblea(perfil: CoopProfile, resultado: ResultadoMatriz, id_evaluacion: int,
                       expediente: str | None) -> None:
    """Somete a la asamblea una postulación con decisión APLICAR; sin asamblea, remite a los aprobadores."""
    if resultado.decision != "APLICAR":
        console.print(f"[yellow]No se creó propuesta para la asamblea: la decisión es {resultado.decision} "
                      "y solo se someten las de APLICAR.[/yellow]")
        return
    if not perfil.tiene_asamblea:
        aprobadores = perfil.procuracion.aprobadores if perfil.procuracion else []
        quienes = "; ".join(aprobadores) or pendiente("aprobadores")
        console.print(f"[yellow]La organización no tiene asamblea en su perfil. "
                      f"La decisión corresponde a: {quienes}.[/yellow]")
        return
    financiador = f" ({resultado.financiador})" if resultado.financiador else ""
    descripcion = (
        f"Someter a la asamblea la postulación a «{resultado.convocatoria}»{financiador}.\n"
        f"Decisión de la matriz: APLICAR con {resultado.puntaje} de 100 puntos. "
        f"Plazo: {resultado.plazo}. Monto: {resultado.monto or MONTO_POR_DEFINIR}.\n"
        f"Expediente: {expediente or 'sin vincular'}. "
        f"Evaluación {id_evaluacion}, huella SHA-256 {resultado.hash}."
    )
    try:
        id_propuesta = create_proposal(f"Postular a {resultado.convocatoria}", descripcion, "subvencion")
    except ValueError as exc:
        fallar(str(exc), "Propuesta rechazada")
    console.print(f"[green]Propuesta {id_propuesta} abierta para la asamblea. "
                  f"Consulte: coopexecutive propuestas.[/green]")


COMANDOS = (iniciar, configurar, evaluar_convocatoria)
