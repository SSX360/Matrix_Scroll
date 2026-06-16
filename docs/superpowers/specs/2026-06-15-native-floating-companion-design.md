# Native Floating Companion Design

## Goal

Make the desktop companion feel like a first-class way to run Cursor Co-pilot: one command starts the local backend, waits until it is reachable, and then launches the transparent always-on-top mascot widget.

The first implementation should stay native on Windows. Docker can be useful later for packaging the backend, but the floating overlay itself needs access to the user's desktop session, which is simpler and more reliable from a host Windows process.

## Current Context

- `app.py` runs the Flask dashboard and API, writes the active port to `.cursor/port.json`, and currently opens the dashboard in a browser on startup.
- `companion.py` is a Tkinter desktop widget. It reads `.cursor/port.json`, floats above the desktop, opens the dashboard on double-click, and calls the backend for project status and chat.
- `run_companion.bat` launches only `companion.py`, so it assumes the backend is already running.
- `.cursor/mcp.json` already contains the Gemini-oriented environment used by the MCP server.

## Recommended Approach

Add a native Windows launcher that orchestrates both pieces:

1. Load environment settings from `.cursor/mcp.json` when available.
2. Start `app.py` on a stable port, defaulting to `59712`.
3. Wait for `http://127.0.0.1:<port>/api/health` to respond.
4. Launch `companion.py` after the backend is healthy.
5. Avoid launching duplicate backends or duplicate companion widgets.

This keeps the backend and desktop UI as separate processes with a simple HTTP boundary.

## UX

The user should be able to run one command from the project root:

```bat
run_desktop_companion.bat
```

Expected behavior:

- If the backend is already healthy, reuse it.
- If the backend is not running, start it in a separate terminal process.
- Once healthy, launch the floating companion.
- Keep the existing companion interactions: drag, right-click chat, double-click dashboard, notebook warning bubble.

The backend should support a launch mode that does not automatically open the browser, so starting the floating companion does not also force the dashboard into focus.

## Components

### Launcher

A new Windows batch launcher should own startup orchestration. It should:

- Activate or directly use `.venv\Scripts\python.exe`.
- Load `PORT`, `LLM_BACKEND`, `GEMINI_MODEL`, and `GEMINI_API_KEY` from `.cursor/mcp.json` where possible.
- Start the backend only if the health endpoint is unavailable.
- Poll `/api/health` for a short bounded period.
- Launch `companion.py` once the backend is available.

### Backend

`app.py` should gain a small configuration flag such as `OPEN_BROWSER=0` to suppress automatic browser opening for companion-driven launches.

The existing `.cursor/port.json` behavior should remain, because `companion.py` already uses it as the discovery mechanism.

### Companion

`companion.py` should remain the native overlay. It already has a duplicate-widget lock on `127.0.0.1:52809`, so the initial design does not need a new companion lock.

Any changes here should be minimal and limited to making startup errors clearer if the backend cannot be reached.

## Error Handling

- If `.venv\Scripts\python.exe` is missing, the launcher should print a clear setup message.
- If `.cursor/mcp.json` is missing or cannot be parsed, the launcher should still start with existing environment variables and defaults.
- If the backend does not become healthy, the launcher should stop before launching the companion and explain which URL failed.
- If the companion is already running, preserve the existing no-op behavior.

## Non-Goals

- Do not Dockerize the floating desktop widget in the first pass.
- Do not replace Tkinter with Electron, Tauri, or a browser wrapper yet.
- Do not change the MCP server transport or Cursor MCP configuration.
- Do not redesign the dashboard UI as part of this work.

## Verification

- Run the new launcher from a clean terminal with no backend running.
- Confirm `/api/health` responds on the configured port.
- Confirm `.cursor/port.json` contains the same port the launcher used.
- Confirm the floating companion appears and can open the dashboard.
- Confirm running the launcher again does not create duplicate companion widgets.
- Confirm `OPEN_BROWSER=0` suppresses backend browser auto-open during companion launch.
