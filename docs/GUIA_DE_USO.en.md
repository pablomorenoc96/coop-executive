# CoopExecutive user guide

This guide walks through each area with examples you can copy. Commands and their options are in Spanish; the explanations are in English. The commands assume the package is installed (see the [README](../README.md#installation)) and that you have set your organisation's workspace:

```bash
export COOPEXECUTIVE_WORKSPACE=~/procurement/my-org
```

On Windows (PowerShell): `$env:COOPEXECUTIVE_WORKSPACE = "$HOME\procurement\my-org"`. You can also pass `--espacio PATH` before any command.

Contents:

1. [First steps](#1-first-steps)
2. [Organisation profile](#2-organisation-profile)
3. [Date and deadlines](#3-date-and-deadlines)
4. [Evaluating funding calls](#4-evaluating-funding-calls)
5. [Comparing funding calls](#5-comparing-funding-calls)
6. [Monitoring funding calls](#6-monitoring-funding-calls)
7. [Funders and cases](#7-funders-and-cases)
8. [Preparing meetings](#8-preparing-meetings)
9. [Drafting and Word documents](#9-drafting-and-word-documents)
10. [Project design](#10-project-design)
11. [Looking up information and reviewing sources](#11-looking-up-information-and-reviewing-sources)
12. [Assembly](#12-assembly)
13. [Chat with tools](#13-chat-with-tools)
14. [Local panel and API](#14-local-panel-and-api)
15. [MCP server](#15-mcp-server)
16. [Audit log](#16-audit-log)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. First steps

```bash
coopexecutive iniciar ~/procurement/my-org --nombre "My Organisation" --tipo asociacion_civil
coopexecutive info
```

`iniciar` creates the folder with a minimal profile (`profile.yaml`), the database and `salidas/`. Valid types are `cooperativa`, `asociacion_civil`, `empresa` and `persona_fisica`. Only cooperatives have statutory funds and a one-member-one-vote assembly.

`info` shows the active organisation, the provider and model, and which `.env` files were loaded. You can start without a model key: the matrix, deadlines, cases, Word documents, the assembly and the audit log all work without a model.

## 2. Organisation profile

### From the website

```bash
coopexecutive configurar --sitio https://www.example.org/
```

The agent reads the home page and up to six pages on the same domain that usually carry institutional data (about, contact, programmes, join, transparency). It respects robots.txt and caps the size of each page. Before proposing anything it strips bank accounts, tax IDs, national IDs, personal emails and phone numbers.

For each of the ten questions it shows the proposal, the evidence and the URL it came from:

- «sí» accepts the proposal;
- any other text replaces it;
- Enter keeps the current value, or leaves it pending if it was empty.

If the site does not say something, the question appears as «Pendiente» and you can type the answer.

### By hand

```bash
coopexecutive configurar
```

Ten questions: name and acronym, legal form, mission, population and territory, programmes and work areas, metrics, legal and tax status, amount range and currency, partners and previous funders, and who approves and how funds are received. If an answer is «está en nuestro sitio» ("it's on our website"), the agent asks for the link once and reads it only for that question.

### From a file

```bash
coopexecutive configurar --desde company/examples/respuestas_perfil.yaml
```

The example file holds fictitious data. Leave blank whatever you do not know: it becomes `[PENDIENTE]`. Do not include tax IDs, national IDs, addresses or bank accounts.

In all three modes the previous profile is backed up (`profile.yaml.bak-…`) before writing, and `procuracion.origenes` records where each field came from.

### Letterhead and identity

In `profile.yaml`, the `procuracion.membrete` block sets the letterhead of the Word files:

```yaml
procuracion:
  membrete:
    imagen: membrete.png   # header image, relative to the profile folder
    pie: "www.example.org"
    fuente: Arial
    tamano: 11
```

The `identidad` block (short name, tagline, logo, font and colours) feeds the terminal intro: `coopexecutive intro generar` draws it and needs the `identidad` extra.

In cooperatives, `governance.mayoria` can be `simple` or `dos_tercios`; the tally applies that rule and the minutes cite it.

## 3. Date and deadlines

```bash
coopexecutive fecha
coopexecutive fecha --cierre 2026-10-09 --cierre "30 de octubre de 2026" --cierre 15/11/2026
```

Shows today's date in the `USER_TIMEZONE` zone and, for each deadline, the weekday, the calendar days left and the deadline text: «Faltan N días», «(URGENTE)» at 13 days or fewer, «Cierra hoy» or «Vencida». The matrix uses the same rule.

## 4. Evaluating funding calls

The matrix has eight criteria that add up to 100 points:

| Criterion | Weight |
|---|---|
| Mission alignment | 20 |
| Geographic and legal eligibility | 10 |
| Suitable budget range | 15 |
| Timeline and delivery feasibility | 10 |
| Technical and operational capacity | 15 |
| Measurable impact potential | 15 |
| Long-term strategic value | 10 |
| Audit and reporting requirements | 5 |

Each score needs evidence. An empty criterion stays pending and does not count as zero. Timeline points must match the days left: fewer than 7 days allows 0 to 2 points; 7 to 13, 3 to 5; 14 to 28, 6 to 8; more than 28, 9 to 10.

The decision comes from the first rule that holds:

| Order | Condition | Decision |
|---|---|---|
| 1 | Data that breaks the rules (score out of range, no evidence) | `ERROR_VALIDACION` |
| 2 | Excluded eligibility or deadline passed | `DESCARTAR` |
| 3 | Eligibility pending | `VERIFICAR_ELEGIBILIDAD` |
| 4 | Validity pending | `VERIFICAR_VIGENCIA` |
| 5 | Clash with a public position of the organisation | `ESCALAR_DIRECCION` |
| 6 | Some criterion not scored | `EVALUACION_INCOMPLETA` |
| 7 | 80 points or more | `APLICAR` |
| 8 | 60 to 79 | `EXPLORAR` |
| 9 | 40 to 59 | `CONDICIONAL` |
| 10 | Below 40 | `DESCARTAR` |

A pending tension lowers APLICAR or EXPLORAR to CONDICIONAL. Each result includes a counterpoint (the strongest or weakest criterion), the next step and a SHA-256 hash of the input and the result.

There are four ways to provide the input:

```bash
# 1. Questions in the terminal
coopexecutive evaluar-convocatoria

# 2. A YAML file with scores and evidence (no model)
coopexecutive evaluar-convocatoria --archivo company/examples/convocatoria_ejemplo.yaml

# 3. The call documents as URL, PDF, Word or HTML: the model proposes scores with evidence
coopexecutive evaluar-convocatoria https://example.org/call.pdf --expediente EXP-2026-0001

# 4. The call documents as pasted text
coopexecutive evaluar-convocatoria --asistido "Text of the call…"
```

In modes 3 and 4 the model only proposes. The proposal is validated with pydantic, you confirm or correct it (`--si` accepts it without asking), the matrix decides, and then the model drafts the analysis, which goes through the strict review.

Useful options:

- `--no-guardar`: shows the result without saving it.
- `--expediente EXP-…`: links the evaluation to a case.
- `--proponer-asamblea`: if the decision is APLICAR, creates a proposal of category `subvencion` that cites the folio and the hash. In organisations without an assembly it refers to their approvers.

## 5. Comparing funding calls

```bash
coopexecutive comparar-convocatorias                      # the ten most recent evaluations
coopexecutive comparar-convocatorias 1 2 --orden puntaje  # by identifier
coopexecutive comparar-convocatorias --expediente EXP-2026-0001 --word
```

The table shows decision, score, amount, deadline and next step, and ends with which one to handle first: the most urgent among those worth preparing (`--orden plazo`, the default) or the highest score (`--orden puntaje`). With `--word` it saves the report.

## 6. Monitoring funding calls

```bash
coopexecutive monitorear
coopexecutive monitorear --tema "energía renovable" --tema "formación técnica"
coopexecutive monitorear --sin-cache --todas
```

Reads the public RSS/Atom feeds of the built-in sources and of your `fuentes.yaml`. Topics come from the profile's work areas, or from `--tema`. A notice is kept only if it contains every significant word of at least one topic. A closing date is accepted only when it follows a closing keyword; otherwise the notice is marked `VIGENCIA NO VERIFICADA`.

To add your own sources, create `fuentes.yaml` in the workspace:

```yaml
fuentes:
  - nombre: State funding portal
    tipo: Gobierno
    region: México
    idioma: es
    url: https://convocatorias.example.gob.mx/
    rss: https://convocatorias.example.gob.mx/feed/
temas: ["energía comunitaria"]
solo_propias: false
```

A source without `rss` is listed for manual review. Downloads are cached for 12 hours in `.cache/`. Each run is stored in the database and shown in the panel. `documento reporte-monitoreo` saves the result as Word.

## 7. Funders and cases

```bash
coopexecutive financiadores registrar "Example Foundation" --proyecto "Community microgrids" \
  --tipo "Fundación" --canal "Correo" --moneda USD --contacto "Programme officer"
coopexecutive financiadores buscar example
coopexecutive financiadores ver FIN-2026-0001
coopexecutive financiadores actualizar FIN-2026-0001 --seguimiento 2026-10-15

coopexecutive expedientes abrir "Example Foundation" --tipo Convocatoria --fecha-limite 2026-11-08
coopexecutive expedientes avance EXP-2026-0001 --estado "Concept note sent" \
  --siguiente "Call the programme officer" --origen "Dato del usuario"
coopexecutive expedientes listar
coopexecutive expedientes ver EXP-2026-0001
```

Funders get a `FIN-YYYY-NNNN` folio and duplicates are detected by normalised name. Cases get `EXP-YYYY-NNNN`; only one can be open per entity and type. Without `--monto`, the case shows `MONTO POR DEFINIR`. Each progress entry records its source, and `--cerrar` closes the case.

## 8. Preparing meetings

```bash
coopexecutive reunion preparar "Example Foundation" --sitio https://foundation.example.org/ \
  --expediente EXP-2026-0001 --objetivo "Present the project and learn their funding cycle" --word
```

Reads the site's home page and up to three more pages. Returns the entity's public profile (only from what was read), your organisation's fact sheet, common ground, risks, an agenda and questions. Each item carries its source label; whatever could not be confirmed is marked `NO VERIFICADO` or `PENDIENTE`.

## 9. Drafting and Word documents

### Drafts for third parties

```bash
coopexecutive redactar carta-intencion --expediente EXP-2026-0001
coopexecutive redactar propuesta --expediente EXP-2026-0001 --bases https://example.org/call.pdf --word
coopexecutive redactar correo-seguimiento --expediente EXP-2026-0001 --indicaciones "Thank them for Tuesday's call"
```

Types: `propuesta`, `carta-intencion`, `nota-conceptual`, `justificacion` and `correo-seguimiento`. The text uses only the profile, the case and the call documents. Before it is shown, unsupported amounts and dates are replaced with markers and bank accounts are censored. With `--word` it is saved with your letterhead.

### Word documents

```bash
coopexecutive documento solicitud --expediente EXP-2026-0001
coopexecutive documento institucional
coopexecutive documento ficha --expediente EXP-2026-0001
coopexecutive documento carta-intencion --expediente EXP-2026-0001
coopexecutive documento nota-conceptual --expediente EXP-2026-0001
coopexecutive documento reporte-evaluacion
coopexecutive documento reporte-monitoreo
```

They are built from the profile, the case and the evaluation, without a model. Anything missing becomes `[PENDIENTE: …]`. You see the content before it is saved (`--si` saves without asking). Files go to `salidas/YYYY/EXP-…/`, are never overwritten and are recorded in their case.

## 10. Project design

```bash
coopexecutive proyecto marco-logico "Community microgrids" --plantilla   # copy the template to marco.yaml
coopexecutive proyecto marco-logico "Community microgrids" --desde marco.yaml -o marco.md
coopexecutive proyecto presupuesto "Community microgrids" --desde presupuesto.yaml --tope-indirectos 10
coopexecutive proyecto dossier "Community microgrids" --expediente EXP-2026-0001 --marco marco.yaml --presupuesto presupuesto.yaml
```

- **Logical framework:** goal, purpose, components and activities, with indicators, means of verification and assumptions. With `--asistido`, the model proposes the structure and it is validated. Anything missing, such as SDG alignment, stays pending.
- **Budget:** line items with requested amount and co-funding. An item without a cost appears as `COSTO POR COTIZAR` and the total as `MONTO POR DEFINIR`. Indirect costs are computed only if you pass `--tope-indirectos`.
- **Dossier:** brings the above together with the funder and call of the case. Statutory funds only appear for cooperatives.

`-o file.md` saves the result without overwriting. The short names `marco-logico`, `presupuesto` and `dossier` still work.

## 11. Looking up information and reviewing sources

```bash
coopexecutive consultar "¿cuál es nuestra figura jurídica?"
coopexecutive consultar "¿qué programas tenemos?" --redactar
coopexecutive revisar https://example.org/call.pdf --pregunta "who can apply?"
coopexecutive revisar report.docx --sin-modelo --pregunta "indicators"
```

`consultar` searches the profile, the workspace's `conocimiento/` folder (md, txt, html, docx and pdf) and the built-in guides. Without `--redactar` it uses neither the model nor the network: it shows the passages with their source. If nothing matches, it answers «No consta en el perfil ni en los documentos de conocimiento» ("not in the profile or the knowledge documents").

`revisar` summarises a page or a file and cites the source. With `--sin-modelo` it shows the fragments most relevant to the question.

## 12. Assembly

Cooperatives only.

```bash
coopexecutive socios alta SOC-001 -n "Member one"
coopexecutive socios alta SOC-002 -n "Member two"
coopexecutive socios listar

coopexecutive propuesta "Apply to the energy fund" -d "Approve the application and its co-funding" -c subvencion
coopexecutive propuestas
coopexecutive votar 1 -s SOC-001 -v a_favor -j "Matches the annual plan"
coopexecutive votar 1 -s SOC-002 -v abstencion
coopexecutive escrutinio 1
```

Each member votes once per proposal. `escrutinio` takes the roll of active members (or `--padron N`), checks the quorum of more than half, applies the profile's majority rule, closes the proposal as approved or rejected and issues minutes with a SHA-256 hash. Proposals that sell equity, distribute statutory funds or impose unpaid work are rejected.

## 13. Chat with tools

```bash
coopexecutive chat
coopexecutive chat --rol finanzas --solo-lectura
coopexecutive ask "¿Qué expedientes vencen este mes?"
coopexecutive ask "Registra a la Fundación Ejemplo como financiador" --estricto
```

Roles: `procurador`, `vigilancia`, `legal`, `finanzas`, `tecnico`, `comunicacion` and `asamblea`.

The model can use 19 tools (the same as in the panel and the MCP server). The 14 read tools run directly. The 5 write tools (register funder, open case, record progress, save evaluation and generate document) show what they are about to do and wait for your confirmation. If you say no, the model is told, and the post-generation review blocks phrases such as "I've registered it".

`--solo-lectura` offers only the read tools; `--sin-herramientas` only chats.

## 14. Local panel and API

```bash
coopexecutive panel
```

Opens the browser at `http://127.0.0.1:8765/#token=…`. The token changes on every start. The panel chat asks for confirmation in a dialog before any write; the «Solo consultas» checkbox limits the chat to read tools.

API example from another terminal (replace the token):

```bash
TOKEN=the-token-shown-in-the-terminal
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/api/expedientes
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"argumentos": {"cierres": ["2026-10-09"]}}' http://127.0.0.1:8765/api/herramientas/fecha_y_plazos
```

For a write tool, the first call returns 409 with a summary of what it would do; repeat it with `"confirmar": true` in the body.

## 15. MCP server

```bash
coopexecutive mcp               # all tools
coopexecutive mcp --solo-lectura
```

Configure your client with the command `coopexecutive`, the argument `mcp` and the `COOPEXECUTIVE_WORKSPACE` variable. The README has the example for Claude Desktop and Claude Code. The server writes only protocol messages to stdout; logs go to stderr.

## 16. Audit log

```bash
coopexecutive bitacora ver
coopexecutive bitacora verificar
coopexecutive bitacora exportar bitacora.jsonl
```

Every command and tool call is recorded with its date, channel (cli, agente, http or mcp), action, censored parameters, result and a SHA-256 hash that includes the previous record's hash. `verificar` walks the chain and points to the first edited or deleted record. `exportar` saves every record as JSON Lines, never overwriting.

## 17. Troubleshooting

| Symptom | What to do |
|---|---|
| The model does not answer or the key is missing | Check `coopexecutive info`: it says which `.env` was loaded. Put the key in that file or use Ollama |
| Error 429 from the free model | That is OpenRouter's daily limit. Wait, change `DEFAULT_MODEL` or use a local model |
| The model does not support tools | The turn is retried without them. Use `coopexecutive modelos --herramientas` to pick one that does |
| A PDF cannot be read | Install the `pdf` extra |
| `panel` or `mcp` do not exist | Install the `web` or `mcp` extras |
| The panel says «Falta el token» | Open the full link the terminal printed, including `#token=…` |
| `escrutinio` asks for a roll | Register members with `socios alta` or use `--padron N` |
| The fact sheet has many `[PENDIENTE]` | Complete the profile (`configurar`) and the case; the agent does not fill in data it does not have |
