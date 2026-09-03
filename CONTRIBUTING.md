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

1. **Clone the repository:**
   ```bash
   git clone https://github.com/pablomorenoc96/coop-executive.git
   cd coop-executive/packages/core
   ```

2. **Run with `uv` (recommended):**
   ```bash
   # Show available CLI commands:
   uv run coopexecutive --help

   # Display current cooperative profile:
   uv run coopexecutive info
   ```

3. **Configure Environment:**
   ```bash
   cp ../../.env.example ../../.env
   ```
   Add your free OpenRouter API key (`sk-or-v1-...`) or enable `LOCAL_MODELS_ENABLED=true` for local Ollama.

---

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feat/your-feature-name`.
2. Commit your changes with descriptive messages: `git commit -m "feat(grants): add export to docx for logframe"`.
3. Push to your branch and open a Pull Request.
