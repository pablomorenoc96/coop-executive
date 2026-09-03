"""Sistema de votación soberana y escrutinio democrático (LGSC Art. 36-40).

Principios:
- Un socio = Un voto (sin ponderación por capital ni aportaciones).
- Cuórum estatutario mínimo (50% + 1 socios activos).
- Invariantes estatutarias: Veto a propuestas que diluyan capital o liquiden fondos irrepartibles.
- Generación formal de Acta de Escrutinio con trazabilidad y hash de verificación.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any
from coopexecutive.memory.episodic import get_db_conn, initialize_db


class VoteChoice(str, Enum):
    A_FAVOR = "A_FAVOR"
    EN_CONTRA = "EN_CONTRA"
    ABSTENCION = "ABSTENCION"


# Palabras clave prohibidas por estatutos cooperativos y LGSC
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


def create_proposal(title: str, description: str, category: str = "subvencion") -> int:
    """Registra una nueva propuesta a someter ante la Asamblea General.
    
    Verifica previamente las salvaguardas estatutarias.
    """
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
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO assembly_proposals (title, description, category, status)
            VALUES (?, ?, ?, 'abierta')
            """,
            (title.strip(), description.strip(), category.strip()),
        )
        return cursor.lastrowid


def cast_vote(
    proposal_id: int,
    member_id: str,
    member_name: str,
    choice: str | VoteChoice,
    justification: str = "",
) -> dict[str, Any]:
    """Emite el voto de un socio bajo el principio 'Un Socio = Un Voto'.
    
    Previene duplicados y valida que la propuesta esté abierta.
    """
    initialize_db()
    if isinstance(choice, str):
        try:
            choice_enum = VoteChoice(choice.upper().strip())
        except ValueError:
            raise ValueError(f"Opción de voto inválida '{choice}'. Opciones válidas: A_FAVOR, EN_CONTRA, ABSTENCION.")
    else:
        choice_enum = choice

    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Verificar estado de la propuesta
        cursor.execute("SELECT id, title, status FROM assembly_proposals WHERE id = ?", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            raise ValueError(f"La propuesta #{proposal_id} no existe.")
        if prop["status"] != "abierta":
            raise ValueError(f"La propuesta #{proposal_id} se encuentra '{prop['status']}'. No admite nuevos votos.")

        # Verificar si el socio ya votó (1 socio = 1 voto)
        cursor.execute(
            "SELECT id FROM assembly_votes WHERE proposal_id = ? AND member_id = ?",
            (proposal_id, member_id.strip()),
        )
        if cursor.fetchone():
            raise ValueError(
                f"El socio '{member_name}' (ID: {member_id}) ya ha emitido su voto en la propuesta #{proposal_id}. "
                f"Principio LGSC: Un socio, un voto."
            )

        cursor.execute(
            """
            INSERT INTO assembly_votes (proposal_id, member_id, member_name, choice, justification)
            VALUES (?, ?, ?, ?, ?)
            """,
            (proposal_id, member_id.strip(), member_name.strip(), choice_enum.value, justification.strip()),
        )
        vote_id = cursor.lastrowid

    return {
        "vote_id": vote_id,
        "proposal_id": proposal_id,
        "member_id": member_id,
        "member_name": member_name,
        "choice": choice_enum.value,
        "status": "registrado",
    }


def tally_votes(proposal_id: int, total_census_members: int = 12) -> dict[str, Any]:
    """Realiza el escrutinio formal de una propuesta y emite el Acta de Acuerdo."""
    initialize_db()
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assembly_proposals WHERE id = ?", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            raise ValueError(f"La propuesta #{proposal_id} no existe.")

        cursor.execute("SELECT * FROM assembly_votes WHERE proposal_id = ?", (proposal_id,))
        votes = [dict(row) for row in cursor.fetchall()]

    total_votes = len(votes)
    a_favor = sum(1 for v in votes if v["choice"] == VoteChoice.A_FAVOR.value)
    en_contra = sum(1 for v in votes if v["choice"] == VoteChoice.EN_CONTRA.value)
    abstencion = sum(1 for v in votes if v["choice"] == VoteChoice.ABSTENCION.value)

    quorum_pct = round((total_votes / total_census_members) * 100, 2) if total_census_members > 0 else 0.0
    quorum_reached = total_votes > (total_census_members / 2.0)  # 50% + 1 socio

    valid_votes = a_favor + en_contra
    majority_pct = round((a_favor / valid_votes) * 100, 2) if valid_votes > 0 else 0.0
    is_approved = quorum_reached and a_favor > en_contra

    status_str = "APROBADA" if is_approved else "RECHAZADA"

    # Generar Hash Criptográfico del Acta de Acuerdo
    raw_hash_data = f"{proposal_id}-{prop['title']}-{total_votes}-{a_favor}-{en_contra}-{abstencion}"
    resolution_hash = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()

    acta_md = f"""# Acta de Escrutinio y Resolución de Asamblea
**Acuerdo Folio:** ASAMBLEA-{proposal_id:04d}-{resolution_hash}  
**Fecha de Escrutinio:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Órgano Resolutivo:** Asamblea General de Socios (Principio: Un Socio = Un Voto)

---

## 1. Identificación de la Propuesta
* **Folio Propuesta:** #{proposal_id}
* **Título:** {prop['title']}
* **Categoría:** {prop['category'].upper()}
* **Materia del Acuerdo:** {prop['description']}

---

## 2. Certificación de Cuórum Legal (LGSC Art. 36-40)
* **Padrón Activo Total:** {total_census_members} socios acreditados
* **Cédulas de Voto Emitidas:** {total_votes} votos
* **Porcentaje de Participación:** {quorum_pct}%
* **Estatus de Cuórum:** {'✓ CUÓRUM LEGAL ACREDITADO (>50%)' if quorum_reached else '✗ SIN CUÓRUM LEGAL REQUERIDO'}

---

## 3. Cómputo de Votos y Resultados
| Sentido del Voto | Conteo | Porcentaje s/ Votantes |
| :--- | :--- | :--- |
| **A Favor** | {a_favor} | {round((a_favor/total_votes)*100, 1) if total_votes else 0}% |
| **En Contra** | {en_contra} | {round((en_contra/total_votes)*100, 1) if total_votes else 0}% |
| **Abstención** | {abstencion} | {round((abstencion/total_votes)*100, 1) if total_votes else 0}% |
| **Total Cédulas** | {total_votes} | 100.0% |

---

## 4. Dictamen Resolutivo de la Mesa Directiva
**Resolución:** **{status_str}**  
*Fundamentación:* {'La propuesta alcanzó mayoría calificada con validez estatutaria.' if is_approved else 'La propuesta no alcanzó los votos favorables suficientes o carece de cuórum.'}

---
*Firma Digital del Escrutinio: `SHA256:{resolution_hash}` — Certificado por CoopExecutive Engine.*
"""

    return {
        "proposal_id": proposal_id,
        "title": prop["title"],
        "total_census": total_census_members,
        "total_votes": total_votes,
        "quorum_pct": quorum_pct,
        "quorum_reached": quorum_reached,
        "a_favor": a_favor,
        "en_contra": en_contra,
        "abstencion": abstencion,
        "status": status_str,
        "is_approved": is_approved,
        "resolution_hash": resolution_hash,
        "acta_md": acta_md,
    }


def list_proposals(status: str | None = None) -> list[dict[str, Any]]:
    """Lista las propuestas registradas en la memoria del sistema."""
    initialize_db()
    with get_db_conn() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM assembly_proposals WHERE status = ? ORDER BY id DESC", (status,))
        else:
            cursor.execute("SELECT * FROM assembly_proposals ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_proposal(proposal_id: int) -> dict[str, Any] | None:
    """Obtiene el detalle de una propuesta."""
    initialize_db()
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assembly_proposals WHERE id = ?", (proposal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
