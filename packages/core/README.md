# CoopExecutive

![CoopExecutive Banner](assets/banner_en.png)

> **Collegiate Executive Board & Grant Procurement AI Agent for Cooperatives, Civil Associations (Non-Profits / NGOs), and Social Economy Organizations.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Free & Paid AI](https://img.shields.io/badge/Models-Free%20%26%20Commercial-orange.svg)](#ai-model-setup-free-local-and-paid-options)
[![Social Economy Principles](https://img.shields.io/badge/Document-Principles%20%26%20Governance-darkgreen.svg)](docs/PRINCIPIOS_ECONOMIA_SOCIAL.en.md)

[🇲🇽 Leer en Español](README.es.md) | [📢 Outreach & Social Media Kit](docs/KIT_DIFUSION_REDES.md)

**CoopExecutive** is an open-source tool built for democratic organizations. Unlike traditional corporate management software focused on shareholder equity, venture rounds, and private profit extraction, CoopExecutive is designed for sovereign assemblies (*one member, one vote*), protected statutory reserves, and non-reimbursable grant funding.

---

## What is CoopExecutive Technically?

In software architecture terms, **CoopExecutive is an Autonomous Vertical AI Agent**. Rather than an open-ended conversational bot, it is a structured system composed of modular layers designed to process environment inputs, apply legal and business rules, and produce auditable technical outputs.

![CoopExecutive Architecture](assets/architecture.png)

### Architectural Components

1. **Environment & Perception:**
   - **Inputs:** Ingests the institutional profile (`company/profile.yaml`), grant notices from international donors, and applicable legal statutes (Cooperative Law / LGSC).
   - **Channels:** Accepts inputs via command-line interface (CLI) and an interactive local web dashboard.

2. **Collegiate Orchestrator (Role Router):**
   - Routes requests to specialized functional roles:
     - *Grant Procurement:* Opportunity evaluation and proposal drafting.
     - *Vigilance Board:* Internal democratic audit and compliance oversight.
     - *Legal Counsel:* Cooperative statutes, non-profit tax exemptions, and open licensing.
     - *Solidarity Finance:* Cash flow oversight and statutory fund protection.
     - *Open Technology:* Open-source software, accessible technical infrastructure, and industry standards (ISO/IEC/NOM).
     - *Assembly Secretariat:* Agendas, accredited roll, legal quorum, and minutes.

3. **Persistent Episodic Memory (SQLite):**
   - Local database (`coop_memory.db`) maintaining an auditable relational record of:
     - Historical assembly agreements.
     - Assembly proposals.
     - Registered member ballots (with strict deduplication per proposal).
     - Prior grant opportunity evaluations.

4. **Universal Inference Engine:**
   - Flexible routing across three compute tiers:
     - *Zero-cost cloud tier ($0.00):* Free OpenRouter models with 429 rate-limit fallback.
     - *Local offline tier:* Fully private execution via Ollama (`granite4.1`, `qwen3.8`).
     - *Commercial APIs (optional):* OpenAI, Anthropic, Google Gemini, Groq, Mistral, and DeepSeek.

5. **Deterministic Tool-Use Layer:**
   - 100-point multicriteria rubric (evaluates 8 dimensions to issue *APPLY*, *EXPLORE*, or *REJECT* verdicts).
   - 4x4 Logical Framework Matrix (Goals, Indicators, Verification Means, Assumptions).
   - Budget builder with explicit cash and in-kind matching funds calculations.
   - Multilateral proposal dossier compiler for major funding bodies (IDB, Horizon, foundations).

6. **Hard Statutory Guardrails (Invariants):**
   - Code-level checks that immediately reject any proposal attempting to:
     - Sell equity, issue corporate shares, or dilute member ownership.
     - Liquidate or privatize protected statutory funds (Reserve, Social Welfare, Education).
     - Enforce mandatory unpaid labor or waive fundamental member rights.

---

## Structural Comparison

| Dimension | Traditional Corporate Approach | CoopExecutive |
| :--- | :--- | :--- |
| **Decision Authority** | Capital-weighted (*one dollar, one vote*). | Democratic (*one member, one vote* in General Assembly). |
| **Oversight** | Board of directors representing private shareholders. | Independent **Vigilance Board** elected by members. |
| **Financing** | Equity sales, commercial debt, and acquisition targets. | Sustainable operations and **non-reimbursable grants**. |
| **Surplus** | Maximization of private dividends. | **Protected Statutory Funds:** Reserve (15%), Welfare (10%), Education (10%). |
| **Legal Structure** | For-profit corporations (C-Corp, S.A. de C.V.). | Cooperative Societies and Non-Profit Civil Associations. |
| **Infrastructure** | Proprietary SaaS with subscription lock-in. | **100% Open Source (MIT), free ($0.00) models and optional commercial APIs.** |

---

## Visual Demo

![CoopExecutive Demo](assets/demo_en.gif)

---

## Core Capabilities

### 1. Multilateral Grant Procurement
* **100-Point Evaluation Rubric:** Analyzes text or PDF calls to extract deadlines, budgets, eligibility, and strategic fit.
* **Logical Framework Matrix (LFM / RBM):** Builds 4x4 Results Matrices and connects activities to UN SDGs.
* **Multilateral Proposal Dossier:** Generates audit-ready project documentation for international funding bodies.

### 2. Democratic Assembly Voting (One Member = One Vote)
* **Ballot Casting:** Registers votes individually, rejecting duplicate ballots automatically.
* **Live Quorum Calculation:** Computes whether statutory attendance (>50% + 1 members) has been met.
* **Cryptographic Minutes:** Issues formal certificates with SHA-256 digital hashes for audit trails.
* **Statutory Invariant Verification:** Blocks motions violating cooperative principles or labor rights.

### 3. Collegiate Board Advisory
* Answers operational, technical, and legal questions regarding cooperative law and tax exemption.
* Generates clear documentation for internal assembly review.

---

## Quickstart

```bash
git clone https://github.com/pablomorenoc96/coop-executive.git
cd coop-executive/packages/core

# Install dependencies with uv:
uv sync --all-groups --extra dev

# Configure environment variables:
cp ../../.env.example .env

# Evaluate a grant opportunity with the 100-point rubric:
uv run coopexecutive evaluar "Clean_Energy_Grant_Call.txt"

# Generate a complete multilateral proposal dossier:
uv run coopexecutive dossier "Community Clean Microgrids" --donante "IDB"

# Register and vote on a General Assembly motion (One Member = One Vote):
uv run coopexecutive propuesta "IDB Clean Energy Proposal Approval" -d "Approval of technical matching commitment"
uv run coopexecutive votar 1 --socio-id "SOC-001" --socio-nombre "Elena Gomez" --voto "A_FAVOR"
uv run coopexecutive escrutinio 1 --padron 12

# Open the interactive Web Dashboard:
uv run coopexecutive dashboard

# Start an interactive session with the collegiate board:
uv run coopexecutive chat
```

---

## AI Model Setup (Free, Local, and Paid Options)

Copy `.env.example` to `.env` in your user folder (`%APPDATA%\CoopExecutive` or `~/.config/coopexecutive`), the repository root or the folder you run from; `coopexecutive info` shows which files were loaded. Model names below were checked on 29/09/2026 and change often: any compatible model works, and `coopexecutive modelos --herramientas` lists the free ones available today.

| Tier | Provider | Variables | Suggested models | Privacy |
|---|---|---|---|---|
| Free cloud | [OpenRouter](https://openrouter.ai/keys) | `OPENROUTER_API_KEY`, `DEFAULT_MODEL` | `google/gemma-4-31b-it:free` (default), `nvidia/nemotron-3-super-120b-a12b:free` (fallback), `qwen/qwen3.8-27b:free` | Daily limits; free providers may train on your data |
| Local and private | [Ollama](https://ollama.com/) | `LOCAL_MODELS_ENABLED=true`, `LOCAL_MODELS` (first is primary, the rest fallbacks) | `granite4.1:8b`, `granite4.1:3b` (low memory), `qwen3.8:27b`, `nemotron3:33b` (24 GB GPU) | Nothing leaves your computer |
| Paid | OpenAI | `OPENAI_API_KEY` | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna` | Provider terms |
| Paid | Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-4-5` | Provider terms |
| Paid | Google Gemini | `GEMINI_API_KEY` | `gemini-3.8-flash`, `gemini-3.5-flash-lite` | Provider terms |
| Paid | Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile`, `openai/gpt-oss-120b` | Provider terms |
| Paid | Mistral | `MISTRAL_API_KEY` | `mistral-medium-3-5-26-04`, `mistral-small-4-0-26-03` | Provider terms |
| Paid | DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-flash`, `deepseek-v4-pro` | Provider terms |
| Any | OpenAI-compatible (Azure, vLLM, LiteLLM, LM Studio) | `CUSTOM_BASE_URL`, `CUSTOM_API_KEY` | The one you host | Yours |

With `PROVIDER=auto` the first key present is used. Rate limits (429), server errors and dropped connections are retried up to `MAX_REINTENTOS` times with backoff before moving to the fallback model.
---

## Technical Documentation
* [Architecture & Data Flow Specification](ARCHITECTURE.md)
* [Social Economy & Governance Principles](docs/PRINCIPIOS_ECONOMIA_SOCIAL.en.md) | [🇲🇽 Español](docs/PRINCIPIOS_ECONOMIA_SOCIAL.md)
* [Logical Framework Practical Guide](docs/GUIA_MARCO_LOGICO.md)
* [Statutory Funds & Cooperative Governance Guide](docs/GUIA_FONDOS_ESTATUTARIOS.md)
* [Contributing Guide](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)

---

## License
Distributed under the [MIT](LICENSE) License. Free for open use and community ownership.
