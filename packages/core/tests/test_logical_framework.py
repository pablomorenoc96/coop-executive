import pytest
from coopexecutive.grant_tools.logical_framework import ProjectLogicalFramework, LogFrameRow


def test_logical_framework_markdown():
    row_fin = LogFrameRow(
        level="Fin",
        narrative_summary="Mejorar la autosuficiencia energética comunitaria",
        indicators=["Reducción del 30% en costos de energía"],
        verification_means=["Facturación eléctrica y censos"],
        assumptions=["Estabilidad en la red local"],
    )
    row_prop = LogFrameRow(
        level="Propósito",
        narrative_summary="Instalar microrredes eólicas y capacitar comités",
        indicators=["3 microrredes operativas"],
        verification_means=["Actas de entrega-recepción"],
        assumptions=["Participación activa de la asamblea"],
    )

    logframe = ProjectLogicalFramework(
        project_title="Energía Renovable para la Producción Rural",
        target_ods=["ODS 7", "ODS 9", "ODS 12"],
        problem_statement="Falta de energía asequible en talleres comunitarios",
        theory_of_change="Si se instalan aerogeneradores y se capacita a los socios, se reduce el costo productivo.",
        rows=[row_fin, row_prop],
    )

    md = logframe.to_markdown()
    assert "Energía Renovable para la Producción Rural" in md
    assert "ODS 7, ODS 9, ODS 12" in md
    assert "Mejorar la autosuficiencia energética comunitaria" in md
    assert "3 microrredes operativas" in md
