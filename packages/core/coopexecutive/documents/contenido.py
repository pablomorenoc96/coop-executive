"""Contenido de un documento, independiente del formato.

Los generadores arman una lista de bloques; de ahí salen la vista previa en Markdown
(que se muestra antes de escribir) y el archivo Word. Así lo que se confirma es
exactamente lo que se guarda.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MARCADORES = re.compile(
    r"\[PENDIENTE: [^\]]+\]|MONTO POR DEFINIR|COSTO POR COTIZAR|VIGENCIA NO VERIFICADA"
)


@dataclass
class Titulo:
    texto: str
    nivel: int = 1


@dataclass
class Parrafo:
    texto: str
    # Falso para textos sin espacios que partir, como una huella SHA-256.
    justificado: bool = True


@dataclass
class Lista:
    elementos: list[str]


@dataclass
class Tabla:
    encabezados: list[str]
    filas: list[list[str]]
    # Proporción del ancho de cada columna; vacío reparte el ancho por igual.
    anchos: list[float] = field(default_factory=list)


Bloque = Titulo | Parrafo | Lista | Tabla


@dataclass
class DocumentoPlano:
    tipo: str
    titulo: str
    subtitulo: str = ""
    bloques: list[Bloque] = field(default_factory=list)

    def textos(self) -> list[str]:
        salida = [self.titulo, self.subtitulo]
        for b in self.bloques:
            if isinstance(b, (Titulo, Parrafo)):
                salida.append(b.texto)
            elif isinstance(b, Lista):
                salida.extend(b.elementos)
            else:
                salida.extend(b.encabezados)
                salida.extend(celda for fila in b.filas for celda in fila)
        return salida

    def pendientes(self) -> list[str]:
        """Marcadores de datos faltantes, sin repetir y en orden de aparición."""
        vistos: dict[str, None] = {}
        for texto in self.textos():
            for marcador in MARCADORES.findall(texto):
                vistos.setdefault(marcador, None)
        return list(vistos)


def _celda(texto: str) -> str:
    return texto.replace("|", "/").replace("\n", " ")


def a_markdown(doc: DocumentoPlano) -> str:
    lineas = [f"# {doc.titulo}"]
    if doc.subtitulo:
        lineas += ["", f"**{doc.subtitulo}**"]
    for b in doc.bloques:
        lineas.append("")
        if isinstance(b, Titulo):
            lineas.append(f"{'#' * (b.nivel + 1)} {b.texto}")
        elif isinstance(b, Parrafo):
            lineas.append(b.texto)
        elif isinstance(b, Lista):
            lineas.extend(f"- {e}" for e in b.elementos)
        else:
            lineas.append("| " + " | ".join(_celda(e) for e in b.encabezados) + " |")
            lineas.append("|" + " :--- |" * len(b.encabezados))
            lineas.extend("| " + " | ".join(_celda(c) for c in fila) + " |" for fila in b.filas)
    return "\n".join(lineas)
