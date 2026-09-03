# CoopExecutive 🏛️🌱
> **El Sistema Directivo Colegiado y Agente Procurador de Fondos con IA para Cooperativas, Asociaciones Civiles (A.C. / ONGs) y la Economía Social.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Modelos Libres](https://img.shields.io/badge/Modelos-OpenRouter%20:free%20%7C%20Ollama-orange.svg)](#configuración-a-costo-cero)
[![Manifiesto Economía Social](https://img.shields.io/badge/Filosof%C3%ADa-Econom%C3%ADa%20Social-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

[🇺🇸 Read in English](README.md)

**CoopExecutive** nace como una **antítesis directa al modelo de Silicon Valley** encarnado por herramientas como OpenExecutive. Mientras que el software tradicional asume corporaciones con juntas de accionistas, capital de riesgo (VC), búsqueda de *exits* y maximización de utilidades individuales, **CoopExecutive** está diseñado para las **organizaciones democráticas, cooperativas de producción y servicios, asociaciones civiles y proyectos de soberanía comunitaria**.

Incorpora de forma nativa al **Agente Procurador de Fondos (Grant Procurement Agent)**, especializado en captar fondos no reembolsables y cooperaciones internacionales (a través de plataformas como [FundsforNGOs](https://www.fundsforngos.org/), agencias bilaterales y fundaciones climáticas/sociales).

---

## ⚖️ La Antítesis: Silicon Valley vs. CoopExecutive

| Dimensión | OpenExecutive (Silicon Valley) | CoopExecutive (Economía Social y Solidaria) |
| :--- | :--- | :--- |
| **Poder de Decisión** | *Un dólar, un voto* (Junta de Accionistas / Inversionistas VC). | **Un socio, un voto** (Asamblea General Democrática). |
| **Órgano de Control** | Comités de auditoría de fondos de inversión privados. | **Consejo de Vigilancia** (auditoría interna democrática y ética). |
| **Financiamiento** | Deuda predatoria, rondas de capital (Seed, Serie A), dilución. | **Flujo operativo bootstrap + Grants y Convocatorias Internacionales ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Finanzas** | Maximizar EBITDA y dividendos para socios capitalistas. | **Fondos Estatutarios Obligatorios (LGSC):** Fondo de Reserva, Previsión Social y Educación Cooperativa. |
| **Régimen Legal** | S.A.P.I., S.A. de C.V., Delaware C-Corp. | Ley General de Sociedades Cooperativas (LGSC), Código Civil (A.C.), Donatarias Autorizadas (SAT). |
| **Tecnología** | Plataformas privativas, licencias caras y vendor lock-in. | **100% Código Abierto, modelos gratuitos (OpenRouter / Ollama).** |

---

## ✨ Capacidades Principales

### 1. Agente Procurador de Fondos (*Grant Procurement Agent*)
* **Evaluación de Convocatorias (0 a 100 puntos):** Analiza bases de convocatorias en segundos extrayendo fechas, montos y requisitos con una rúbrica de 8 dimensiones: *APLICAR*, *EXPLORAR*, *CONDICIONAL* o *NO APLICAR*.
* **Metodología de Marco Lógico (MML):** Genera automáticamente Árboles de Problemas, Árboles de Objetivos y la Matriz de Indicadores de Resultados (MIR) 4x4.
* **Teoría del Cambio (ToC):** Estructura la cadena causal vinculada a los Objetivos de Desarrollo Sostenible (ODS 7, 8, 9, 12, 13).
* **Presupuestos Auditables:** Desglose riguroso de CAPEX, OPEX, personal técnico, contrapartidas y gastos administrativos.

### 2. Consejo Directivo y de Vigilancia Colegiado
* **Consejo de Vigilancia:** Auditoría democrática interna y supervisión estatutaria.
* **Asesor Jurídico en Economía Social:** Marco legal de cooperativas, donatarias autorizadas y convenios abiertos.
* **Gestor de Finanzas Solidarias:** Blindaje del Fondo de Reserva, Previsión Social y Educación Cooperativa.
* **Desarrollo Tecnológico Comunitario:** Fomento de infraestructura abierta, energías limpias y formación técnica.
* **Secretaría de Actas:** Redacción formal de convocatorias, cómputo de quórum y actas de asamblea.

---

## 🚀 Inicio Rápido

```bash
git clone https://github.com/pablomorenoc96/coop-executive.git
cd coop-executive/packages/core
cp ../../.env.example ../../.env
```

### Comandos de Ejemplo:
```powershell
# Ver perfil y fondos estatutarios:
uv run coopexecutive info

# Generar Marco Lógico completo:
uv run coopexecutive marco-logico "Energía Limpia Comunitaria y Capacitación Técnica"

# Evaluar una convocatoria:
uv run coopexecutive evaluar-convocatoria "https://www.fundsforngos.org/..."

# Sesión interactiva con el consejo:
uv run coopexecutive chat
```

---

## 📄 Licencia
[MIT License](LICENSE) — Libre para usar, modificar, cooperativizar y compartir.
