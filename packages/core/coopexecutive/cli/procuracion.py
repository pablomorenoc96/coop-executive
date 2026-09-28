"""Comandos de procuración: espacio de trabajo, autoconfiguración y evaluación de oportunidades."""
from __future__ import annotations

import asyncio
import json
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
from coopexecutive.config import ARCHIVO_PERFIL, get_settings, usar_espacio
from coopexecutive.crm import cases
from coopexecutive.grant_tools import matrix
from coopexecutive.grant_tools.matrix import CRITERIOS, EntradaMatriz, ResultadoMatriz
from coopexecutive.guardrails import agregar_leyenda, revisar_respuesta
from coopexecutive.memory import onboarding
from coopexecutive.memory.company_profile import TIPOS_ORGANIZACION, CoopProfile
from coopexecutive.memory.episodic import initialize_db
from coopexecutive.utils.fechas import hoy_local

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
        f"Carpeta: {espacio.ruta}\n"
        f"Perfil ({ARCHIVO_PERFIL}): {perfil}\n"
        f"Base de datos: {settings.episodic_db_path.name}\n\n"
        f"Siguiente paso: [cyan]coopexecutive --espacio \"{espacio.ruta}\" configurar[/cyan]",
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


def _preguntar(actuales: dict[str, Any]) -> dict[str, Any]:
    respuestas: dict[str, Any] = {}
    console.print("[dim]Enter conserva el valor entre corchetes. Lo que no sepa, déjelo vacío.[/dim]")
    for pregunta in onboarding.PREGUNTAS:
        console.print(f"\n[bold cyan]{pregunta.numero}. {pregunta.texto}[/bold cyan]")
        for campo in pregunta.campos:
            respuestas[campo] = click.prompt(
                f"  {ETIQUETAS[campo]}", default=_como_texto(actuales.get(campo)), show_default=True
            )
    return respuestas


@click.command("configurar")
@click.option(
    "--desde",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Archivo YAML con las respuestas; guarda sin preguntar.",
)
def configurar(desde: Path | None) -> None:
    """Completar el perfil con diez preguntas. Respalda el perfil antes de escribir."""
    ruta = get_settings().company_profile_path
    try:
        datos = onboarding.leer_perfil_crudo(ruta)
        if desde is not None:
            respuestas = yaml.safe_load(desde.read_text(encoding="utf-8")) or {}
            if not isinstance(respuestas, dict):
                fallar(f"{desde.name} debe contener pares campo: valor.")
        else:
            respuestas = _preguntar(onboarding.respuestas_actuales(datos))
        nuevo = onboarding.aplicar_respuestas(datos, respuestas)
    except (ValueError, yaml.YAMLError) as exc:
        fallar(str(exc), "Perfil no válido")

    perfil = CoopProfile(**nuevo)
    console.print(Panel(Markdown(perfil.to_prompt_block()), title="Resumen del perfil", border_style="cyan"))
    if desde is None and not click.confirm("¿Guardar el perfil?", default=True):
        console.print("[dim]No se guardó ningún cambio.[/dim]")
        return
    respaldo = onboarding.guardar_perfil(ruta, nuevo)
    mensaje = f"[bold green]Perfil guardado[/bold green] en {ruta}"
    if respaldo is not None:
        mensaje += f"\nRespaldo del perfil anterior: {respaldo.name}"
    console.print(mensaje)


# --- evaluar-convocatoria ----------------------------------------------------------

_BLOQUE_JSON = re.compile(r"\{.*\}", re.DOTALL)


def _extraer_json(texto: str) -> dict[str, Any]:
    texto = re.sub(r"```(?:json)?", "", texto)
    encontrado = _BLOQUE_JSON.search(texto)
    if not encontrado:
        raise ValueError("El modelo no devolvió un objeto JSON.")
    datos = json.loads(encontrado.group(0))
    if not isinstance(datos, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return datos


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


async def _consultar(pregunta: str) -> tuple[str, str]:
    """Devuelve (respuesta, bloque de perfil) usando el rol de procurador."""
    from coopexecutive.orchestrator.coop_executive import CoopExecutive

    executive = CoopExecutive()
    partes = [chunk async for chunk in executive.stream_chat(pregunta, specialist_focus="procurador")]
    return "".join(partes), executive.profile.to_prompt_block()


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
    if re.match(r"^https?://", origen.strip(), re.IGNORECASE):
        fallar(
            "No se descargan páginas web en este modo. Copie el texto de las bases en un archivo "
            "y páselo como origen.",
            "Origen no admitido",
        )
    ruta = Path(origen)
    try:
        if ruta.is_file():
            return ruta.read_text(encoding="utf-8")
    except OSError:
        pass
    return origen


def _analisis_redactado(resultado: ResultadoMatriz, bases: str) -> None:
    pedido = (
        "Redacta un análisis breve (máximo 300 palabras) del resultado de la matriz que aparece abajo. "
        "No cambies la decisión, el puntaje ni el plazo; explícalos. Usa solo datos de las bases o del perfil. "
        "Termina con una sección CONTRAPUNTO y con el siguiente paso.\n\n"
        f"{resultado.to_markdown()}"
    )
    try:
        texto, perfil = asyncio.run(_consultar(pedido))
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
def evaluar_convocatoria(
    origen: str | None,
    archivo: Path | None,
    asistido: str | None,
    expediente: str | None,
    guardar: bool,
    aceptar: bool,
) -> None:
    """Evaluar una oportunidad con la matriz de 100 puntos.

    Sin argumentos pregunta cada dato. Con --archivo lee un YAML. Con un ORIGEN o
    --asistido, el modelo propone puntajes con evidencia; la matriz decide.
    """
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
            respuesta, _ = asyncio.run(_consultar(_instrucciones_json(bases)))
            datos = _extraer_json(respuesta)
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
    if fuente:
        _analisis_redactado(resultado, bases)


COMANDOS = (iniciar, configurar, evaluar_convocatoria)
