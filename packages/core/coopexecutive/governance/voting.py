"""Padrón de socios, votación y escrutinio de asamblea.

Principios:
- Un socio, un voto (sin ponderación por capital ni aportaciones).
- Cuórum: votan más de la mitad del padrón activo.
- Mayoría según el perfil (`governance.mayoria`): simple o de dos tercios de los votos válidos.
- Veto a propuestas que diluyan capital o liquiden fondos irrepartibles.
- El escrutinio cierra la propuesta, guarda el resultado con su huella SHA-256 completa
  y registra el acuerdo; repetirlo devuelve la misma acta.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from coopexecutive.memory.episodic import get_db_conn, initialize_db
from coopexecutive.utils.fechas import ahora_local

Mayoria = Literal["simple", "dos_tercios"]

REGLAS: dict[str, str] = {
    "simple": "mayoría simple de los votos válidos (más votos a favor que en contra)",
    "dos_tercios": "mayoría de dos tercios de los votos válidos",
}


class VoteChoice(str, Enum):
    A_FAVOR = "A_FAVOR"
    EN_CONTRA = "EN_CONTRA"
    ABSTENCION = "ABSTENCION"


# Conceptos que los estatutos cooperativos y la LGSC no permiten someter a votación.
PROHIBITED_CONCEPTS = [
    "vender acciones",
    "dilucion de capital",
    "dilución de capital",
    "equity",
    "privatizar fondo",
    "liquidar fondo de reserva",
    "repartir fondo de prevision",
    "repartir fondo de previsión",
    "trabajo no remunerado obligatorio",
    "renuncia de derechos",
    "jurisdiccion arbitraria",
]


# --- Padrón ------------------------------------------------------------------------


def alta_socio(socio_id: str, nombre: str) -> dict[str, Any]:
    """Da de alta (o reactiva) a un socio en el padrón."""
    socio_id, nombre = socio_id.strip(), nombre.strip()
    if not socio_id or not nombre:
        raise ValueError("El socio necesita identificador y nombre.")
    initialize_db()
    with get_db_conn() as conn:
        fila = conn.execute("SELECT activo FROM socios WHERE socio_id = ?", (socio_id,)).fetchone()
        if fila is not None and fila["activo"]:
            raise ValueError(f"El socio {socio_id} ya está activo en el padrón.")
        if fila is not None:
            conn.execute(
                "UPDATE socios SET nombre = ?, activo = 1, baja_en = NULL WHERE socio_id = ?", (nombre, socio_id)
            )
        else:
            conn.execute("INSERT INTO socios (socio_id, nombre) VALUES (?, ?)", (socio_id, nombre))
    return {"socio_id": socio_id, "nombre": nombre, "activo": True}


def baja_socio(socio_id: str) -> None:
    """Da de baja a un socio; sus votos ya emitidos se conservan."""
    initialize_db()
    with get_db_conn() as conn:
        cambio = conn.execute(
            "UPDATE socios SET activo = 0, baja_en = CURRENT_TIMESTAMP WHERE socio_id = ? AND activo = 1",
            (socio_id.strip(),),
        )
        if cambio.rowcount == 0:
            raise ValueError(f"No hay un socio activo con el identificador {socio_id}.")


def listar_socios(solo_activos: bool = True) -> list[dict[str, Any]]:
    initialize_db()
    with get_db_conn() as conn:
        filtro = "WHERE activo = 1 " if solo_activos else ""
        return [dict(f) for f in conn.execute(f"SELECT * FROM socios {filtro}ORDER BY socio_id")]


def padron_activo() -> int:
    initialize_db()
    with get_db_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM socios WHERE activo = 1").fetchone()[0]


# --- Propuestas y votos ------------------------------------------------------------


def create_proposal(title: str, description: str, category: str = "subvencion") -> int:
    """Registra una propuesta para la asamblea, después de revisar las salvaguardas estatutarias."""
    initialize_db()
    combined_text = f"{title} {description}".lower()
    for forbidden in PROHIBITED_CONCEPTS:
        if forbidden in combined_text:
            raise ValueError(
                f"Propuesta estatutariamente nula: viola la LGSC (Art. 53-59). "
                f"Se detectó el concepto prohibido '{forbidden}'. "
                f"El patrimonio colectivo y los fondos sociales son irrepartibles e inalienables."
            )

    with get_db_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO assembly_proposals (title, description, category, status) VALUES (?, ?, ?, 'abierta')",
            (title.strip(), description.strip(), category.strip()),
        )
        return cursor.lastrowid


def cast_vote(
    proposal_id: int,
    member_id: str,
    member_name: str = "",
    choice: str | VoteChoice = VoteChoice.ABSTENCION,
    justification: str = "",
) -> dict[str, Any]:
    """Registra el voto de un socio: uno por propuesta y solo en propuestas abiertas.

    Si hay padrón, el socio debe estar activo en él y su nombre sale del padrón.
    """
    initialize_db()
    if isinstance(choice, str):
        try:
            choice_enum = VoteChoice(choice.upper().strip())
        except ValueError:
            raise ValueError(
                f"Opción de voto inválida '{choice}'. Opciones válidas: A_FAVOR, EN_CONTRA, ABSTENCION."
            ) from None
    else:
        choice_enum = choice
    member_id = member_id.strip()

    with get_db_conn() as conn:
        prop = conn.execute("SELECT id, status FROM assembly_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not prop:
            raise ValueError(f"La propuesta #{proposal_id} no existe.")
        if prop["status"] != "abierta":
            raise ValueError(f"La propuesta #{proposal_id} se encuentra '{prop['status']}'. No admite nuevos votos.")

        hay_padron = conn.execute("SELECT COUNT(*) FROM socios").fetchone()[0] > 0
        if hay_padron:
            socio = conn.execute(
                "SELECT nombre FROM socios WHERE socio_id = ? AND activo = 1", (member_id,)
            ).fetchone()
            if socio is None:
                raise ValueError(f"El socio {member_id} no está activo en el padrón.")
            member_name = socio["nombre"]
        if not member_name.strip():
            raise ValueError("Sin padrón registrado, indique el nombre del socio.")

        if conn.execute(
            "SELECT id FROM assembly_votes WHERE proposal_id = ? AND member_id = ?", (proposal_id, member_id)
        ).fetchone():
            raise ValueError(
                f"El socio '{member_name}' (ID: {member_id}) ya ha emitido su voto en la propuesta #{proposal_id}. "
                f"Principio LGSC: Un socio, un voto."
            )

        vote_id = conn.execute(
            "INSERT INTO assembly_votes (proposal_id, member_id, member_name, choice, justification) "
            "VALUES (?, ?, ?, ?, ?)",
            (proposal_id, member_id, member_name.strip(), choice_enum.value, justification.strip()),
        ).lastrowid

    return {
        "vote_id": vote_id,
        "proposal_id": proposal_id,
        "member_id": member_id,
        "member_name": member_name.strip(),
        "choice": choice_enum.value,
        "status": "registrado",
    }


# --- Escrutinio --------------------------------------------------------------------


def _aprobada(a_favor: int, en_contra: int, mayoria: str) -> bool:
    if mayoria == "dos_tercios":
        return a_favor > 0 and 3 * a_favor >= 2 * (a_favor + en_contra)
    return a_favor > en_contra


def _pct(parte: int, total: int) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def tally_votes(
    proposal_id: int,
    total_census_members: int | None = None,
    mayoria: Mayoria = "simple",
) -> dict[str, Any]:
    """Escruta una propuesta, la cierra y emite el acta.

    Sin `total_census_members` se usa el padrón activo; si no hay padrón, falla.
    Una propuesta ya cerrada devuelve el resultado guardado sin volver a contar.
    """
    if mayoria not in REGLAS:
        raise ValueError(f"Regla de mayoría desconocida: {mayoria}.")
    initialize_db()
    with get_db_conn() as conn:
        prop = conn.execute("SELECT * FROM assembly_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if not prop:
            raise ValueError(f"La propuesta #{proposal_id} no existe.")
        if prop["cerrada_en"] and prop["resultado_json"]:
            return {**json.loads(prop["resultado_json"]), "ya_cerrada": True}

        if total_census_members is None:
            total_census_members = conn.execute("SELECT COUNT(*) FROM socios WHERE activo = 1").fetchone()[0]
            origen_padron = "padrón activo registrado"
        else:
            origen_padron = "indicado en el escrutinio"
        if total_census_members <= 0:
            raise ValueError(
                "No hay padrón de socios activos. Registre socios (coopexecutive socios alta) "
                "o indique el padrón con --padron."
            )

        votes = [dict(r) for r in conn.execute(
            "SELECT member_id, choice FROM assembly_votes WHERE proposal_id = ? ORDER BY member_id", (proposal_id,)
        )]
        total_votes = len(votes)
        a_favor = sum(1 for v in votes if v["choice"] == VoteChoice.A_FAVOR.value)
        en_contra = sum(1 for v in votes if v["choice"] == VoteChoice.EN_CONTRA.value)
        abstencion = total_votes - a_favor - en_contra

        quorum_pct = round(total_votes / total_census_members * 100, 2)
        quorum_reached = total_votes > total_census_members / 2
        is_approved = quorum_reached and _aprobada(a_favor, en_contra, mayoria)
        status_str = "APROBADA" if is_approved else "RECHAZADA"
        if not quorum_reached:
            fundamento = "No hubo cuórum: votaron la mitad del padrón o menos."
        elif is_approved:
            fundamento = f"Con cuórum, la propuesta alcanzó la {REGLAS[mayoria]}."
        else:
            fundamento = f"Con cuórum, la propuesta no alcanzó la {REGLAS[mayoria]}."

        cerrada_en = ahora_local()
        canonico = json.dumps(
            {"propuesta": proposal_id, "titulo": prop["title"], "descripcion": prop["description"],
             "padron": total_census_members, "mayoria": mayoria, "votos": votes, "resultado": status_str},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        resolution_hash = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
        folio = f"ASAMBLEA-{proposal_id:04d}-{resolution_hash[:8].upper()}"

        acta_md = f"""# Acta de Escrutinio y Resolución de Asamblea
**Acuerdo Folio:** {folio}
**Fecha de Escrutinio:** {cerrada_en.strftime('%Y-%m-%d %H:%M:%S %Z')}
**Órgano Resolutivo:** Asamblea General de Socios (un socio, un voto)

## 1. Identificación de la Propuesta
* **Folio Propuesta:** #{proposal_id}
* **Título:** {prop['title']}
* **Categoría:** {prop['category'].upper()}
* **Materia del Acuerdo:** {prop['description']}

## 2. Cuórum
* **Padrón activo:** {total_census_members} socios ({origen_padron})
* **Votos emitidos:** {total_votes}
* **Participación:** {quorum_pct}%
* **Cuórum:** {'ACREDITADO (más de la mitad del padrón)' if quorum_reached else 'NO ACREDITADO'}

## 3. Cómputo de Votos
| Sentido del Voto | Conteo | Porcentaje de votantes |
| :--- | :--- | :--- |
| **A Favor** | {a_favor} | {_pct(a_favor, total_votes)}% |
| **En Contra** | {en_contra} | {_pct(en_contra, total_votes)}% |
| **Abstención** | {abstencion} | {_pct(abstencion, total_votes)}% |
| **Total** | {total_votes} | {100.0 if total_votes else 0.0}% |

## 4. Resolución
**Resolución:** **{status_str}**
**Regla aplicada:** {REGLAS[mayoria]}.
*Fundamentación:* {fundamento}

---
*Huella del escrutinio: `SHA256:{resolution_hash}`*
"""

        resultado = {
            "proposal_id": proposal_id,
            "title": prop["title"],
            "total_census": total_census_members,
            "total_votes": total_votes,
            "quorum_pct": quorum_pct,
            "quorum_reached": quorum_reached,
            "a_favor": a_favor,
            "en_contra": en_contra,
            "abstencion": abstencion,
            "mayoria": mayoria,
            "status": status_str,
            "is_approved": is_approved,
            "folio": folio,
            "resolution_hash": resolution_hash,
            "acta_md": acta_md,
        }
        conn.execute(
            "UPDATE assembly_proposals SET status = ?, cerrada_en = CURRENT_TIMESTAMP, resultado_json = ?, hash = ? "
            "WHERE id = ?",
            (status_str.lower(), json.dumps(resultado, ensure_ascii=False), resolution_hash, proposal_id),
        )
        conn.execute(
            "INSERT INTO assembly_decisions (session_id, decision_text, organ, proposal_id) VALUES (?, ?, ?, ?)",
            (folio, acta_md, "Asamblea General", proposal_id),
        )
    return {**resultado, "ya_cerrada": False}


def list_proposals(status: str | None = None) -> list[dict[str, Any]]:
    """Lista las propuestas registradas, de la más reciente a la más antigua."""
    initialize_db()
    with get_db_conn() as conn:
        if status:
            filas = conn.execute("SELECT * FROM assembly_proposals WHERE status = ? ORDER BY id DESC", (status,))
        else:
            filas = conn.execute("SELECT * FROM assembly_proposals ORDER BY id DESC")
        return [dict(row) for row in filas]


def get_proposal(proposal_id: int) -> dict[str, Any] | None:
    initialize_db()
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM assembly_proposals WHERE id = ?", (proposal_id,)).fetchone()
        return dict(row) if row else None
