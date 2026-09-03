"""Línea de comandos de CoopExecutive."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from coopexecutive.config import get_settings
from coopexecutive.memory.company_profile import CoopProfile
from coopexecutive.orchestrator.coop_executive import CoopExecutive
from coopexecutive.grant_tools.eligibility_evaluator import evaluate_grant_opportunity

console = Console(legacy_windows=False)


@click.group()
def cli() -> None:
    """CoopExecutive — Sistema Directivo y Procurador de Fondos para la Economía Social."""
    pass


@cli.command()
@click.argument("pregunta")
@click.option("--rol", default=None, help="Especialista a enfocar: procurador, vigilancia, legal, finanzas, tecnico, asamblea")
def ask(pregunta: str, rol: str | None) -> None:
    """Hacer una consulta directa al Director Colegiado."""
    asyncio.run(_ask(pregunta, rol))


async def _ask(pregunta: str, rol: str | None) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold green]🏛️ CoopExecutive ({executive.profile.name})[/bold green]\n")
    async for chunk in executive.stream_chat(pregunta, specialist_focus=rol):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command()
def chat() -> None:
    """Iniciar sesión interactiva con el Director Colegiado de la cooperativa."""
    asyncio.run(_chat())


async def _chat() -> None:
    executive = CoopExecutive()
    settings = get_settings()
    console.print(Panel.fit(
        f"[bold cyan]CoopExecutive — Dirección Colegiada y Economía Social[/bold cyan]\n"
        f"Organización: [bold green]{executive.profile.name}[/bold green]\n"
        f"Régimen: {executive.profile.legal_structure}\n"
        f"Modelo IA: [bold yellow]{settings.default_model}[/bold yellow] (Escribe 'salir' para terminar)",
        border_style="green",
    ))

    history: list[dict[str, str]] = []

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]Asamblea / Tú[/bold yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Sesión finalizada. En favor del bien común.[/dim]")
            break

        if user_input.lower() in ("salir", "exit", "quit", "q"):
            console.print("[dim]Sesión finalizada.[/dim]")
            break

        if not user_input.strip():
            continue

        console.print("\n[bold green]🏛️ CoopExecutive[/bold green]\n")
        response_text = ""
        async for chunk in executive.stream_chat(user_input, history=history):
            response_text += chunk
            console.print(chunk, end="", highlight=False)
        console.print("\n")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response_text})


@cli.command("evaluar-convocatoria")
@click.argument("origen", type=str)
def evaluar_convocatoria(origen: str) -> None:
    """Evaluar una convocatoria (texto, URL o archivo) con la Matriz de 100 Puntos."""
    asyncio.run(_evaluar_convocatoria(origen))


async def _evaluar_convocatoria(origen: str) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold cyan]📋 Agente Procurador de Fondos — Evaluando Convocatoria[/bold cyan]\n")
    
    contenido = origen
    path_candidate = Path(origen)
    if path_candidate.exists() and path_candidate.is_file():
        contenido = path_candidate.read_text(encoding="utf-8")
        console.print(f"Archivo cargado: [dim]{path_candidate.name}[/dim]")

    prompt = (
        f"Actúa como el Agente Procurador de Fondos de {executive.profile.name}. "
        f"Evalúa la siguiente convocatoria aplicando con rigor la Matriz de Evaluación de 100 Puntos (las 8 dimensiones):\n\n"
        f"{contenido}\n\n"
        f"Genera el Dictamen Ejecutivo con:\n"
        f"1. Datos clave (Donante, Monto, Fecha límite, Elegibilidad).\n"
        f"2. Tabla de puntuación desglosada (0-100 pts) con justificación técnica.\n"
        f"3. Dictamen claro: APLICAR / EXPLORAR / CONDICIONAL / NO APLICAR.\n"
        f"4. Fortalezas de nuestra organización y Riesgos/Brechas identificadas.\n"
        f"5. Ruta de acción recomendada paso a paso."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("marco-logico")
@click.argument("proyecto", type=str)
def marco_logico(proyecto: str) -> None:
    """Generar la Matriz de Marco Lógico 4x4 y Teoría del Cambio para un proyecto."""
    asyncio.run(_marco_logico(proyecto))


async def _marco_logico(proyecto: str) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold cyan]📐 Generando Matriz de Marco Lógico (MML) para: {proyecto}[/bold cyan]\n")
    
    prompt = (
        f"Para la organización {executive.profile.name}, genera una propuesta técnica con Metodología de Marco Lógico "
        f"para el proyecto: '{proyecto}'.\n"
        f"Incluye:\n"
        f"1. Planteamiento del problema y Árbol de Objetivos.\n"
        f"2. Teoría del Cambio (Theory of Change) vinculada a los ODS (ODS 7, 8, 9 o 12).\n"
        f"3. Matriz 4x4 de Marco Lógico (Fin, Propósito, Componentes y Actividades) con Indicadores, Medios de Verificación y Supuestos."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("presupuesto")
@click.argument("proyecto", type=str)
def presupuesto(proyecto: str) -> None:
    """Generar un presupuesto auditable y desglose de costos para un proyecto."""
    asyncio.run(_presupuesto(proyecto))


async def _presupuesto(proyecto: str) -> None:
    executive = CoopExecutive()
    console.print(f"\n[bold cyan]💰 Estructurando Presupuesto Auditable para: {proyecto}[/bold cyan]\n")
    
    prompt = (
        f"Actúa como el Agente Procurador de Fondos de {executive.profile.name}. "
        f"Estructura un presupuesto detallado y auditable para el proyecto: '{proyecto}'.\n"
        f"Incluye:\n"
        f"1. Tabla de costos desglosada por rubros estándar de cooperación internacional: "
        f"Personal Técnico, Equipamiento/CAPEX, Gastos Operativos/OPEX, Auditoría Externa y Costos Indirectos (máx 7-10%).\n"
        f"2. Distinción clara entre Fondos Solicitados al Donante y Contrapartida Institucional (en especie o valorizada).\n"
        f"3. Resumen financiero total y notas de justificación presupuestal."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("dossier")
@click.argument("proyecto")
@click.option("--donante", default="Banco Interamericano de Desarrollo / Agencias Multilaterales", help="Agencia donante o cooperante")
@click.option("--convocatoria", default="Fondo de Transición Sostenible y Economía Social", help="Título de la convocatoria")
def dossier(proyecto: str, donante: str, convocatoria: str) -> None:
    """Generar un dossier formal de postulación técnica y financiera."""
    asyncio.run(_dossier(proyecto, donante, convocatoria))


async def _dossier(proyecto: str, donante: str, convocatoria: str) -> None:
    executive = CoopExecutive()
    console.print(f"[bold cyan]📁 Generando Dossier Multilateral de Postulación:[/bold cyan] {proyecto}")
    console.print(f"[dim]Donante: {donante} | Convocatoria: {convocatoria}[/dim]\n")

    prompt = (
        f"Actúa como el Agente Procurador de Fondos Colegiado de {executive.profile.name}.\n"
        f"Redacta un Dossier Formal Completo de Postulación para el proyecto '{proyecto}', dirigido a '{donante}' "
        f"bajo la convocatoria '{convocatoria}'.\n"
        f"Estructura el documento con el máximo rigor técnico conforme a los estándares de Research Grants y RBM:\n"
        f"1. Resumen Ejecutivo y Perfil del Proponente (subrayando el modelo cooperativo y asambleario).\n"
        f"2. Diagnóstico del Problema Central y Línea Base.\n"
        f"3. Matriz de Marco Lógico 4x4 (Fin, Propósito, Componentes, Actividades) con ODS vinculados.\n"
        f"4. Plan Presupuestal Consolidado (Fondos Solicitados vs. Contrapartida en Especie).\n"
        f"5. Salvaguardas Cooperativas y Anticorrupción (Fondo de Reserva 15%, Previsión 10%, Educación 10%).\n"
        f"6. Estrategia de Sostenibilidad y Salida Post-Donante."
    )

    async for chunk in executive.stream_chat(prompt, specialist_focus="procurador"):
        console.print(chunk, end="", highlight=False)
    console.print("\n")


@cli.command("dashboard")
def dashboard() -> None:
    """Abrir el Panel de Control Web y Gobernanza Colegiada en el navegador."""
    import webbrowser
    from pathlib import Path
    web_file = Path(__file__).resolve().parent.parent / "web" / "dashboard.html"
    console.print(f"[bold cyan]🌐 Abriendo Panel de Control Web:[/bold cyan] {web_file}")
    webbrowser.open(web_file.as_uri())


@cli.command("info")
def info() -> None:
    """Mostrar la información y estatus de la organización activa."""
    executive = CoopExecutive()
    console.print(Panel(
        Markdown(executive.profile.to_prompt_block()),
        title=f"🏛️ Organización Activa: {executive.profile.name}",
        border_style="cyan"
    ))


if __name__ == "__main__":
    cli()
