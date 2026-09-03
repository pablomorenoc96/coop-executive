import pytest
from coopexecutive.grant_tools.dossier_generator import ProposalDossier
from coopexecutive.grant_tools.logical_framework import ProjectLogicalFramework, LogFrameRow
from coopexecutive.grant_tools.budget_builder import GrantBudget, BudgetItem

def test_proposal_dossier_markdown_generation():
    # Build sample logframe
    logframe = ProjectLogicalFramework(
        project_title="Electrificación Limpia de Talleres",
        target_ods=["ODS 7", "ODS 9"],
        problem_statement="Falta de energía asequible",
        theory_of_change="Si se instalan aerogeneradores comunitarios, se reduce el costo de producción.",
        rows=[
            LogFrameRow("Fin", "Reducir costos energéticos", ["30% ahorro"], ["Recibos"], ["Tarifas"]),
            LogFrameRow("Propósito", "Instalar 3 microrredes", ["3 sistemas"], ["Actas"], ["Participación"]),
        ]
    )

    # Build sample budget
    budget = GrantBudget(
        project_title="Electrificación Limpia de Talleres",
        currency="USD",
        items=[
            BudgetItem(
                category="Equipamiento",
                concept="3 Generadores eólicos",
                unit="piezas",
                quantity=3.0,
                unit_cost_usd=15000.0,
                requested_amount_usd=45000.0,
                matching_amount_usd=5000.0
            ),
            BudgetItem(
                category="Personal",
                concept="Ingeniero de instalación",
                unit="meses",
                quantity=6.0,
                unit_cost_usd=2000.0,
                requested_amount_usd=12000.0,
                matching_amount_usd=3000.0
            ),
        ]
    )

    dossier = ProposalDossier(
        project_name="Electrificación Limpia de Talleres",
        organization_name="Cooperativa de Producción Comunitaria S.C. de R.L.",
        donor_agency="Banco Interamericano de Desarrollo",
        call_title="Convocatoria Transición Energética Justa 2026",
        logical_framework=logframe,
        budget=budget
    )

    md = dossier.to_markdown()

    assert "DOSSIER DE POSTULACIÓN TÉCNICA Y FINANCIERA" in md
    assert "Cooperativa de Producción Comunitaria S.C. de R.L." in md
    assert "Reducir costos energéticos" in md
    assert "**Fondos Solicitados al Donante:** $57,000.00 USD" in md
    assert "**Contrapartida Institucional (Especie/Valorizada):** $8,000.00 USD" in md
    assert "**Presupuesto Total Consolidado:** $65,000.00 USD" in md
    assert "SALVAGUARDAS COOPERATIVAS" in md
    assert "ESTRATEGIA DE SOSTENIBILIDAD" in md
