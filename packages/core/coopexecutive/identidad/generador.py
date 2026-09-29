"""Genera la intro de la terminal a partir del logo y la fuente de la organización.

El logo (PNG) y el nombre, dibujado con la fuente propia (TTF u OTF), se convierten en
bloques de cuadrante: cada carácter representa 2 x 2 píxeles. El resultado es texto con
marcado de rich que se guarda en ``intro.txt`` y se muestra sin necesitar Pillow.
Requiere el extra ``identidad`` (Pillow) solo para generar.
"""
from __future__ import annotations

from pathlib import Path

# Bits en orden: arriba-izquierda, arriba-derecha, abajo-izquierda, abajo-derecha.
CUADRANTES = " ▗▖▄▝▐▞▟▘▚▌▙▀▜▛█"

UMBRAL_LOGO = 0.4
# El texto usa un umbral mayor para que no se cierren los huecos de letras como «e» o «a».
UMBRAL_TEXTO = 0.5
SEPARACION = 3


def _pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - depende de la instalación
        raise RuntimeError(
            "Generar la intro requiere Pillow: instale el extra con "
            "«uv sync --extra identidad» o «pip install coopexecutive[identidad]»."
        ) from exc
    return Image, ImageDraw, ImageFont


def _a_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _color_visible(rgb: tuple[int, int, int]) -> str:
    """Devuelve el color del logo, o vacío si es casi negro o casi blanco.

    Un logo negro desaparece en una terminal oscura y uno blanco en una clara; vacío
    significa usar el color de texto de la terminal.
    """
    luminancia = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    if luminancia < 40 or luminancia > 225:
        return ""
    return _a_hex(rgb)


def mascara_logo(ruta: Path):
    """Máscara en escala de grises (255 = logo) y color medio del trazo."""
    from PIL import ImageChops, ImageStat

    Image, _, _ = _pillow()
    imagen = Image.open(ruta).convert("RGBA")
    rgb = imagen.convert("RGB")
    mascara = imagen.getchannel("A")
    fondo = imagen.getpixel((0, 0))
    if fondo[3] > 0:
        # Fondo opaco: el trazo es lo que se aleja del color de la esquina.
        diferencia = ImageChops.difference(rgb, Image.new("RGB", imagen.size, fondo[:3]))
        r, g, b = diferencia.split()
        distancia = ImageChops.add(ImageChops.add(r, g), b)
        mascara = ImageChops.multiply(mascara, distancia.point(lambda v: 255 if v > 90 else 0))
    caja = mascara.getbbox()
    if caja is None:
        raise ValueError(f"No se encontró un trazo en {ruta.name}.")
    trazo = mascara.point(lambda v: 255 if v > 127 else 0)
    color = tuple(int(v) for v in ImageStat.Stat(rgb, mask=trazo).mean)
    return mascara.crop(caja), color


def mascara_texto(texto: str, fuente: Path | None):
    """Dibuja el texto con la fuente indicada (o la de Pillow) y lo recorta.

    Un salto de línea en el texto lo reparte en varias líneas alineadas a la izquierda.
    """
    Image, ImageDraw, ImageFont = _pillow()
    tamano = 200
    letra = ImageFont.truetype(str(fuente), tamano) if fuente else ImageFont.load_default(tamano)
    medidor = ImageDraw.Draw(Image.new("L", (1, 1)))
    espacio = tamano // 5
    izquierda, arriba, derecha, abajo = medidor.multiline_textbbox((0, 0), texto, font=letra, spacing=espacio)
    lienzo = Image.new("L", (derecha - izquierda + 20, abajo - arriba + 20), 0)
    ImageDraw.Draw(lienzo).multiline_text(
        (10 - izquierda, 10 - arriba), texto, font=letra, fill=255, spacing=espacio
    )
    return lienzo.crop(lienzo.getbbox())


def a_cuadrantes(mascara, filas: int, umbral: float = UMBRAL_LOGO) -> list[str]:
    """Convierte la máscara en ``filas`` líneas de bloques, conservando la proporción.

    Un carácter mide aproximadamente el doble de alto que de ancho, así que cada píxel
    de cuadrante es el doble de alto que de ancho: la imagen se estira al doble en
    horizontal antes de muestrear.
    """
    Image, _, _ = _pillow()
    proporcion = mascara.width / mascara.height
    columnas = max(1, round(filas * 2 * proporcion))
    reducida = mascara.resize((columnas * 2, filas * 2), Image.Resampling.BOX)
    limite = 255 * umbral
    lineas = []
    for fila in range(filas):
        caracteres = []
        for col in range(columnas):
            bits = 0
            for peso, (dx, dy) in zip((8, 4, 2, 1), ((0, 0), (1, 0), (0, 1), (1, 1)), strict=True):
                if reducida.getpixel((col * 2 + dx, fila * 2 + dy)) > limite:
                    bits |= peso
            caracteres.append(CUADRANTES[bits])
        lineas.append("".join(caracteres))
    return lineas


def _pintar(linea: str, color: str, negrita: bool = False) -> str:
    estilo = " ".join(filter(None, ["bold" if negrita else "", color]))
    contenido = linea.rstrip()
    if not contenido.strip() or not estilo:
        return contenido
    return f"[{estilo}]{contenido}[/]"


def generar_intro(
    texto: str,
    logo: Path | None = None,
    fuente: Path | None = None,
    lema: str = "",
    color_logo: str = "",
    color_texto: str = "",
    filas_logo: int = 8,
    filas_texto: int = 5,
    ancho_max: int = 78,
) -> str:
    """Devuelve la intro como marcado de rich: logo a la izquierda, nombre y lema a la derecha.

    ``filas_texto`` es la altura de cada línea del nombre en la terminal; si el conjunto
    no cabe en ``ancho_max`` columnas, se reduce hasta un mínimo de 2.
    """
    bloque_logo: list[str] = []
    if logo is not None:
        mascara, color_medio = mascara_logo(logo)
        bloque_logo = a_cuadrantes(mascara, filas_logo)
        color_logo = color_logo or _color_visible(color_medio)
    ancho_logo = max((len(linea) for linea in bloque_logo), default=0)
    margen = ancho_logo + SEPARACION if bloque_logo else 0

    mascara_nombre = mascara_texto(texto, fuente)
    # filas_texto es la altura de cada línea del nombre; se reduce si no cabe en ancho_max.
    lineas_nombre = len(texto.splitlines()) or 1
    filas = filas_texto
    bloque_texto = a_cuadrantes(mascara_nombre, filas * lineas_nombre, UMBRAL_TEXTO)
    while filas > 2 and margen + len(bloque_texto[0]) > ancho_max:
        filas -= 1
        bloque_texto = a_cuadrantes(mascara_nombre, filas * lineas_nombre, UMBRAL_TEXTO)
    ancho_texto = len(bloque_texto[0])

    derecha = [_pintar(linea, color_texto, negrita=True) for linea in bloque_texto]
    if lema:
        lema_linea = lema if len(lema) <= ancho_texto else lema[: max(ancho_texto - 1, 1)] + "…"
        derecha += ["", _pintar(lema_linea, color_logo)]

    alto = max(len(bloque_logo), len(derecha))
    inicio_logo = (alto - len(bloque_logo)) // 2
    inicio_texto = (alto - len(derecha)) // 2
    lineas = []
    for i in range(alto):
        izquierda = ""
        if bloque_logo:
            parte = bloque_logo[i - inicio_logo] if 0 <= i - inicio_logo < len(bloque_logo) else ""
            parte = parte.rstrip()
            izquierda = _pintar(parte, color_logo) + " " * (margen - len(parte))
        parte_derecha = derecha[i - inicio_texto] if 0 <= i - inicio_texto < len(derecha) else ""
        lineas.append((izquierda + parte_derecha).rstrip())
    return "\n".join(lineas) + "\n"
