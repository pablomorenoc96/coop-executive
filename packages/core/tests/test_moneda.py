import pytest

from coopexecutive.grant_tools.budget_builder import GrantBudget
from coopexecutive.utils.moneda import formatear_monto, validar_moneda


def test_validar_moneda_normaliza():
    assert validar_moneda(" mxn ") == "MXN"
    assert validar_moneda("EUR") == "EUR"


@pytest.mark.parametrize("codigo", ["", "PESOS", "$", "XXX", "XTS", "XAU", "US"])
def test_validar_moneda_rechaza(codigo):
    with pytest.raises(ValueError, match="ISO 4217"):
        validar_moneda(codigo)


def test_formatear_monto_por_decimales():
    assert formatear_monto(57000, "usd") == "57,000.00 USD"
    assert formatear_monto(1500000, "JPY") == "1,500,000 JPY"
    assert formatear_monto(12.5, "KWD") == "12.500 KWD"
    assert formatear_monto(1, "CLF") == "1.0000 CLF"


def test_presupuesto_valida_moneda():
    assert GrantBudget(project_title="P", currency="mxn").currency == "MXN"
    with pytest.raises(ValueError):
        GrantBudget(project_title="P", currency="PESOS")
