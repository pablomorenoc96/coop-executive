from coopexecutive.grant_tools.budget_builder import BudgetItem, GrantBudget


def test_grant_budget_calculations():
    budget = GrantBudget(project_title="Proyecto Piloto Comunitario")
    budget.items.append(
        BudgetItem(
            category="Personal",
            concept="Ingeniero de Automatización",
            unit="meses",
            quantity=6.0,
            unit_cost=2000.0,
            requested_amount=12000.0,
            matching_amount=2000.0,
        )
    )
    budget.items.append(
        BudgetItem(
            category="Equipamiento",
            concept="Inversor de potencia y control",
            unit="piezas",
            quantity=2.0,
            unit_cost=1500.0,
            requested_amount=3000.0,
            matching_amount=0.0,
        )
    )

    assert budget.total_requested == 15000.0
    assert budget.total_matching == 2000.0
    assert budget.grand_total == 17000.0

    md = budget.to_markdown()
    assert "Proyecto Piloto Comunitario" in md
    assert "15,000.00 USD" in md
    assert "2,000.00 USD" in md
    assert "17,000.00 USD" in md
