"""Autoconfiguración del perfil: diez preguntas, espacio de trabajo y respaldo previo.

La lógica vive aquí, sin consola, para que la CLI y otros canales la compartan.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from coopexecutive.config import ARCHIVO_PERFIL
from coopexecutive.guardrails.sensibles import IDENTIFICADOR, contiene_dato_bancario
from coopexecutive.memory.company_profile import CoopProfile, TipoOrganizacion, inferir_tipo


@dataclass(frozen=True)
class Pregunta:
    numero: int
    texto: str
    campos: tuple[str, ...]


# Cada respuesta se guarda en uno o más campos; las listas se separan con «;».
PREGUNTAS: tuple[Pregunta, ...] = (
    Pregunta(1, "¿Cómo se llama la organización y qué siglas o nombre corto usa?", ("nombre", "siglas")),
    Pregunta(
        2,
        "¿Cuál es su figura jurídica? Por ejemplo: asociación civil, cooperativa, "
        "persona física con actividad empresarial o S.A.S. en trámite.",
        ("figura",),
    ),
    Pregunta(3, "¿Cuál es su misión, en una o dos frases?", ("mision",)),
    Pregunta(4, "¿A qué población atiende y en qué territorio trabaja?", ("poblacion", "territorio")),
    Pregunta(5, "¿Qué programas y ejes de trabajo tiene?", ("programas", "ejes")),
    Pregunta(
        6,
        "¿Qué resultados puede demostrar con cifras verificables? Déjelo vacío si aún no los tiene.",
        ("metricas",),
    ),
    Pregunta(
        7,
        "¿Cuál es su estatus legal y fiscal? No escriba RFC, CURP ni otros identificadores.",
        ("estatus_legal", "estatus_fiscal"),
    ),
    Pregunta(
        8,
        "¿Qué rango de montos puede solicitar o ejecutar? Mínimo, máximo y moneda; vacío si está por definir.",
        ("rango_minimo", "rango_maximo", "moneda"),
    ),
    Pregunta(9, "¿Con qué alianzas y financiadores ha trabajado?", ("alianzas", "financiadores")),
    Pregunta(
        10,
        "¿Quién aprueba las solicitudes y qué tipo de mecanismo usa para recibir donativos o pagos? "
        "Por ejemplo: transferencia, plataforma en línea o recibo deducible. No escriba números de cuenta.",
        ("aprobadores", "mecanismos_cobro"),
    ),
)

CAMPOS_LISTA = {
    "poblacion", "programas", "ejes", "metricas", "alianzas", "financiadores",
    "aprobadores", "mecanismos_cobro",
}
CAMPOS_MONTO = {"rango_minimo", "rango_maximo"}

FIGURA_POR_TIPO: dict[str, str] = {
    "cooperativa": "Sociedad Cooperativa",
    "asociacion_civil": "Asociación Civil",
    "empresa": "Sociedad mercantil",
    "persona_fisica": "Persona física con actividad empresarial",
}

def _lista(valor: Any) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, (list, tuple)):
        return [str(v).strip() for v in valor if str(v).strip()]
    return [parte.strip() for parte in str(valor).split(";") if parte.strip()]


def _monto(valor: Any, campo: str) -> float | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        return float(str(valor).replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(f"{campo}: «{valor}» no es un monto.") from exc


def _revisar_identificadores(respuestas: dict[str, Any]) -> None:
    for campo, valor in respuestas.items():
        textos = valor if isinstance(valor, list) else [valor]
        for texto in textos:
            if not isinstance(texto, str):
                continue
            if IDENTIFICADOR.search(texto):
                raise ValueError(
                    f"{campo}: parece contener un RFC o una CURP. El perfil no guarda identificadores fiscales."
                )
            if contiene_dato_bancario(texto):
                raise ValueError(
                    f"{campo}: parece contener una cuenta bancaria o una tarjeta. "
                    "Indique solo el tipo de mecanismo, sin números."
                )


def leer_perfil_crudo(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def respuestas_actuales(datos: dict[str, Any]) -> dict[str, Any]:
    """Respuestas que corresponden a un perfil existente (valores por omisión del cuestionario)."""
    proc = datos.get("procuracion") or {}
    rango = proc.get("rango_presupuesto") or {}
    return {
        "nombre": datos.get("name", ""),
        "siglas": proc.get("siglas", ""),
        "figura": datos.get("legal_structure", ""),
        "mision": (datos.get("mission") or "").strip(),
        "poblacion": datos.get("target_communities", []),
        "territorio": proc.get("territorio", ""),
        "programas": proc.get("programas", []),
        "ejes": datos.get("focus_areas", []),
        "metricas": proc.get("metricas_impacto", []),
        "estatus_legal": proc.get("estatus_legal", ""),
        "estatus_fiscal": proc.get("estatus_fiscal", ""),
        "rango_minimo": rango.get("minimo"),
        "rango_maximo": rango.get("maximo"),
        "moneda": rango.get("moneda") or proc.get("moneda_base", "MXN"),
        "alianzas": proc.get("alianzas", []),
        "financiadores": proc.get("financiadores_historicos", []),
        "aprobadores": proc.get("aprobadores", []),
        "mecanismos_cobro": proc.get("mecanismos_cobro", []),
    }


def aplicar_respuestas(
    datos: dict[str, Any], respuestas: dict[str, Any], origenes: dict[str, str] | None = None
) -> dict[str, Any]:
    """Combina las respuestas con el perfil existente. Un campo ausente conserva su valor.

    `origenes` registra de dónde salió cada campo (por ejemplo, la URL de la página
    del sitio web); se guarda en `procuracion.origenes`.
    """
    desconocidos = set(respuestas) - {c for p in PREGUNTAS for c in p.campos} - {"tipo"}
    if desconocidos:
        raise ValueError(f"Campos desconocidos en las respuestas: {', '.join(sorted(desconocidos))}.")
    r = {k: (_lista(v) if k in CAMPOS_LISTA else v) for k, v in respuestas.items()}
    _revisar_identificadores(r)

    nuevo = dict(datos)
    proc = dict(nuevo.get("procuracion") or {})

    def poner(destino: dict[str, Any], clave: str, campo: str) -> None:
        if campo in r:
            valor = r[campo]
            destino[clave] = valor.strip() if isinstance(valor, str) else valor

    poner(nuevo, "name", "nombre")
    poner(nuevo, "legal_structure", "figura")
    poner(nuevo, "mission", "mision")
    poner(nuevo, "target_communities", "poblacion")
    poner(nuevo, "focus_areas", "ejes")
    for clave, campo in (
        ("siglas", "siglas"),
        ("territorio", "territorio"),
        ("programas", "programas"),
        ("metricas_impacto", "metricas"),
        ("estatus_legal", "estatus_legal"),
        ("estatus_fiscal", "estatus_fiscal"),
        ("alianzas", "alianzas"),
        ("financiadores_historicos", "financiadores"),
        ("aprobadores", "aprobadores"),
        ("mecanismos_cobro", "mecanismos_cobro"),
    ):
        poner(proc, clave, campo)

    if CAMPOS_MONTO & r.keys() or "moneda" in r:
        rango = dict(proc.get("rango_presupuesto") or {})
        if "rango_minimo" in r:
            rango["minimo"] = _monto(r["rango_minimo"], "Mínimo")
        if "rango_maximo" in r:
            rango["maximo"] = _monto(r["rango_maximo"], "Máximo")
        if "moneda" in r and str(r["moneda"] or "").strip():
            rango["moneda"] = str(r["moneda"]).strip().upper()
            proc["moneda_base"] = rango["moneda"]
        proc["rango_presupuesto"] = rango

    if origenes:
        proc["origenes"] = {**(proc.get("origenes") or {}), **origenes}

    if "tipo" in r and r["tipo"]:
        nuevo["tipo_organizacion"] = r["tipo"]
    elif "figura" in r:
        nuevo["tipo_organizacion"] = inferir_tipo(str(r["figura"]))
    nuevo["procuracion"] = proc

    CoopProfile(**nuevo)  # valida antes de escribir
    return nuevo


def respaldar(ruta: Path, ahora: datetime | None = None) -> Path | None:
    """Copia el perfil a `profile.yaml.bak-AAAAMMDD-HHMMSS` sin sobrescribir respaldos previos."""
    if not ruta.exists():
        return None
    if ahora is None:
        from coopexecutive.utils.fechas import ahora_local

        ahora = ahora_local()
    base = ruta.with_name(f"{ruta.name}.bak-{ahora.strftime('%Y%m%d-%H%M%S')}")
    destino, n = base, 1
    while destino.exists():
        destino = base.with_name(f"{base.name}-{n}")
        n += 1
    shutil.copy2(ruta, destino)
    return destino


def guardar_perfil(ruta: Path, datos: dict[str, Any], ahora: datetime | None = None) -> Path | None:
    """Valida, respalda el perfil anterior y escribe el nuevo. Devuelve la ruta del respaldo."""
    CoopProfile(**datos)
    respaldo = respaldar(ruta, ahora)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        yaml.safe_dump(datos, f, allow_unicode=True, sort_keys=False, width=100)
    return respaldo


def perfil_inicial(nombre: str, tipo: TipoOrganizacion) -> dict[str, Any]:
    """Perfil mínimo para un espacio nuevo; lo demás se completa con `configurar`."""
    return {
        "name": nombre.strip(),
        "tipo_organizacion": tipo,
        "legal_structure": FIGURA_POR_TIPO[tipo],
        "mission": "",
        "procuracion": {"moneda_base": "MXN"},
    }


@dataclass
class EspacioCreado:
    ruta: Path
    perfil_creado: bool


def crear_espacio(ruta: Path, nombre: str, tipo: TipoOrganizacion) -> EspacioCreado:
    """Crea la carpeta, `salidas/` y un perfil mínimo si no existe. No sobrescribe nada."""
    ruta = ruta.expanduser().resolve()
    (ruta / "salidas").mkdir(parents=True, exist_ok=True)
    perfil = ruta / ARCHIVO_PERFIL
    creado = False
    if not perfil.exists():
        guardar_perfil(perfil, perfil_inicial(nombre, tipo))
        creado = True
    return EspacioCreado(ruta=ruta, perfil_creado=creado)
