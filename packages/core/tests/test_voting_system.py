import pytest
from coopexecutive.governance.voting import (
    create_proposal,
    cast_vote,
    tally_votes,
    list_proposals,
    VoteChoice,
)


def test_create_proposal_and_list(tmp_path, monkeypatch):
    test_db = tmp_path / "test_memory.db"
    monkeypatch.setenv("EPISODIC_DB_PATH", str(test_db))

    prop_id = create_proposal(
        title="Postulación a Fondos BID 2026",
        description="Aprobación de la contrapartida comunal para el proyecto eólico.",
        category="subvencion",
    )
    assert prop_id > 0

    proposals = list_proposals()
    assert len(proposals) == 1
    assert proposals[0]["title"] == "Postulación a Fondos BID 2026"
    assert proposals[0]["status"] == "abierta"


def test_statutory_invariant_rejection(tmp_path, monkeypatch):
    test_db = tmp_path / "test_memory.db"
    monkeypatch.setenv("EPISODIC_DB_PATH", str(test_db))

    # Intentar someter una propuesta violatoria de la LGSC o de la integridad de los miembros
    with pytest.raises(ValueError, match="Propuesta estatutariamente nula"):
        create_proposal(
            title="Venta de participación a Fondo VC",
            description="Acordar vender acciones de la cooperativa para dilución de capital.",
            category="financiero",
        )

    with pytest.raises(ValueError, match="Propuesta estatutariamente nula"):
        create_proposal(
            title="Imposición de jornadas extraordinarias",
            description="Exigir trabajo no remunerado obligatorio para cubrir pérdidas operativas.",
            category="estatutario",
        )


def test_one_member_one_vote_enforcement(tmp_path, monkeypatch):
    test_db = tmp_path / "test_memory.db"
    monkeypatch.setenv("EPISODIC_DB_PATH", str(test_db))

    prop_id = create_proposal("Aprobación de Balances", "Ejercicio fiscal 2025")

    # Primer voto: exitoso
    res = cast_vote(
        proposal_id=prop_id,
        member_id="SOC-001",
        member_name="María López",
        choice="A_FAVOR",
        justification="Cumple con el dictamen del consejo de vigilancia",
    )
    assert res["status"] == "registrado"
    assert res["choice"] == "A_FAVOR"

    # Segundo intento de voto del mismo socio en la misma propuesta: DEBE FALLAR
    with pytest.raises(ValueError, match="ya ha emitido su voto"):
        cast_vote(
            proposal_id=prop_id,
            member_id="SOC-001",
            member_name="María López",
            choice="EN_CONTRA",
        )


def test_tally_votes_approved_quorum(tmp_path, monkeypatch):
    test_db = tmp_path / "test_memory.db"
    monkeypatch.setenv("EPISODIC_DB_PATH", str(test_db))

    prop_id = create_proposal("Equipamiento de Taller", "Compra de maquinaria comunal")

    # Votan 7 de 10 socios (70% cuórum > 50%)
    for i in range(1, 6):
        cast_vote(prop_id, f"SOC-{i:03d}", f"Socio {i}", VoteChoice.A_FAVOR)
    cast_vote(prop_id, "SOC-006", "Socio 6", VoteChoice.EN_CONTRA)
    cast_vote(prop_id, "SOC-007", "Socio 7", VoteChoice.ABSTENCION)

    tally = tally_votes(prop_id, total_census_members=10)
    assert tally["total_votes"] == 7
    assert tally["quorum_pct"] == 70.0
    assert tally["quorum_reached"] is True
    assert tally["a_favor"] == 5
    assert tally["en_contra"] == 1
    assert tally["abstencion"] == 1
    assert tally["status"] == "APROBADA"
    assert tally["is_approved"] is True
    assert "SHA256:" in tally["acta_md"]


def test_tally_votes_no_quorum(tmp_path, monkeypatch):
    test_db = tmp_path / "test_memory.db"
    monkeypatch.setenv("EPISODIC_DB_PATH", str(test_db))

    prop_id = create_proposal("Reforma Menor", "Ajuste de horario de oficinas")

    # Votan solo 2 de 10 socios (20% cuórum < 50%)
    cast_vote(prop_id, "SOC-001", "Socio 1", VoteChoice.A_FAVOR)
    cast_vote(prop_id, "SOC-002", "Socio 2", VoteChoice.A_FAVOR)

    tally = tally_votes(prop_id, total_census_members=10)
    assert tally["total_votes"] == 2
    assert tally["quorum_pct"] == 20.0
    assert tally["quorum_reached"] is False
    assert tally["status"] == "RECHAZADA"
    assert tally["is_approved"] is False
