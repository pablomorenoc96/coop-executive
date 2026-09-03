# CoopExecutive

![CoopExecutive Banner](assets/banner_en.png)

> **Collegiate Executive Board & Grant Procurement AI Agent for Cooperatives, Civil Associations (Non-Profits / NGOs), and the Social Economy.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml/badge.svg)](https://github.com/pablomorenoc96/coop-executive/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](https://www.python.org/)
[![Free & Paid AI](https://img.shields.io/badge/Models-Free%20%26%20Commercial-orange.svg)](#ai-model-setup-free-local-and-paid-options)
[![Social Economy Manifesto](https://img.shields.io/badge/Philosophy-Social%20Economy-darkgreen.svg)](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)

[🇲🇽 Leer en Español](README.es.md) | [📢 Social Media & Outreach Kit](docs/KIT_DIFUSION_REDES.md)

**CoopExecutive** is an open-source alternative to the traditional corporate management model. While conventional Silicon Valley AI tools assume private equity, shareholder primacy, and venture capital, this system is engineered for **democratic organizations**: sovereign assemblies, collective statutory reserves, and non-profit public impact.

---

## What is CoopExecutive Technically?

In software and AI engineering terms, **CoopExecutive is not a simple chatbot or passive text generator**: it is an **Autonomous Vertical AI Agent** built on five formal architectural pillars:

```
                   ┌────────────────────────────────────────────────────────┐
                   │                     ENVIRONMENT (World)                │
                   │  (profile.yaml, LGSC Law, Multilateral Grants, CLI/Web)│
                   └───────────────▲────────────────────────┬───────────────┘
                                   │                        │
                          Perception (Sensors)         Action (Actuators)
                                   │                        │
       ┌───────────────────────────┴────────────────────────▼───────────────────────────┐
       │                            CoopExecutive AGENT                                 │
       │                                                                                │
       │   ┌────────────────────────────────────────────────────────────────────────┐   │
       │   │                    COLLEGIATE EXECUTIVE ORCHESTRATOR                   │   │
       │   │   (Role Router: Procurement, Vigilance, Legal, Finance, Assembly)      │   │
       │   └──────┬───────────────────────┬──────────────────────────┬──────────────┘   │
       │          │                       │                          │                  │
       │   ┌──────▼──────┐         ┌──────▼──────┐            ┌──────▼──────┐           │
       │   │  EPISODIC   │         │  UNIVERSAL  │            │   EXECUTION │           │
       │   │   MEMORY    │         │  INFERENCE  │            │  TOOL-USE   │           │
       │   │  (SQLite)   │         │  (Resilient │            │             │           │
       │   │ - Assembly  │         │   Fallback) │            │ - 4x4 MML   │           │
       │   │ - Ballots   │         │             │            │ - 100pt Rub.│           │
       │   │ - Dossiers  │         │             │            │ - Budgeting │           │
       │   └─────────────┘         └─────────────┘            └─────────────┘           │
       │                                                                                │
       │   ┌────────────────────────────────────────────────────────────────────────┐   │
       │   │                   HARD STATUTORY GUARDRAILS & INVARIANTS               │   │
       │   │      Cooperative Law: 15% Reserve, 10% Welfare, 0% Equity Dilution     │   │
       │   └────────────────────────────────────────────────────────────────────────┘   │
       └────────────────────────────────────────────────────────────────────────────────┘
```

1. **Perception:** Inspects institutional state (`company/profile.yaml`), parses statutory laws, and ingests multilateral grant guidelines in real-time.
2. **Action Space & Tool-Use:** Executes deterministic code: builds auditable budgets with matching funds, computes 4x4 Logical Frameworks, and compiles official proposal dossiers.
3. **Episodic & Persistent Memory:** Relational SQLite database (`coop_memory.db`) storing assembly agreements, grant evaluations, and voting ballots across sessions.
4. **Deliberation & Autonomous Reasoning:** Applies an 8-dimension 100-point multicriteria rubric to issue binding strategic verdicts (`APPLY`, `EXPLORE`, `REJECT`).
5. **Hard Statutory Guardrails (Invariants):** Code-enforced legal protections: preserves mandatory collective funds (15% Reserve, 10% Welfare, 10% Education) and vetoes capital dilution attempts.

---

## The Antithesis: Silicon Valley vs. CoopExecutive

| Dimension | Silicon Valley Approach | CoopExecutive (Social Economy) |
| :--- | :--- | :--- |
| **Decision Power** | Weighted by capital (*one dollar, one vote*). | Democratic (*one member, one vote* — General Assembly). |
| **Oversight** | Private board of directors representing venture funds. | Independent **Vigilance Board** elected by members. |
| **Financing** | Debt, capital dilution, and exit orientation (*liquidity events*). | Sustainable operation + **Non-reimbursable grants ([FundsforNGOs](https://www.fundsforngos.org/))**. |
| **Surplus** | Maximizing dividend distributions to investors. | **Protected Statutory Funds:** Reserve (15%), Welfare (10%), Education (10%). |
| **Legal Regime** | For-profit corporations (Delaware C-Corp, S.A. de C.V.). | Cooperative Societies (LGSC) and Civil Associations (NGOs). |
| **Infrastructure** | Proprietary SaaS with expensive subscription lock-in. | **100% Open Source (MIT), free ($0.00) models and optional commercial APIs.** |

---

## Visual Demo

![CoopExecutive Demo](assets/demo_en.gif)

---

## Core Capabilities

### 1. Multilateral Grant Procurement Agent
* **100-Point Evaluation Rubric:** Automatically evaluates funding opportunities across 8 weighted criteria (*APPLY*, *EXPLORE*, *CONDITIONAL*, or *DO NOT APPLY*).
* **Logical Framework Methodology (LFM / RBM):** Automatically generates Problem Trees, Objective Trees, and 4x4 Result Matrices.
* **Theory of Change (ToC):** Aligns project activities directly with UN Sustainable Development Goals (SDGs 7, 8, 9, 12, 13).
* **Multilateral Proposal Dossier Generator:** Compiles audit-ready technical dossiers for the Inter-American Development Bank (IDB), Horizon Europe, and international foundations.

### 2. Democratic Assembly Voting System (One Member = One Vote)
* **Sovereign Ballot Casting:** Credentials members, prevents duplicate voting, and records official choices (`A_FAVOR`, `EN_CONTRA`, `ABSTENCION`).
* **Live Quorum Calculation:** Enforces statutory minimum attendance (50% + 1 members) under cooperative law.
* **Cryptographic Scrutiny Certificate:** Issues formal Assembly Minutes with verification SHA-256 hashes.
* **Anti-Dilution Statutory Veto:** Automatically rejects and nullifies any motion aiming to privatize collective funds or sell cooperative shares.

### 3. Collegiate Executive & Vigilance Board
* **Vigilance Board:** Internal democratic audit, ethical compliance, and conflict-of-interest prevention.
* **Social Legal Counsel:** Cooperative legal framework, authorized donee compliance, and open-technology licensing.
* **Solidarity Finance:** Manages and shields mandatory statutory funds (Reserve, Social Welfare, Cooperative Education).
* **Assembly Secretariat:** Drafts agendas, records accredited rolls, and certfies assembly resolutions.

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

CoopExecutive is a sovereign multi-provider AI engine supporting three flexible execution routes:
1. **Free Cloud Tier ($0.00):** Add a free API key from [OpenRouter](https://openrouter.ai/keys) to `.env` (no credit card required). Access high-performance free models like `minimax/minimax-m3:free` and `nvidia/nemotron-3-super-120b-a12b:free` with automatic 429 rate-limit fallback.
2. **Local Offline Tier (100% Private & Free):** Set `LOCAL_MODELS_ENABLED=true` in `.env` to execute completely offline via [Ollama](https://ollama.com/) with models like `llama3.1` or `qwen2.5`.
3. **Commercial & Paid APIs (Optional):** If your cooperative or non-profit has commercial accounts or institutional credits, you can directly configure API keys for **OpenAI** (`gpt-4o`, `o1`, `o3-mini`), **Anthropic** (`claude-3-7-sonnet`, `claude-3-5-sonnet`), **Google Gemini** (`gemini-2.0-flash`), **Groq**, **Mistral**, **DeepSeek**, or custom OpenAI-compatible enterprise gateways (`vLLM`, `Azure OpenAI`). The engine automatically routes requests based on the selected model and active keys.

---

## Documentation
* [Architecture & Resilience Design](ARCHITECTURE.md)
* [Social Economy Manifesto](docs/MANIFIESTO_ECONOMIA_SOCIAL.md)
* [Logical Framework Practical Guide](docs/GUIA_MARCO_LOGICO.md)
* [Statutory Funds & Cooperative Governance Guide](docs/GUIA_FONDOS_ESTATUTARIOS.md)
* [Contributing Guide](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)

---

## License
Distributed under the [MIT](LICENSE) License. Free for community use, modification, and collective ownership.
