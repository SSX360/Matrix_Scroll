# Archived Digital Rain Integrations

Historical note: this file documents older pre-launch local MCP and desktop
companion workflows from the Digital Rain phase of the project. It is not the
current Matrix Scroll public product surface.

Current public truth lives here first:

- `https://matrixscroll.com`
- `https://matrixscroll.com/docs/`
- `https://github.com/SSX360/matrixscroll`
- `Matrix_Scroll/README.md`

Digital Rain is designed to be highly interoperable, working across multiple editors, agent platforms, and directly on your desktop.

---

## 1. Desktop Floating Companion (Clippy-style Widget)

You can launch a lightweight, transparent, always-on-top floating desktop mascot that stays on the side of your screen (matching your IDE) by running:

```bat
run_desktop_companion.bat
```

The launcher starts or reuses the local Flask backend, waits for it to become
healthy, and then opens the floating companion. It starts the backend with browser
auto-open disabled, so the mascot can launch quietly and still open the dashboard
on double-click.

### Features:
- **Frameless & Transparent**: It has no window borders. The cyberpunk girl mascot floats directly over your IDE and desktop.
- **Draggable**: Left-click and drag the mascot anywhere on your screen.
- **Project Scan Alerts**: Reads the active workspace (not just the Digital Rain install dir) and alerts you through a speech bubble (e.g. if you have out-of-order execution in Jupyter Notebooks).
- **Interactive Chat**: Right-click the mascot to open a text box, type your question, and press Enter — answers stream in the speech bubble.
- **Brainstorm greeting**: On launch, surfaces a tailored next-step idea from `/api/brainstorm`.
- **Double-click Dashboard**: Double-click the mascot to open the full web dashboard in your browser.

---

## 2. Integration with Other IDEs & Editors

Because the assistant exposes a standard **Model Context Protocol (MCP)** server via `mcp_server.py`, you can easily connect it to other editors. The server exposes **13 tools** (docs Q&A, project scan, notebook scan, brainstorm, MCP recommendations, artifact generation, device identity, and more).

### A. VS Code (native agent mode, 1.102+)
VS Code has built-in MCP support in agent mode. Commit a workspace config at `.vscode/mcp.json` using the native `servers` map with `type: "stdio"`, then start it from the **Start** code-lens above the server entry (or **MCP: List Servers → Start**):

```json
{
  "servers": {
    "digital-rain-mcp": {
      "type": "stdio",
      "command": "path/to/digital-rain/.venv/Scripts/python.exe",
      "args": [
        "path/to/digital-rain/mcp_server.py"
      ],
      "env": {
        "COPILOT_WORKSPACE": "${workspaceFolder}",
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}",
        "LLM_BACKEND": "ollama",
        "GEMINI_MODEL": "gemini-2.5-flash",
        "OLLAMA_MODEL": "gemma4:e4b",
        "OLLAMA_CHAT_MODEL": "gemma3:4b"
      }
    }
  }
}
```

On Windows, point `command` at the absolute `.venv\Scripts\python.exe` so VS Code runs the correct interpreter. The 13 tools then appear in the agent tools picker.

### B. VS Code (via Cline, Roo-Code, or Windsurf)
If you are using VS Code with agent extensions like Cline or Roo-Code, add the server to your global MCP settings file (typically `~/AppData/Roaming/Code/User/global_mcp_settings.json`). These extensions use the `mcpServers` key:

```json
{
  "mcpServers": {
    "digital-rain-mcp": {
      "command": "python",
      "args": [
        "path/to/digital-rain/mcp_server.py"
      ],
      "env": {
        "COPILOT_WORKSPACE": "${workspaceFolder}",
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "LLM_BACKEND": "ollama",
        "GEMINI_MODEL": "gemini-2.5-flash",
        "OLLAMA_MODEL": "gemma4:e4b"
      }
    }
  }
}
```

### C. Claude Desktop
To integrate with the Claude Desktop app, edit your `claude_desktop_config.json` (located in `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "digital-rain-mcp": {
      "command": "python",
      "args": [
        "path/to/digital-rain/mcp_server.py"
      ],
      "env": {
        "COPILOT_WORKSPACE": "${workspaceFolder}",
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "LLM_BACKEND": "ollama",
        "OLLAMA_MODEL": "gemma4:e4b"
      }
    }
  }
}
```

### D. Cursor Editor
The Cursor editor handles it automatically! It registers via `.cursor/mcp.json` or by adding a new `command` MCP server in your Cursor settings:
- **Type**: `command`
- **Command**: `python path/to/digital-rain/mcp_server.py`
- **Env**: set `COPILOT_WORKSPACE` to `${workspaceFolder}` so scans target the repo you have open.

---

## 3. Per-Project Workspace & Vault

By default Digital Rain used to scan its own install directory. It now resolves the **active codebase** from (in priority order):

1. `COPILOT_WORKSPACE` env var (set in MCP config for Cursor)
2. `~/.cursor/co-pilot-active.json` (set from the dashboard **Active Project** sidebar)
3. The co-pilot install root (fallback)

### Per-repo config: `.cursor/co-pilot.json`

Copy [`.cursor/co-pilot.json.example`](.cursor/co-pilot.json.example) into each project as `.cursor/co-pilot.json`:

| Section | Purpose |
|---------|---------|
| `workspace_root` | Relative root for scans (usually `.`) |
| `vault.mode` | `project` (scaffold under repo) or `existing` (link Obsidian vault) |
| `vault.path` | Absolute path when `mode` is `existing` |
| `vault.project_subdir` | Subfolder for scaffolded vault (default `docs/vault`) |
| `notebooks` | Enable scans, out-of-order warnings, exclude dirs |
| `brainstorm` | Tailored suggestion chips; optional LLM enhancement |

### Dashboard setup

Open the web dashboard (double-click the companion) and use the sidebar:

- **Set active project** — writes `~/.cursor/co-pilot-active.json`
- **Vault mode** — project scaffold vs existing Obsidian path
- **Scaffold vault** — creates `docs/vault/` with starter notes
- **Brainstorm chips** — dynamic next-step ideas from stack, notebooks, rules, vault

### REST API (Flask)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workspace/status` | GET | Active workspace path and configured flag |
| `/api/workspace/active` | PUT | Set active project (`{"path": "..."}`) |
| `/api/workspace/config` | GET/PUT | Read/write merged `.cursor/co-pilot.json` |
| `/api/vault/status` | GET | Vault path, mode, note count |
| `/api/vault/scaffold` | POST | Create project vault under configured subdir |
| `/api/brainstorm` | GET | Tailored suggestions (`?limit=6`) |
| `/api/project/status` | GET | Stack scan of active workspace |
| `/api/health` | GET | LLM backend chain + Ollama model availability |
| `/api/identity` | GET | Matrix Scroll root-of-trust identity (device id, public key, mode) |

### MCP tools (workspace-aware)

When `COPILOT_WORKSPACE` is set, these default to your open repo:

- `scan_project` — languages, frameworks, dependencies
- `scan_notebooks` — Jupyter health (out-of-order cells)
- `brainstorm_project(goal)` — tailored next-step ideas
- `search_knowledge_vault` — Obsidian/knowledge vault search
- `device_identity` — active Matrix Scroll root-of-trust identity (device id, Ed25519 public key, mode)

### Root of trust (device identity)

Every editor connection shares the same Matrix Scroll device identity from
`identity.py`. The active key signs release evidence (`qa/release_evidence.py`)
so builds are attributable to a device, and any IDE can read the public identity
via the `device_identity` tool or `GET /api/identity`. Mode is selected with
`MATRIXSCROLL_MODE` (`emulated` software key by default, `hardware` for the
physical device); the private key never leaves the store.

---

## 4. Integration with Antigravity (this Agent)

Since we are running in the **Antigravity** environment, Antigravity can call the tools of Digital Rain using standard MCP commands or by querying the Flask REST API at `http://127.0.0.1:<port>/api/project/status`.

All tool schemas are exposed on the standard `mcp_server.py` stdio channel.

### LLM backends

Resolution order: **anthropic → gemini → ollama** (preferred backend first via `LLM_BACKEND`).

- **Local Ollama (recommended offline):** `ollama pull gemma4:e4b`, set `LLM_BACKEND=ollama` and `OLLAMA_MODEL=gemma4:e4b`
- **Gemini:** `GEMINI_API_KEY` + `LLM_BACKEND=gemini`
- **Anthropic:** `ANTHROPIC_API_KEY` + `LLM_BACKEND=anthropic`

The dashboard health pill shows the **active** backend from `/api/health` (`llm.active`).
