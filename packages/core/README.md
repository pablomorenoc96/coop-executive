# CoopExecutive

![CoopExecutive](https://raw.githubusercontent.com/pablomorenoc96/coop-executive/main/assets/banner_en.png)

Local AI agent for grant procurement and democratic governance in cooperatives, civil associations and social economy organisations. It evaluates funding calls with a 100-point evidence matrix, tracks funders and cases, prepares meetings, drafts proposals and Word documents without inventing amounts or dates, and runs one-member-one-vote assemblies with SHA-256 minutes. The same 19 tools are available from the CLI, a local web panel, a local API and an MCP server, and every write asks for confirmation.

![Demo](https://raw.githubusercontent.com/pablomorenoc96/coop-executive/main/assets/demo_en.gif)

## Install

```bash
pipx install "coopexecutive[web,mcp,pdf] @ git+https://github.com/pablomorenoc96/coop-executive.git#subdirectory=packages/core"
coopexecutive iniciar ~/procurement/my-org --nombre "My Organisation" --tipo asociacion_civil
export COOPEXECUTIVE_WORKSPACE=~/procurement/my-org
coopexecutive configurar --sitio https://www.example.org/
```

Extras: `web` (panel and API), `mcp` (MCP server), `pdf` (PDF reading), `identidad` (terminal intro), `todo` (all of them).

## Development

```bash
cd packages/core
uv sync --all-extras --all-groups
uv run --extra dev pytest -q
uv run --extra dev ruff check coopexecutive tests evals
uv run python -m coopexecutive.evals
```

Full documentation, model setup and guides: [github.com/pablomorenoc96/coop-executive](https://github.com/pablomorenoc96/coop-executive).

MIT License.
