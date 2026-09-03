import pytest
from coopexecutive.grant_tools.eligibility_evaluator import evaluate_grant_opportunity


def test_evaluate_grant_opportunity_high_score():
    report = evaluate_grant_opportunity(
        call_title="Fondo de Transición Energética Comunitaria",
        donor_agency="Agencia Internacional de Cooperación",
        deadline="2026-12-31",
        available_budget="$100,000 USD",
        mission_alignment=20.0,
        alignment_notes="Plena coincidencia con los objetivos",
        geo_eligibility=10.0,
        geo_notes="Elegible para cooperativas de América Latina",
        budget_feasibility=15.0,
        budget_notes="Presupuesto adecuado para los costos de ingeniería",
        timeline_feasibility=10.0,
        timeline_notes="12 meses es viable",
        capacity_score=15.0,
        capacity_notes="Equipo técnico disponible",
        impact_score=15.0,
        impact_notes="Beneficia a 5 comunidades rurales",
        strategic_value=10.0,
        strategic_notes="Deja capacidad instalada",
        reporting_manageability=5.0,
        reporting_notes="Informes semestrales manejables",
        strengths=["Experiencia en energía comunitaria", "Alianzas técnicas"],
        risks=["Demoras en entrega de suministros"],
        next_steps=["Elaborar Marco Lógico", "Integrar presupuesto"],
    )

    assert report.total_score == 100.0
    assert "APLICAR" in report.recommendation
    assert report.color_code == "🟢"
    md = report.to_markdown()
    assert "Fondo de Transición Energética Comunitaria" in md
    assert "Experiencia en energía comunitaria" in md


def test_evaluate_grant_opportunity_low_score():
    report = evaluate_grant_opportunity(
        call_title="Fondo Incompatible",
        donor_agency="Corporación Privada",
        deadline="2026-09-10",
        available_budget="$5,000 USD",
        mission_alignment=5.0,
        alignment_notes="Poca coincidencia",
        geo_eligibility=0.0,
        geo_notes="Solo empresas privadas europeas",
        budget_feasibility=5.0,
        budget_notes="Monto insuficiente",
        timeline_feasibility=5.0,
        timeline_notes="Demasiado apresurado",
        capacity_score=5.0,
        capacity_notes="Sin experiencia en el ramo",
        impact_score=5.0,
        impact_notes="Bajo impacto comunitario",
        strategic_value=0.0,
        strategic_notes="Sin valor estratégico",
        reporting_manageability=2.0,
        reporting_notes="Excesiva burocracia",
        strengths=[],
        risks=["Incompatibilidad legal", "Costo operativo elevado"],
        next_steps=["Descartar postulación"],
    )

    assert report.total_score < 40.0
    assert "NO APLICAR" in report.recommendation
    assert report.color_code == "🔴"
