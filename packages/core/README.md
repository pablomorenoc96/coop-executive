# CoopExecutive 🏛️🌱
> **The Open-Source AI Collegiate Executive Board & Grant Procurement Agent for Cooperatives, Non-Profits, and the Social Economy.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Zero Cost Models](https://img.shields.io/badge/Models-OpenRouter%20:free%20%7C%20Ollama-orange.svg)](#zero-cost-ai-setup)
[![Social Economy Manifesto](https://img.shields.io/badge/Philosophy-Social%20Economy-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

[🇪🇸 Leer en Español](README.es.md)

**CoopExecutive** is built as a **direct antithesis to Silicon Valley's corporate AI tools** (such as OpenExecutive). While conventional tools assume venture capital (VC) backing, shareholder primacy, stock options, and aggressive profit extraction, **CoopExecutive** is architected for **democratic worker cooperatives, non-profit organizations (NGOs), community land trusts, and social enterprises**.

It features a native **Grant Procurement Agent**, designed to evaluate, structure, and draft multilateral funding proposals (via platforms like [FundsforNGOs](https://www.fundsforngos.org/), development banks, and climate/social foundations).

---

## ⚖️ The Antithesis: Silicon Valley vs. CoopExecutive

| Dimension | OpenExecutive (Silicon Valley) | CoopExecutive (Social & Solidarity Economy) |
| :--- | :--- | :--- |
| **Decision Power** | *One dollar, one vote* (Shareholders / VC investors). | **One member, one vote** (General Assembly democracy). |
| **Oversight** | Private venture capital audit committees. | **Vigilance Board** (*Consejo de Vigilancia* — internal democratic audit). |
| **Funding Engine** | Predatory debt, VC rounds (Seed, Series A), equity dilution. | **Bootstrap operations + Non-reimbursable grants ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Finance & Surpluses**| Maximize EBITDA & shareholder dividends. | **Protected Statutory Funds:** Reserve Fund, Social Welfare, and Education. |
| **Legal Regime** | Delaware C-Corp, S.A.P.I., S.A. de C.V. | General Cooperative Societies Law, Non-Profit Civil Associations (A.C.). |
| **Technology** | Proprietary platforms, expensive vendor lock-in. | **100% Open Source, free-tier models (OpenRouter `:free` or local Ollama).** |

---

## ✨ Core Features

### 1. Grant Procurement Agent
* **Call Suitability Evaluation (0-100 pts):** Analyzes grant notices (text, URL, or document) across 8 dimensions to yield an instant verdict: *APPLY*, *EXPLORE*, *CONDITIONAL*, or *DO NOT APPLY*.
* **Logical Framework Approach (LFA / MML):** Generates complete 4x4 matrix (Goal, Purpose, Outputs, Activities) with Objectively Verifiable Indicators (OVIs) and critical assumptions.
* **Theory of Change (ToC):** Establishes the causal chain from local inputs to lasting community impact aligned with UN Sustainable Development Goals (SDGs 7, 8, 9, 12, 13).
* **Auditable Budgets:** Structures eligible costs (CAPEX, OPEX, technical staff, overhead, and matching funds).

### 2. Collegiate Social Council
* **Vigilance Board:** Ethical oversight, constitutional bylaws adherence, and conflict of interest prevention.
* **Social Legal Counsel:** Cooperative law, non-profit tax exemptions, and open intellectual property.
* **Solidarity Finance:** Protection of mandatory reserve, welfare, and education funds.
* **Community Technology:** Open-source hardware, clean energy, and technical self-determination.
* **Assembly Secretariat:** Automated drafting of formal assembly notices, agendas, and minutes.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`

### 1. Installation
```bash
git clone https://github.com/pablomorenoc96/coop-executive.git
cd coop-executive/packages/core
```

### 2. Configure Environment
```bash
cp ../../.env.example ../../.env
```
CoopExecutive works with **100% free models**:
* **Cloud (Recommended):** Set your free [OpenRouter API key](https://openrouter.ai/keys) (`OPENROUTER_API_KEY=sk-or-v1-...`). Preconfigured with `minimax/minimax-m3:free` and `nvidia/nemotron-3-super-120b-a12b:free` at $0.00 cost.
* **Local Offline:** Enable `LOCAL_MODELS_ENABLED=true` to run fully private on your machine via [Ollama](https://ollama.com/).

### 3. Usage Examples
```bash
# View active organization profile & statutory funds:
uv run coopexecutive info

# Generate a 4x4 Logical Framework matrix:
uv run coopexecutive marco-logico "Community Clean Energy & Rural Tech Training"

# Evaluate any grant opportunity:
uv run coopexecutive evaluar-convocatoria "https://www.fundsforngos.org/..."

# Interactive chat with the collegiate board:
uv run coopexecutive chat
```

---

## 📖 Documentation
* [Architecture & Design Details](ARCHITECTURE.md)
* [Social Economy Manifesto](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)
* [Logical Framework Practical Guide](docs/GUIA_MARCO_LOGICO.md)
* [Statutory Funds & Cooperative Governance Guide](docs/GUIA_FONDOS_ESTATUTARIOS.md)
* [Contributing Guide](CONTRIBUTING.md)

---

## 📄 License
[MIT License](LICENSE) — Free for cooperatives, non-profits, communities, and developers worldwide.
