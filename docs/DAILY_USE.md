# Archived Daily Use - Digital Rain

Historical note: this file covers an older Digital Rain local workflow. It is
retained for reference only and should not be used as the current Matrix Scroll
public quickstart.

Use these canonical surfaces for current launch messaging and evaluation:

- `https://matrixscroll.com`
- `https://matrixscroll.com/docs/`
- `https://github.com/SSX360/matrixscroll`

## One-command launch

```bat
run_desktop_companion.bat
```

Starts or reuses the backend on port **59712**, then opens the floating companion.

## First-time setup (once)

1. Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` if missing
2. Set `GEMINI_API_KEY` in Windows environment (optional cloud fallback)
3. Pull models:
   ```bat
   ollama pull gemma4:e4b
   ollama pull gemma3:4b
   ```
4. In the dashboard sidebar: **Set active project** to your real repo path

## Recommended Ollama split

| Task | Model | Env var |
|------|-------|---------|
| Interactive chat | `gemma3:4b` (fast) | `OLLAMA_CHAT_MODEL` |
| Brainstorm enhancement | `gemma4:e4b` (quality) | `OLLAMA_MODEL` |

Brainstorm shows **offline chips instantly**, then upgrades in the background when `async=1` (dashboard default).

## Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:59712/api/health
Invoke-RestMethod "http://127.0.0.1:59712/api/brainstorm?limit=3&async=1"
Invoke-RestMethod http://127.0.0.1:59712/api/identity
```

`/api/identity` returns the active Matrix Scroll device id, Ed25519 public key,
and mode (`emulated` by default). The same data is available to any IDE through
the `device_identity` MCP tool.

## MCP in Cursor

Add to your project's `.cursor/mcp.json`:

```json
"COPILOT_WORKSPACE": "${workspaceFolder}"
```

Enable **cursor-copilot** in Cursor Settings → MCP.
