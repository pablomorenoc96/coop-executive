"""`python -m coopexecutive.evals`: corre los casos dorados e imprime el resumen."""
from __future__ import annotations

import sys
from collections import Counter

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from coopexecutive.evals import correr_todos


def main() -> int:
    consola = Console(legacy_windows=False)
    resultados = correr_todos()
    tabla = Table(title="Evaluaciones de comportamiento", header_style="bold cyan")
    tabla.add_column("Familia")
    tabla.add_column("Caso")
    tabla.add_column("Resultado")
    for r in resultados:
        estado = "[green]ok[/green]" if r.ok else f"[red]falla[/red] {escape(r.detalle)}"
        tabla.add_row(r.caso.familia, escape(r.caso.nombre), estado)
    consola.print(tabla)
    por_familia = Counter(r.caso.familia for r in resultados)
    fallas = [r for r in resultados if not r.ok]
    resumen = ", ".join(f"{familia}: {n}" for familia, n in por_familia.items())
    consola.print(f"{len(resultados) - len(fallas)} de {len(resultados)} casos correctos ({resumen}).",
                  highlight=False)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
