# Contributing to CoopExecutive

Thank you for your interest in contributing to **CoopExecutive**! This project aims to provide an open-source, vendor-independent AI-powered collegiate executive board and grant procurement agent for cooperatives, civil associations, and social enterprises.

---

## Code of Conduct & Core Invariants

CoopExecutive is explicitly built as an **antithesis to Silicon Valley's venture capital model**. When contributing, please uphold these core invariants:

1. **Democratic Governance Invariant:**
   * All governance logic strictly adheres to **One Member, One Vote** (General Assembly supremacy). Never introduce plutocratic voting schemes (e.g., voting power weighted by capital or equity).
2. **Statutory Funds Invariant:**
   * Respect mandatory cooperative statutory funds (Reserve Fund, Social Welfare Fund, Cooperative Education Fund).
3. **Open Access & Zero Vendor Lock-in:**
   * Code must remain compatible with free open-weights models (via OpenRouter `:free` tier or local Ollama). No features requiring mandatory paid subscriptions or proprietary platforms.
4. **Grant Procurement & Logical Framework:**
   * Keep grant evaluation algorithms and Logical Framework tools grounded in official multilateral standards (UN SDGs, Logical Framework Approach, auditable budgets).

---

## Development Setup

1. **Clone the repository and install everything:**
   ```bash
   git clone https://github.com/pablomorenoc96/coop-executive.git
   cd coop-executive/packages/core
   uv sync --all-extras --all-groups
   ```

2. **Configure a model (optional):**
   ```bash
   cp ../../.env.example ../../.env
   ```
   Add a free OpenRouter key or set `LOCAL_MODELS_ENABLED=true` for Ollama. `uv run coopexecutive info` shows which `.env` was loaded. Tests and evals never need a key or the network.

3. **Check your change before opening a pull request:**
   ```bash
   uv run --extra dev pytest -q                                # tests and evals
   uv run --extra dev ruff check coopexecutive tests evals     # lint
   uv run python -m coopexecutive.evals                        # golden cases summary
   ```

## Ground rules for code

- Anything that must be reproducible (scores, deadlines, quorum, budgets) is computed in code, not by the model.
- Never let the agent invent amounts, dates, partners or results: use `MONTO POR DEFINIR`, `COSTO POR COTIZAR`, `VIGENCIA NO VERIFICADA` or `[PENDIENTE: …]`.
- A new tool that writes data must set `escribe=True`, so it always asks for confirmation.
- New commands need a test, and any command you cite in the READMEs or `docs/GUIA_DE_USO*` must exist (`tests/test_docs.py` checks it).
- New dependencies must have a permissive license; heavy ones go in an optional extra.

---

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feat/your-feature-name`.
2. Commit with conventional messages: `git commit -m "feat(grants): add deadline filter to comparar-convocatorias"`.
3. Push to your branch and open a Pull Request.
