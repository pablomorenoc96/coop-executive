# CoopExecutive Architecture & Autonomous Agent Specification

CoopExecutive is a modular, open-source AI platform designed to empower cooperatives, civil associations (A.C. / NGOs), and social economy organizations.

---

## 1. Why CoopExecutive is an Autonomous Vertical AI Agent

Unlike generic conversational interfaces (chatbots) that passively respond to textual prompts without state or operational agency, CoopExecutive is an **Autonomous Domain-Specific AI Agent (Vertical AI Agent)** characterized by five architectural layers:

```
                                [ ENVIRONMENT ]
             (profile.yaml, LGSC Law, Grant Guidelines, CLI & Web)
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
             Perception (Sensors)             Actuation (Effectors)
                     │                                 │
                     ▼                                 ▼
         ┌────────────────────────────────────────────────────────┐
         │                  CoopExecutive Agent                   │
         │                                                        │
         │  1. Perception:                                        │
         │     - Ingests institutional profile & statutory rules  │
         │     - Parses grant notices & funding requirements      │
         │                                                        │
         │  2. Collegiate Orchestrator (Reasoning):               │
         │     - Dynamic role routing (Procurement, Vigilance,    │
         │       Solidarity Finance, Legal, Assembly Secretariat) │
         │     - 100-Point Multicriteria Evaluation Engine        │
         │                                                        │
         │  3. Action Space (Deterministic Tool-Use):             │
         │     - 4x4 Logical Framework generator                  │
         │     - Auditable Budget & Matching Fund builder         │
         │     - Multilateral Proposal Dossier compiler           │
         │                                                        │
         │  4. Episodic & Persistent Memory:                      │
         │     - SQLite relational storage (coop_memory.db)       │
         │     - Assembly decisions, ballots, and grant records   │
         │                                                        │
         │  5. Hard Statutory Guardrails (Invariants):            │
         │     - 15% Reserve, 10% Welfare, 10% Education (LGSC)   │
         │     - Immediate programmatic veto on equity dilution   │
         └────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Subsystems

### A. Democratic Governance & Voting Engine (`coopexecutive.governance.voting`)
* **Principle: One Member = One Vote:** Enforces equality of voting rights regardless of capital contribution.
* **Proposal Lifecycle:** Proposals are created and validated against statutory invariants (blocking illegal motions like share selling or reserve fund liquidation).
* **Quorum Engine:** Computes real-time assembly attendance and evaluates whether statutory quorums (>50% + 1 members) are achieved pursuant to LGSC Articles 36–40.
* **Cryptographic Attestation:** Emits formal Assembly Minutes (*Actas de Escrutinio*) signed with SHA-256 digital hashes.

### B. Grant Procurement Engine (`coopexecutive.grant_tools`)
* **`eligibility_evaluator.py`:** Evaluates funding opportunities across 8 weighted dimensions (0–100 points) and produces formal binding verdicts (`APLICAR`, `EXPLORAR`, `CONDICIONAL`, or `NO APLICAR`).
* **`logical_framework.py`:** Produces a complete 4x4 Results-Based Management (RBM) matrix with Objectively Verifiable Indicators, Means of Verification, and Critical Assumptions aligned with UN SDGs.
* **`budget_builder.py`:** Enforces strict categorization of Personnel, CAPEX, OPEX, External Audit, and non-cash Institutional Matching Funds.
* **`dossier_generator.py`:** Generates comprehensive technical proposal dossiers ready for submission to international donors (IDB, Horizon Europe, multilateral funds).

### C. Collegiate Social Council (`coopexecutive.prompts.domain_prompts`)
Specialized agent personas reflecting collective governance:
* **Vigilance Board (*Consejo de Vigilancia*):** Democratic internal audit, ethical oversight, prevention of conflicts of interest.
* **Social Legal Counsel (*Asesor Jurídico Social*):** Cooperative societies law, non-profit tax exemptions (authorized donees), and open IP agreements.
* **Solidarity Finance (*Finanzas Solidarias*):** Statutory funds protection (Reserve, Welfare, Education) and transparent treasury.
* **Open Technology (*Desarrollo Tecnológico Comunitario*):** Open-source hardware, clean energy, and technical self-determination.
* **Assembly Secretariat (*Secretaría de Actas*):** Quorum computation, agenda preparation, and formal minutes.

### D. Universal Multi-Provider AI Client (`coopexecutive.providers.client`)
* **Zero-Cost Sovereign Cloud Route ($0.00):** Connects to OpenRouter free models (`minimax/minimax-m3:free`, `nvidia/nemotron:free`) with silent fallback upon 429 rate-limiting events.
* **Offline Local Route:** Operates 100% disconnected via local Ollama instances (`llama3.1`, `qwen2.5`).
* **Commercial Paid APIs (Optional):** Native routing for OpenAI, Anthropic, Google Gemini, Groq, Mistral, DeepSeek, and custom OpenAI-compatible enterprise endpoints.
