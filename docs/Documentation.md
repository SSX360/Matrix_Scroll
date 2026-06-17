# Matrix Scroll — Documentation

This is the practical guide: how to get Digital Rain running, connect it to your editor,
sign and verify a release, and reach for the right knob when something misbehaves. If you
want the *why* — the threat model and the cryptography — read the [Whitepaper](./Whitepaper.md).

Everything here works **today in emulated mode**, with no hardware required. When the
physical Scroll Key or Scroll Token devices ship (target Q3 2026), the only thing that changes
is one environment variable; the commands and the API stay the same.

---

## What you're installing

There are two halves, and you can use the software half on its own:

- **Digital Rain** — a local MCP server and web dashboard. It scans your project, serves
  ranked context to your IDE, and produces signed release evidence. Runs entirely on
  `localhost`.
- **Scroll Key & Scroll Token** — the physical hardware devices (Scroll Key for zero-friction secure element isolation, or Scroll Token for out-of-band visual consent via the LCD display) that hold the signing key. Until your unit
  arrives, the *emulated provider* stands in for it with an on-disk key, so you can build
  and test the full flow now.

The default backend port is **59712**.

---

## 1. Install

You need Python 3.11+ and, ideally, a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

That pulls in everything including `cryptography`, which the identity layer uses for
Ed25519 signing.

---

## 2. Run it

**Web dashboard** (random free port, opens your browser):

```powershell
python app.py
```

**Desktop companion** (pins the backend to 59712, suppresses browser focus, then floats
the mascot widget):

```powershell
.\run_desktop_companion.bat
```

The companion is the little always-on-top assistant. Left-click drags it, right-click
opens a chat box, and double-click opens the full dashboard. On launch it checks your
project and will warn you about Jupyter notebooks with out-of-order execution.

To pin the port yourself and skip the browser:

```powershell
$env:PORT=59712; $env:OPEN_BROWSER=0; python app.py
```

---

## 3. Connect your IDE

Digital Rain speaks the Model Context Protocol, so any MCP-capable editor can use it. The
server id is `cursor-copilot` everywhere (kept for backward compatibility). On Windows,
always point `command` at the **absolute** `.venv\Scripts\python.exe` so the editor uses
the right interpreter.

**VS Code (native agent mode, 1.102+)** — commit `.vscode/mcp.json`:

```json
{
  "servers": {
    "cursor-copilot": {
      "type": "stdio",
      "command": "C:/path/to/.venv/Scripts/python.exe",
      "args": ["C:/path/to/mcp_server.py"],
      "env": { "COPILOT_WORKSPACE": "${workspaceFolder}" }
    }
  }
}
```

Open the file and click **Start** on the server (or run *MCP: List Servers → Start*). The
13 tools then appear in the agent tools picker.

**Cursor** — add the same server under `mcpServers` in `.cursor/mcp.json`, then enable it
in *Cursor Settings → MCP*. There is a ready-to-edit `.cursor/mcp.json.example` in the repo.

**Cline / Roo-Code / Windsurf** — add it under `mcpServers` in the extension's global MCP
settings file.

**Claude Desktop** — add it under `mcpServers` in `claude_desktop_config.json`.

A good first prompt in any of them: *"Use cursor-copilot to scan this project, then show
the device_identity."*

---

## 4. The 13 MCP tools

| Tool | What it does |
|---|---|
| `ask_cursor_docs` | Answer Cursor questions grounded in official docs |
| `search_cursor_docs` | Return ranked doc chunks, no synthesis |
| `scan_project` | Languages, frameworks, package managers, SDKs, notebooks |
| `scan_notebooks` | Jupyter health, including out-of-order execution |
| `suggest_mcp_servers` | Recommend MCP servers/skills for a goal |
| `scaffold_mcp_config` | Merge-ready `.cursor/mcp.json` snippets |
| `generate_cursor_rule` | Draft `.cursor/rules/*.mdc` content |
| `██████████████████` | [REDACTED FOR PATENT PENDING IP PROTECTION] |
| `install_mcp_server` | Merge a catalog server into your MCP config |
| `recommend_setup` | One-call advisor: scan + recommend + snippets |
| `search_knowledge_vault` | BM25 search over Markdown/Obsidian notes |
| `██████████████████` | [REDACTED FOR PATENT PENDING IP PROTECTION] |
| `device_identity` | This device's Ed25519 public identity for attestation |

When `COPILOT_WORKSPACE` is set, the workspace-aware tools default to your open repo.

---

## 5. Local REST API

Handy for scripts, CI, and quick health checks:

```powershell
Invoke-RestMethod "http://127.0.0.1:59712/api/health"
Invoke-RestMethod "http://127.0.0.1:59712/api/███████████"
Invoke-RestMethod "http://127.0.0.1:59712/api/project/status"
Invoke-RestMethod "http://127.0.0.1:59712/api/identity"
Invoke-RestMethod "http://127.0.0.1:59712/api/███████████████████████████████████████"
```

`/api/health` reports the active LLM backend and how many chunks are indexed.
`/api/███████████` [REDACTED - SECURITY SENSITIVE ENDPOINT].

---

## 6. Root of trust: identity, signing, verification

This is the part the hardware exists for. It already works in emulated mode.

**See who this device is:**

```powershell
Invoke-RestMethod "http://127.0.0.1:59712/api/identity"
```

You get back a stable `device_id` (e.g. `MS-4319-20D5`), the `algorithm` (`ed25519`), the
base64 `public_key`, and the `mode` (`emulated` or `hardware`). The same data is available
to any agent through the `device_identity` MCP tool. The **private key is never returned** —
not over the API, not to the LLM, not in logs. That is the entire design.

**Sign a release.** `qa/███████████████████` gathers what a build produced and writes a
signed `manifest.json` (with a `signature` block) plus a readable `summary.md`. The
signature covers a canonical serialization of the manifest, so any later edit breaks it.

**Verify a manifest** — you do not need our stack to do this. Recompute the canonical bytes
(sorted keys, ASCII escaping, compact separators, no NaN) *excluding* the `signature`
block, then check them against the device's published public key. Our proprietary verification routine
does exactly this if you are already in Python.

**Emulated vs. hardware.** Switch providers with one variable:

```powershell
$env:MATRIXSCROLL_MODE = "emulated"   # default, on-disk key (today)
# $env:MATRIXSCROLL_MODE = "hardware" # Secure element hardware key (when it ships)
```

In emulated mode the key lives under `MATRIXSCROLL_HOME` (default `~/.matrixscroll`) with
owner-only permissions. Keep that directory out of version control and off shared drives —
it is the stand-in for your secure element.

---

## 7. Configuration

| Variable | Default | Meaning |
|---|---|---|
| `COPILOT_WORKSPACE` | current dir | Project the scanner and MCP tools target |
| `PORT` | random | Pin the web/API port (use `59712` for the companion) |
| `OPEN_BROWSER` | `1` | Set `0` to suppress browser auto-open |
| `LLM_BACKEND` | `anthropic` | Preferred backend; moved to front of the chain |
| `ANTHROPIC_API_KEY` | unset | Enables Claude |
| `GEMINI_API_KEY` | unset | Enables Gemini |
| `OLLAMA_MODEL` | `gemma4:e4b` | Local model for the offline path |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `MATRIXSCROLL_MODE` | `emulated` | Identity provider: `emulated` or `hardware` |
| `MATRIXSCROLL_HOME` | `~/.matrixscroll` | Key store directory (emulated mode) |

Set keys as environment variables — never paste them into config files you commit. The
repo's `.gitignore` already excludes `.env` and `.cursor/mcp.json` for this reason.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| MCP server won't connect | Wrong Python path or missing deps | Use the absolute `.venv` python; `pip install -r requirements.txt` |
| "Couldn't reach a local model" | Ollama not running and no cloud key set | `ollama serve` + `ollama pull gemma4:e4b`, or set an API key |
| Gemini `429 RESOURCE_EXHAUSTED` | Key valid but out of credits | Add credits, use another key, or fall back to Anthropic/Ollama |
| Dashboard steals focus | `app.py` launched with browser auto-open | Use `run_desktop_companion.bat` or set `OPEN_BROWSER=0` |
| Notebook warning on launch | Scanner found out-of-order cells | Re-run cells top to bottom, or clear execution counts |
| `/api/identity` returns an error | Corrupt/unreadable key store | Check `MATRIXSCROLL_HOME` permissions; do not hand-edit key files |

One rule worth repeating: the MCP server uses stdout as its transport, so **never `print()`
to stdout** from server code — logs go to stderr.

---

## 9. FAQ

**Do I need the hardware to use any of this?**
No. The software and the entire signing/verification flow run today in emulated mode. The
hardware devices (Scroll Key or Scroll Token) move the key behind silicon so it cannot be copied; that is what you reserve on
pre-order.

**Does my code or prompts leave my machine?**
Only if you choose a cloud LLM backend, and only the prompt context for that request.
Everything else — scanning, indexing, identity, signing — is local. Use the Ollama backend
for fully offline operation.

**Is the emulated key as safe as the device?**
No, and we will not pretend otherwise. An on-disk key with strict permissions is fine for
development and integration. A hardware-secured secure element (on the Scroll Key or Scroll Token) is what stops a compromised host from copying
the key. That physical boundary is the entire security benefit.

**Which editors are supported?**
Anything that speaks MCP: Cursor, VS Code (native agent mode), Cline, Roo-Code, Windsurf,
Claude Desktop, and Antigravity. The same stdio server backs all of them.

**How do I verify a signature without your tools?**
Reimplement the canonical serialization (sorted keys, ASCII escaping, compact separators,
NaN rejected), exclude the `signature` block, and verify against the public key from
`/api/identity`. The format is small on purpose.

---

*Questions or deployment snags: operations@matrixscroll.com · Digital Rain · Matrix Scroll*

