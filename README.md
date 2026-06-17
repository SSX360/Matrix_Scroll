# Digital Rain

A context-aware assistant for working in [Cursor](https://cursor.com) — like a
modern Clippy that actually helps. It understands the project you're building,
answers questions grounded in the **official Cursor documentation**, and
proactively recommends and scaffolds the **MCP servers, skills, and rules** that
help you reach your goal.

It runs several ways over the same engine:

- **As an MCP server inside Cursor** (primary) — Cursor's agent calls its tools
  directly while you work.
- **As a floating desktop companion** — a transparent always-on-top mascot that
  can warn about project issues and answer questions from your desktop.
- **As a local web chat** (`app.py`) — open it in a browser alongside Cursor.
- **As direct local APIs** — useful for QA, scripts, and quick health checks.

Generation uses **LLM_BACKEND** to pick a preferred backend, then falls through
**anthropic → gemini → ollama**. For fully offline use, set `LLM_BACKEND=ollama`
and run `ollama pull gemma4:e4b`. Cloud backends are used when keys are configured.

| Piece | File | What it does |
| --- | --- | --- |
| MCP server | `mcp_server.py` | 13 tools Cursor's agent can call (docs Q&A, project scan, notebook scan, brainstorm, MCP recommendations, artifact generation, device identity) |
| LLM backend | `llm.py` | Claude / Gemini / Ollama backend chain with fallthrough |
| Project scanner | `scanner.py` | Infers your stack, per-service components, and likely install/dev/build commands from manifests, configs, file tree, README |
| Retrieval | `search.py` | Pure-Python BM25 over docs **and** an MCP catalog |
| Ingestion | `ingest.py` | Scrapes Cursor docs + an MCP catalog (registry API, GitHub, mcpmarket) |
| Artifacts | `cursor_artifacts.py` | Renders `.cursor/rules/*.mdc` and `.cursor/mcp.json` |
| Web UI | `app.py` + `ui.py` | Single-page streaming chat |
| Desktop launcher | `desktop_launcher.py` + `run_desktop_companion.bat` | Starts/reuses the backend, waits for health, then launches the floating companion |

---

## 1. Install

**Python 3.9+.** From the project directory:

```bash
pip install -r requirements.txt    # flask, requests, mcp, anthropic, google-genai, cryptography
python ingest.py                   # scrape docs + build the MCP catalog index
```

Pick a generation backend (resolution tries them in order — **anthropic →
gemini → ollama** — preferred first via `LLM_BACKEND`):

- **Local Ollama (offline, common default):** install [Ollama](https://ollama.com/download),
  run `ollama pull gemma4:e4b`, and set `LLM_BACKEND=ollama`.
- **Claude:** set `ANTHROPIC_API_KEY`. Uses `claude-opus-4-8` by
  default (set `ANTHROPIC_MODEL=claude-sonnet-4-6` for a cheaper option).
- **Google Gemini:** set `GEMINI_API_KEY`. Uses `gemini-2.5-flash` by
  default (set `GEMINI_MODEL=gemini-2.5-pro` for the stronger option).

## 2. Recommended: launch the floating companion

```bat
run_desktop_companion.bat
```

This starts or reuses the local Flask backend on port `59712`, waits for
`/api/health`, then launches the transparent Tkinter companion. The backend is
started with `OPEN_BROWSER=0` so the dashboard does not steal focus; double-click
the companion to open it when needed.

You can also run the legacy alias:

```bat
run_companion.bat
```

The companion supports:

- **Drag**: left-click and drag the mascot.
- **Chat**: right-click, type a question, press Enter.
- **Dashboard**: double-click to open the web UI.
- **Project alerts**: it calls `/api/project/status` and warns about notebook
  execution issues.

Try asking:

```text
Digital Rain, scan my project and tell me what stack we are using.
Does my Jupyter Notebook have any out-of-order execution issues?
How do I configure project-specific rules in Cursor?
```

## 3. Use it as an MCP server in Cursor

Add this to your project's `.cursor/mcp.json` (or `~/.cursor/mcp.json` for all
projects), then enable it in **Cursor Settings → MCP**:

```json
{
  "mcpServers": {
    "cursor-copilot": {
      "command": "python",
      "args": ["C:/Users/you/path/to/cursor-co-pilot/mcp_server.py"],
      "env": {
        "COPILOT_WORKSPACE": "${workspaceFolder}",
        "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}",
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}"
      }
    }
  }
}
```

> On Windows, prefer an absolute path to the venv's python
> (`.../.venv/Scripts/python.exe`) so Cursor uses the right interpreter.

Once connected, Cursor's agent can call these tools:

| Tool | Purpose | Uses LLM? |
| --- | --- | --- |
| `ask_cursor_docs(question)` | Grounded answer about Cursor features | yes |
| `search_cursor_docs(query)` | Raw doc passages (fast, offline) | no |
| `scan_project(path)` | Stack profile of your project | no |
| `suggest_mcp_servers(goal, project_path)` | Ranked MCP server recommendations | optional |
| `generate_cursor_rule(intent, globs)` | A ready `.cursor/rules/*.mdc` file | yes |
| `scaffold_mcp_config(server_names)` | A merge-ready `.cursor/mcp.json` snippet | no |
| `recommend_setup(project_path, goal)` | Full "what should I set up?" plan | yes |
| `create_cursor_rule(name, intent, ...)` | Generate and write a project rule file | yes |
| `install_mcp_server(name, ...)` | Install a catalog MCP server into config | no |
| `scan_notebooks(path)` | Report notebook imports, variables, and execution order health | no |
| `search_knowledge_vault(query, ...)` | Search indexed Markdown/Obsidian notes | no |
| `brainstorm_project(goal)` | Tailored next-step ideas from stack, notebooks, rules, vault | optional |
| `device_identity()` | Active Matrix Scroll root-of-trust identity (device id, Ed25519 public key, mode) | no |

Try asking Cursor: *"Use cursor-copilot to recommend MCP servers and rules for
this project."*

## 3b. Point Digital Rain at your codebase

Each project can ship a [`.cursor/co-pilot.json.example`](.cursor/co-pilot.json.example)
as `.cursor/co-pilot.json` with workspace, vault, notebook, and brainstorm settings.

For **desktop companion** mode (Digital Rain installed separately), set the active
project in the dashboard sidebar (**Active Project → Set active project**). This
writes `~/.cursor/co-pilot-active.json`.

For **Cursor MCP** mode, add `"COPILOT_WORKSPACE": "${workspaceFolder}"` to
`mcp.json` so scans target the repo you have open—not the Digital Rain install folder.

The dashboard **Brainstorm** hero loads tailored suggestion chips from
`/api/brainstorm` based on your detected stack, notebooks, and rules.

## 4. Use it as a web chat

```bash
python app.py    # starts on a random free port and opens your browser
```

The status pill shows the active LLM backend and how many chunks are indexed.

For companion-style launches, prefer `run_desktop_companion.bat`; it pins the
backend to port `59712` and suppresses automatic browser focus.

## 5. Use local APIs for QA or scripts

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/health"
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/diagnostics"
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/project/status"
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/identity"
```

Use `/api/diagnostics` for support handoff. It includes the active workspace,
runtime, index, and LLM configuration while redacting secret-like fields.

The chat endpoint streams Server-Sent Events:

```powershell
$body = @{ message = "scan my project and tell me the stack"; history = @() } | ConvertTo-Json
Invoke-WebRequest -Uri "http://127.0.0.1:59712/api/chat" -Method POST -Body $body -ContentType "application/json"
```

Project-aware questions such as stack scans and notebook health include local
scanner context before the LLM answers.

For GTM release checks, run the fresh-project QA gate. It starts the backend
against a brand-new synthetic workspace so stale active-project pointers cannot
leak into launch evidence:

```powershell
.\.venv\Scripts\python.exe -m qa.run_gates --workspace empty --report out\qa-report.json
```

To create a full release evidence pack for Sales, support, and device-readiness
reviews, run the matrix across empty, Python, TypeScript, monorepo, notebook,
and security-sensitive fixtures. The pack also writes a CycloneDX-shaped SBOM
and supply-chain summary for the release candidate:

```powershell
.\.venv\Scripts\python.exe -m qa.release_evidence --output-dir out\release-evidence
```

See [docs/GTM_PRODUCTION_READINESS.md](docs/GTM_PRODUCTION_READINESS.md) for the
full production readiness checklist.

The TypeScript and monorepo fixtures also validate launch readiness statically:
suggested commands must stay inside the synthetic workspace, avoid destructive
script patterns, and expose a sensible install/build/run order without executing
installs or servers. The security fixture proves surfaced project scan payloads
redact sentinel secret values from README and package script metadata while
flagging sensitive local files without reading their contents. The stale-project
gate uses neutral configurable markers so QA evidence never depends on a prior
demo or customer repo.

## 5b. Matrix Scroll root of trust (Ed25519 device identity)

Digital Rain carries a device identity — the software emulation of the **Matrix
Scroll** hardware key (`identity.py`). It generates an Ed25519 keypair, derives a
human-readable device id (e.g. `MS-7F3A-9C21`), and signs release evidence so a
build is attributable to a specific device, not just an account.

- **Inspect it** — `GET /api/identity`, or ask any IDE: *"Use cursor-copilot's
  device_identity tool."* Both return the device id, public key, and mode; the
  private key never leaves the store.
- **Signed releases** — `qa.release_evidence` signs `manifest.json` and records
  the signer in `summary.md`. Verify any manifest with
  `python -c "import json,identity; print(identity.verify_manifest(json.load(open('out/release-evidence/.../manifest.json'))))"`.
- **Emulated vs. hardware** — `MATRIXSCROLL_MODE=emulated` (default) uses a local
  software key; `hardware` is reserved for the physical device. The emulated key
  store lives under `~/.matrixscroll` (directory `0700`, key file `0600`).

## 6. Use with Superpowers workflows

When working in Cursor Chat with the Superpowers skill pack installed, start a
structured coding session with:

```text
/using-superpowers
```

Good follow-up prompts:

```text
/using-superpowers QA this companion integration end to end.
/using-superpowers Write an implementation plan before changing behavior.
/using-superpowers Debug why chat fallback is not using Gemini.
```

For this repo, the useful workflow pattern is:

1. Brainstorm or write a short spec for new behavior.
2. Write a plan for multi-step changes.
3. Use TDD for fixes and behavior changes.
4. Verify with unit tests, `py_compile`, backend health, MCP smoke tests, and a
   real companion chat question.

## 7. Refresh the knowledge base

```bash
python ingest.py                 # docs + MCP catalog (full refresh)
python ingest.py --catalog-only  # refresh only the MCP catalog, rebuild index
python ingest.py --seed          # rebuild index from local docs (+ cached catalog)
python ingest.py --no-catalog    # docs only
```

The MCP catalog is built from the official
[MCP registry](https://registry.modelcontextprotocol.io), the
`modelcontextprotocol/servers` reference list, and (best-effort)
[mcpmarket.com](https://mcpmarket.com). mcpmarket rate-limits automated access,
so it's treated as optional enrichment — the registry is the robust primary.

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | _(unset)_ | Enables the Claude backend |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Claude model to use |
| `GEMINI_API_KEY` | _(unset)_ | Enables the Gemini fallback backend |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `LLM_BACKEND` | `anthropic` | Preferred backend: `anthropic`, `gemini`, or `ollama` |
| `OLLAMA_MODEL` | `gemma4:e4b` | Local model when using Ollama |
| `OLLAMA_CHAT_MODEL` | _(same as OLLAMA_MODEL)_ | Faster model for interactive chat (`gemma3:4b` recommended) |
| `OLLAMA_NUM_PREDICT` | `512` | Max tokens for Ollama chat generation |
| `OLLAMA_BRAINSTORM_NUM_PREDICT` | `256` | Max tokens for async Ollama brainstorm jobs |
| `STATUS_CACHE_TTL` | `30` | Seconds to cache `/api/project/status` scans |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `TOP_K` | `5` | Doc chunks retrieved per question (web UI) |
| `COPILOT_WORKSPACE` | _(unset)_ | Absolute path to the user's active codebase (MCP: `${workspaceFolder}`) |
| `MATRIXSCROLL_MODE` | `emulated` | Root-of-trust provider: `emulated` (software key) or `hardware` (Matrix Scroll device) |
| `MATRIXSCROLL_HOME` | `~/.matrixscroll` | Directory for the emulated device key store (created `0700`, key file `0600`) |
| `PORT` | _(random)_ | Force a specific port for the web UI |
| `OPEN_BROWSER` | `1` | Set to `0` to keep `app.py` from opening the dashboard automatically |
| `SLACK_BOT_TOKEN` | _(unset)_ | Slack bot token (`xoxb-…`) for the dev-team notifier; unset = notifier inert |
| `SLACK_CHANNEL_CICD` | `#feed-ci-cd-qa` | Channel for QA gate / release-evidence posts |
| `SLACK_WEBHOOK_CICD` | _(unset)_ | Optional Incoming Webhook for CI/QA; overrides the bot token for that channel |

Any of these can be set in a gitignored **`.env`** at the repo root (copy
`.env.example`). Real OS environment variables always override `.env` values.

Backend resolution walks the chain **anthropic → gemini → ollama** (with the
`LLM_BACKEND` choice moved to the front) and uses the first backend that has its
key + SDK available; if one errors at call time it falls through to the next. So
with no cloud keys set it lands on Ollama and keeps working offline.

## Project layout

```
cursor-co-pilot/
  mcp_server.py           # MCP server (stdio) + 13 tools  <- Digital Rain
  identity.py             # Matrix Scroll root of trust (Ed25519 device identity + signing)
  llm.py                  # Claude / Gemini / Ollama backend chain
  scanner.py              # project stack profiler
  cursor_artifacts.py     # .mdc rule + mcp.json renderers
  app.py                  # Flask web chat (streaming)
  ui.py                   # single-page chat UI
  companion.py            # floating desktop mascot (Tkinter)
  desktop_launcher.py     # starts/reuses backend, then launches companion
  run_desktop_companion.bat
  search.py               # chunking + BM25 over docs AND mcp catalog
  ingest.py               # scrape docs + ingest MCP catalog
  tests/                  # unit tests (launcher, LLM errors, project context)
  data/
    docs/                 # scraped Cursor docs (markdown)
    catalog/              # cached MCP catalog (registry, servers, mcpmarket)
    index.json            # built BM25 index (docs + catalog)
```

Optional dev dependency for regenerating `docs/Digital-Rain-Feature-Guide.pdf`:

```bash
pip install -r requirements-dev.txt
python scratch/generate_feature_guide_pdf.py
```

## Troubleshooting

- **MCP server won't connect in Cursor** — check the absolute python path in
  `mcp.json`; ensure deps are installed in that interpreter; the server logs to
  stderr (visible in Cursor's MCP logs). Never `print()` to stdout from it —
  stdout is the transport.
- **"Couldn't reach a local model"** — set `ANTHROPIC_API_KEY` to use Claude, or
  start Ollama (`ollama serve` + `ollama pull gemma4:e4b`).
- **Gemini 429 / `RESOURCE_EXHAUSTED`** — the key is present, but billing or
  prepayment credits need attention. Add credits, use another Gemini key, set
  `ANTHROPIC_API_KEY`, or start Ollama.
- **Desktop companion launches but chat errors** — check `/api/health`; if the
  LLM chain is configured but every backend fails, the chat stream reports each
  backend failure in order.
- **Companion starts more than once** — the widget has a socket lock and should
  no-op on duplicate launches. Use `run_desktop_companion.bat` so backend reuse
  and companion launch happen together.
- **Few / stale MCP recommendations** — run `python ingest.py --catalog-only`.
- **Answers seem thin** — run `python ingest.py` to pull the full docs set.
