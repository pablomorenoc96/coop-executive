"""Dibuja assets/architecture.png (inglés) y assets/architecture_es.png con Pillow.

Uso, desde la raíz del repositorio:

    uv run --project packages/core --all-extras python scripts/diagrama.py
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
ANCHO, ALTO = 1600, 1040
FONDO, TINTA, SUAVE, LINEA = (250, 250, 247), (28, 33, 40), (88, 96, 105), (170, 176, 184)
VERDE, AZUL, AMBAR, MORADO, GRIS = (46, 125, 80), (37, 99, 170), (176, 112, 20), (112, 72, 168), (96, 104, 112)

TEXTOS = {
    "es": {
        "titulo": "CoopExecutive 0.5: arquitectura",
        "sub": "Todo corre en su equipo. Lo que decide la matriz, los plazos y la asamblea se calcula en código; el modelo redacta y usa herramientas.",
        "canales": "Canales",
        "cli": ("Terminal (CLI)", "chat, ask y más de 25 comandos"),
        "panel": ("Panel local", "127.0.0.1, token por sesión"),
        "api": ("API local", "JSON y chat en streaming"),
        "mcp": ("Servidor MCP", "stdio, clientes MCP"),
        "agente": ("Agente con herramientas", "Toda escritura pide confirmación; lo negado se informa al modelo"),
        "registro": ("Registro de herramientas", "14 de consulta · 5 de escritura · mismo catálogo en CLI, MCP y API"),
        "roles": ("Roles", "procurador · vigilancia · legal · finanzas · técnico · comunicación · asamblea"),
        "modelos": ("Modelos", "OpenRouter gratis · Ollama local · OpenAI, Anthropic, Gemini, Groq, Mistral, DeepSeek"),
        "determinista": "Cálculo determinista",
        "det": [("Matriz de 100 puntos", "evidencia por criterio, huella SHA-256"),
                ("Plazos y comparación", "días a hoy, qué atender primero"),
                ("Asamblea", "padrón, cuórum, un socio un voto"),
                ("Proyecto", "marco lógico y presupuesto sin inventar")],
        "revision": ("Revisión posterior", "montos, fechas y acciones sin respaldo → MONTO POR DEFINIR, [PENDIENTE]; cuentas censuradas"),
        "datos": "Datos locales (un espacio por organización)",
        "dat": [("Perfil YAML", "con el origen de cada dato"),
                ("SQLite", "financiadores, expedientes, evaluaciones, documentos, monitoreo, asamblea"),
                ("Bitácora encadenada", "canal, acción, resultado, SHA-256"),
                ("Salidas Word", "membrete propio, sin sobrescribir")],
        "fuera": "Lo único que sale a la red",
        "fue": ["Consultas al modelo que usted elija", "Sitio web propio (configurar --sitio)",
                "Fuentes RSS de convocatorias", "Bases en URL o PDF"],
    },
    "en": {
        "titulo": "CoopExecutive 0.5: architecture",
        "sub": "Everything runs on your machine. Matrix decisions, deadlines and assembly results are computed in code; the model drafts and calls tools.",
        "canales": "Channels",
        "cli": ("Terminal (CLI)", "chat, ask and 25+ commands"),
        "panel": ("Local panel", "127.0.0.1, per-session token"),
        "api": ("Local API", "JSON and streaming chat"),
        "mcp": ("MCP server", "stdio, any MCP client"),
        "agente": ("Tool-calling agent", "Every write asks for confirmation; a denial is reported to the model"),
        "registro": ("Tool registry", "14 read · 5 write · same catalogue in CLI, MCP and API"),
        "roles": ("Roles", "procurement · oversight · legal · finance · technical · communication · assembly"),
        "modelos": ("Models", "OpenRouter free · local Ollama · OpenAI, Anthropic, Gemini, Groq, Mistral, DeepSeek"),
        "determinista": "Deterministic computation",
        "det": [("100-point matrix", "evidence per criterion, SHA-256 hash"),
                ("Deadlines and comparison", "days to today, what comes first"),
                ("Assembly", "member roll, quorum, one member one vote"),
                ("Project design", "logframe and budget, nothing invented")],
        "revision": ("Post-generation review", "unsupported amounts, dates and actions → MONTO POR DEFINIR, [PENDIENTE]; accounts censored"),
        "datos": "Local data (one workspace per organisation)",
        "dat": [("YAML profile", "with the source of each field"),
                ("SQLite", "funders, cases, evaluations, documents, monitoring, assembly"),
                ("Chained audit log", "channel, action, result, SHA-256"),
                ("Word outputs", "own letterhead, never overwritten")],
        "fuera": "The only network traffic",
        "fue": ["Calls to the model you choose", "Your own website (configurar --sitio)",
                "RSS feeds of funding calls", "Call documents by URL or PDF"],
    },
}


def fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    for carpeta in (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path("/usr/share/fonts/truetype/dejavu")):
        if (carpeta / nombre).is_file():
            return ImageFont.truetype(str(carpeta / nombre), tam)
    return ImageFont.truetype(nombre, tam)


F = {"titulo": fuente(34, True), "sub": fuente(17), "seccion": fuente(15, True), "caja": fuente(19, True),
     "detalle": fuente(15)}


def envolver(texto: str, f: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if f.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return [*lineas, actual]


def caja(d: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color, titulo: str, detalle: str = "") -> None:
    d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=(255, 255, 255), outline=color, width=2)
    d.rounded_rectangle([x, y, x + 8, y + h], radius=4, fill=color)
    d.text((x + 22, y + 14), titulo, font=F["caja"], fill=TINTA)
    for i, linea in enumerate(envolver(detalle, F["detalle"], w - 40)):
        d.text((x + 22, y + 44 + i * 21), linea, font=F["detalle"], fill=SUAVE)


def seccion(d: ImageDraw.ImageDraw, x: int, y: int, texto: str, color) -> None:
    d.text((x, y), texto.upper(), font=F["seccion"], fill=color)


def flecha(d: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color=LINEA, doble: bool = False) -> None:
    d.line([x1, y1, x2, y2], fill=color, width=3)
    for (ax, ay), (bx, by) in [((x1, y1), (x2, y2))] + ([((x2, y2), (x1, y1))] if doble else []):
        if ax == bx:
            s = 1 if by > ay else -1
            d.polygon([(bx, by), (bx - 7, by - 12 * s), (bx + 7, by - 12 * s)], fill=color)
        else:
            s = 1 if bx > ax else -1
            d.polygon([(bx, by), (bx - 12 * s, by - 7), (bx - 12 * s, by + 7)], fill=color)


def dibujar(idioma: str) -> Image.Image:
    t = TEXTOS[idioma]
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    d.text((60, 40), t["titulo"], font=F["titulo"], fill=TINTA)
    d.text((60, 90), t["sub"], font=F["sub"], fill=SUAVE)

    # Canales
    seccion(d, 60, 140, t["canales"], AZUL)
    for i, clave in enumerate(("cli", "panel", "api", "mcp")):
        caja(d, 60 + i * 285, 166, 265, 92, AZUL, *t[clave])
    flecha(d, 590, 258, 590, 300, AZUL, doble=True)

    # Núcleo
    caja(d, 60, 300, 1100, 92, VERDE, *t["agente"])
    caja(d, 60, 412, 540, 110, VERDE, *t["registro"])
    caja(d, 620, 412, 540, 110, GRIS, *t["roles"])
    flecha(d, 330, 392, 330, 412, VERDE)

    # Determinista
    seccion(d, 60, 548, t["determinista"], AMBAR)
    for i, (titulo, detalle) in enumerate(t["det"]):
        caja(d, 60 + i * 280, 574, 260, 104, AMBAR, titulo, detalle)
    flecha(d, 330, 522, 330, 574, AMBAR)
    caja(d, 60, 698, 1100, 80, MORADO, *t["revision"])

    # Datos
    seccion(d, 60, 806, t["datos"], GRIS)
    for i, (titulo, detalle) in enumerate(t["dat"]):
        caja(d, 60 + i * 280, 832, 260, 124, GRIS, titulo, detalle)
    flecha(d, 610, 778, 610, 832, GRIS, doble=True)

    # Modelos y red, a la derecha
    caja(d, 1200, 166, 340, 226, VERDE, *t["modelos"])
    flecha(d, 1160, 346, 1200, 346, VERDE, doble=True)
    seccion(d, 1200, 420, t["fuera"], TINTA)
    d.rounded_rectangle([1200, 446, 1540, 956], radius=12, fill=(255, 255, 255), outline=LINEA, width=2)
    for i, linea in enumerate(t["fue"]):
        y = 470 + i * 110
        d.ellipse([1222, y + 6, 1234, y + 18], fill=AZUL)
        for j, parte in enumerate(envolver(linea, F["caja"], 270)):
            d.text((1248, y + j * 26), parte, font=F["caja"], fill=TINTA)
    return img


def main() -> None:
    for idioma, nombre in (("en", "architecture.png"), ("es", "architecture_es.png")):
        destino = RAIZ / "assets" / nombre
        dibujar(idioma).save(destino, optimize=True)
        print(f"{destino.relative_to(RAIZ)}: {destino.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
