"""Casos dorados de comportamiento (marcador `eval`); también: python -m coopexecutive.evals."""
from __future__ import annotations

import pytest

from coopexecutive.evals import casos, correr

pytestmark = pytest.mark.eval


@pytest.mark.parametrize("caso", casos(), ids=lambda c: f"{c.familia}:{c.nombre}")
def test_caso(caso):
    resultado = correr(caso)
    assert resultado.ok, resultado.detalle
