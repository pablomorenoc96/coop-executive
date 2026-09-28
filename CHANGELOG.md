# Changelog

All notable changes to **CoopExecutive** will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-09-27

### Added
- **Terminal intro:** running `coopexecutive` without a command shows the organisation's intro (logo and name drawn with quadrant blocks) or the built-in CoopExecutive one. `coopexecutive intro generar` builds `intro.txt` from the optional `identidad` profile block (short name, motto, logo, font, colours). Generating requires the optional `identidad` extra (Pillow); showing it does not.
- **Word documents (`documento solicitud|institucional|ficha`):** application, institutional document and opportunity sheet built from the profile, the case and the latest evaluation. Missing data stays as `[PENDIENTE: …]`; the files never include internal tensions or the draft notice. The content is shown for confirmation before saving. Files go to `salidas/YYYY/EXP-…/` in the workspace, are never overwritten and are logged in the case (`expedientes ver` lists them).
- **Letterhead per organisation:** the `procuracion.membrete` block sets the header image, footer text, font and size. Default format: Arial 11, 1.15 line spacing, 6 pt after, justified text and tables at page width.
- **Opportunity monitoring (`monitorear`):** reads the public RSS/Atom feeds of the built-in sources (`knowledge/builtin/procuracion_fondos/fuentes.yaml`) and of the workspace's own `fuentes.yaml`, filters by the profile's focus areas (Spanish topics also match English notices), extracts the closing date only when it follows a closing keyword, and applies the matrix deadline rules. Output: up to 3 prioritised notices, notices to review and closed ones; a notice without an explicit date is marked `VIGENCIA NO VERIFICADA`. Notices published more than 120 days ago are skipped. Sources without a feed are listed for manual review.
- Monitoring privacy: only requests to public feeds leave the machine and, if a SearXNG instance is configured in `fuentes.yaml` (`buscador`), the topics. No profile or funder data is sent. Downloads are cached for 12 hours in the workspace `.cache/` folder; if a source fails, the cached copy is used and flagged.
- **`evaluar-convocatoria --proponer-asamblea`:** when the decision is APLICAR and the organisation has an assembly, opens a `subvencion` proposal that cites the case folio and the evaluation hash. Without an assembly, it names the profile's approvers (or `[PENDIENTE: aprobadores]`).
- Database migration 2 adds the `documentos` table.

### Changed
- New dependency: `python-docx` (MIT).

---

## [0.2.1] - 2026-09-27

### Fixed
- Non-cooperative profiles no longer inherit the cooperative default regime ("Economía Social y Solidaria"). When `regime` is not declared, the tax status from `configurar` is used, or `[PENDIENTE: régimen]`.

---

## [0.2.0] - 2026-09-27

### Added
- **Workspaces:** `--espacio` (or `COOPEXECUTIVE_WORKSPACE`) points to a folder with `profile.yaml`, `coop_memory.db` and `salidas/`. `coopexecutive iniciar` creates it without overwriting an existing profile. Explicit `COMPANY_PROFILE_PATH` and `EPISODIC_DB_PATH` keep priority, and without a workspace everything works as before.
- **Organisation types:** `tipo_organizacion` (cooperativa, asociacion_civil, empresa, persona_fisica), inferred from the legal structure when absent. Statutory funds and the one-member-one-vote assembly apply only to cooperatives; other organisations get a general advisory persona. New fictitious template `company/templates/persona_fisica_empresarial.yaml`.
- **Procurement profile:** optional `procuracion` block (short name, legal and tax status, territory, programmes, impact metrics, alliances, past funders, budget range, base currency, payment channels, approvers, letterhead). Missing data is shown as `[PENDIENTE: …]`.
- **`coopexecutive configurar`:** ten guided questions or `--desde answers.yaml`; shows a summary, rejects RFC/CURP identifiers and backs up the previous profile as `profile.yaml.bak-YYYYMMDD-HHMMSS`.
- **Deterministic matrix (`grant_tools.matrix`):** 8 criteria with required evidence; empty criteria stay pending instead of counting as zero; deadline bands; decision precedence; counterpoint; next step; SHA-256 hash. Results are stored in `grant_evaluations`, which was never written before.
- **`evaluar-convocatoria`** now runs the matrix in three modes: interactive, `--archivo` YAML and assisted (the model proposes scores as JSON, you confirm, the matrix decides and the model drafts the analysis). `--expediente` links the evaluation to a case.
- **Funders (`financiadores registrar|buscar|ver|actualizar`)** with `FIN-YYYY-NNNN` folios, catalogues, normalised duplicate detection and amounts in any ISO 4217 currency.
- **Cases (`expedientes abrir|avance|ver|listar`)** with `EXP-YYYY-NNNN` folios, one open case per entity and type, a progress log with data origin and linked evaluations.
- **Post-generation review (`guardrails`):** flags unsupported amounts and dates, emojis, answers over 900 words, recommendations without a counterpoint and claims of actions that were not executed. `ask --estricto` replaces unsupported amounts and dates with placeholders.
- The system prompt includes today's date in the organisation's time zone.
- Fictitious examples in `company/examples/` for `configurar --desde` and `evaluar-convocatoria --archivo`.

### Changed
- **BREAKING — `evaluar-convocatoria`:** the previous LLM-only command is replaced by the matrix. Passing a text or file with the call's rules starts the assisted mode; URLs are not downloaded.
- The grant procurement prompt was rewritten (under 8,000 characters) around evidence, placeholders and the matrix decision.
- The database schema is versioned with `PRAGMA user_version`; migrations add the `financiadores`, `expedientes` and `avances` tables and three columns to `grant_evaluations`.
- `eligibility_evaluator` takes its weights and thresholds from the matrix module.

---

## [0.1.1] - 2026-09-27

### Changed
- **BREAKING — Budget Builder:** `BudgetItem` fields `unit_cost_usd`, `requested_amount_usd` and `matching_amount_usd` are renamed to `unit_cost`, `requested_amount` and `matching_amount` (and `total_cost_usd` to `total_cost`). Amounts are expressed in the budget currency, which must be a valid ISO 4217 code; no conversion is performed. Amounts are now rendered as `57,000.00 USD` instead of `$57,000.00`.
- **Proposal Dossier:** sections the user does not provide are marked `[PENDIENTE: …]` instead of being filled with generic claims (such as a fixed self-sufficiency month or a quarterly audit).
- **Voting:** the assembly minutes timestamp uses the organisation's time zone (`USER_TIMEZONE`).
- **Association template:** `company/templates/asociacion_civil.yaml` now describes a fictitious organisation.

### Added
- `coopexecutive.utils`: `ahora_local()`, `hoy_local()`, `fecha_larga()` (locale-independent Spanish dates) and ISO 4217 validation and formatting.
- `comunicacion` specialist role for `ask --rol` (the communication prompt was previously unreachable).
- Organisation profiles keep `target_communities`, `focus_areas` and `funding_sources`, which were silently dropped when loading YAML.
- CLI tests for `info`, `propuesta`, `propuestas`, `votar` and `escrutinio`.

### Fixed
- `propuestas` crashed because `Table` was not imported.
- `propuestas` showed the creation date in UTC (SQLite `CURRENT_TIMESTAMP`); it is now shown in the organisation's time zone, and the category and status columns are no longer truncated at 80 columns.

---

## [0.1.0] - 2026-09-02

### Added
- **Core Orchestrator:** Collegiate Executive Director AI based on the 7 Universal Cooperative Principles.
- **Grant Procurement Agent:** Specialised agent for evaluating calls (FundsforNGOs, bilateral donors) using an 8-dimension, 100-point rubric.
- **Logical Framework Engine:** Automated 4x4 matrix, Problem Tree, Objective Tree, and Theory of Change generator aligned with UN SDGs.
- **Budget Builder:** Auditable grant budget builder distinguishing CAPEX, OPEX, technical personnel, and matching funds.
- **Statutory Funds Shielding:** Built-in calculation and protection for Reserve (15%), Social Welfare (10%), and Education (10%) funds according to cooperative law.
- **Multi-Provider Resilience:** Support for free OpenRouter models (`minimax-m3:free`, `nemotron:free`) with automatic 429 rate-limit fallback, and full offline support via Ollama.
- **Modular CLI:** Interactive `chat`, single-query `ask`, `evaluar-convocatoria`, `marco-logico`, and `info` commands.
- **Institutional Open-Source Documentation:** Comprehensive English/Spanish READMEs, Architecture, Contributing guide, and Manifestos.
