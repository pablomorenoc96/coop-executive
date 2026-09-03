# CoopExecutive Architecture & Design Philosophy

CoopExecutive is a modular, open-source AI platform designed to empower cooperatives, civil associations (A.C. / NGOs), and social economy organizations.

---

## High-Level Architecture

```
                                  [ CLI / API Layer ]
                                          │
                                          ▼
                         [ CoopExecutive Orchestrator ]
                                          │
                   ┌──────────────────────┼──────────────────────┐
                   │                      │                      │
                   ▼                      ▼                      ▼
         [ Cooperative Persona ]   [ Social Council ]    [ Grant Tools ]
         - 7 Coop Principles       - Vigilance Board     - 100-pt Rubric
         - Assembly Sovereignty    - Legal / Statutory   - 4x4 LogFrame
         - Statutory Funds         - Solidarity Finance  - Budget Builder
                                          │
                                          ▼
                               [ Multi-Provider Engine ]
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    ▼                                           ▼
         [ OpenRouter :free Tier ]                      [ Local Ollama ]
         - Minimax M3 (Default)                         - LLaMA 3.1 / Qwen
         - Nemotron 120B (Fallback)                     - 100% Offline
```

---

## Key Modules

### 1. Grant Procurement Engine (`coopexecutive.grant_tools`)
* **`eligibility_evaluator.py`:** Evaluates funding opportunities across 8 weighted dimensions:
  1. Mission Alignment (0-20)
  2. Geographic & Legal Eligibility (0-10)
  3. Budget Range (0-15)
  4. Timeline Feasibility (0-10)
  5. Technical & Operational Capacity (0-15)
  6. Measurable Social/Environmental Impact (0-15)
  7. Long-term Strategic Value (0-10)
  8. Reporting & Audit Manageability (0-5)
  Outputs a clear decision: `APLICAR`, `EXPLORAR`, `CONDICIONAL`, or `NO APLICAR`.
* **`logical_framework.py`:** Produces a complete 4x4 Logical Framework Matrix (Goal, Purpose, Outputs, Activities) with Objectively Verifiable Indicators (OVIs), Means of Verification, and Critical Assumptions.
* **`budget_builder.py`:** Formats multi-currency budgets with strict separation of personnel, direct materials/CAPEX, operational expenses/OPEX, external audit, and institutional matching funds.

### 2. Collegiate Social Council (`coopexecutive.prompts.domain_prompts`)
Specialized agent personas reflecting collective governance:
* **Vigilance Board (*Consejo de Vigilancia*):** Democratic internal audit, ethical oversight, prevention of conflicts of interest.
* **Social Legal Counsel (*Asesor Jurídico Social*):** Cooperative societies law, non-profit tax exemptions (authorized donees), and open IP agreements.
* **Solidarity Finance (*Finanzas Solidarias*):** Statutory funds protection (Reserve, Welfare, Education) and transparent treasury.
* **Open Technology (*Desarrollo Tecnológico Comunitario*):** Open-source hardware, clean energy, and technical self-determination.
* **Social Communication (*Comunicación Social*):** Transparent outreach and inter-cooperative federation alliances.
* **Assembly Secretariat (*Secretaría de Actas*):** Quorum computation, agenda preparation, and formal minutes.

### 3. Resilient Ingestion & Provider Routing (`coopexecutive.providers`)
* **Zero-cost by default:** Uses open-weights models available on OpenRouter's `:free` endpoints.
* **Automatic 429 Rate-Limit Fallback:** If the primary upstream model is temporarily busy, the client automatically transparently switches to the deep reasoning fallback model (`nvidia/nemotron-3-super-120b-a12b:free`).
* **Air-gapped / Local Execution:** Pointing `LOCAL_MODELS_ENABLED=true` enables 100% offline private execution with Ollama.
