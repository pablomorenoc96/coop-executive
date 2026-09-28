"""Seguimiento de financiadores y expedientes de procuración de fondos."""
from coopexecutive.crm import cases, funders
from coopexecutive.crm.cases import Avance, Expediente, ExpedienteDuplicado
from coopexecutive.crm.funders import Financiador, FinanciadorDuplicado

__all__ = [
    "cases",
    "funders",
    "Avance",
    "Expediente",
    "ExpedienteDuplicado",
    "Financiador",
    "FinanciadorDuplicado",
]
