# Native Floating Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command native Windows launch path that starts or reuses the Flask backend and then opens the floating Tkinter companion.

**Architecture:** Add a small Python launcher as the orchestration layer and keep `run_desktop_companion.bat` as the user-facing Windows entrypoint. The launcher reads `.cursor/mcp.json`, starts `app.py` with a stable port and browser auto-open disabled, waits for `/api/health`, then launches `companion.py`.

**Tech Stack:** Python stdlib, Flask backend in `app.py`, Tkinter companion in `companion.py`, Windows batch entrypoint.

---

### Task 1: Backend Browser Suppression Flag

**Files:**
- Modify: `app.py`
- Test: `tests/test_app_launch_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_app_launch_config.py`:

```python
import importlib
import os
import unittest
from unittest.mock import patch


class AppLaunchConfigTests(unittest.TestCase):
    def reload_app(self):
        import app
        return importlib.reload(app)

    def test_should_open_browser_defaults_true(self):
        with patch.dict(os.environ, {}, clear=True):
            app = self.reload_app()
            self.assertTrue(app.should_open_browser())

    def test_should_open_browser_respects_zero_false_no_off(self):
        for value in ("0", "false", "False", "no", "off"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPEN_BROWSER": value}, clear=True):
                    app = self.reload_app()
                    self.assertFalse(app.should_open_browser())

    def test_should_open_browser_accepts_one_true_yes_on(self):
        for value in ("1", "true", "yes", "on"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPEN_BROWSER": value}, clear=True):
                    app = self.reload_app()
                    self.assertTrue(app.should_open_browser())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app_launch_config -v
```

Expected: FAIL because `app.should_open_browser` does not exist.

- [ ] **Step 3: Implement the launch flag**

In `app.py`, add this helper near the server bootstrap section:

```python
def should_open_browser() -> bool:
    value = os.environ.get("OPEN_BROWSER", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}
```

Then change:

```python
threading.Timer(0.8, lambda: webbrowser.open(url)).start()
```

to:

```python
if should_open_browser():
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app_launch_config -v
```

Expected: PASS.

---

### Task 2: Native Desktop Launcher

**Files:**
- Create: `desktop_launcher.py`
- Test: `tests/test_desktop_launcher.py`

- [ ] **Step 1: Write failing tests for config loading and health polling**

Create `tests/test_desktop_launcher.py`:

```python
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import desktop_launcher


class DesktopLauncherTests(unittest.TestCase):
    def test_load_mcp_env_returns_cursor_copilot_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "cursor-copilot": {
                        "env": {
                            "GEMINI_API_KEY": "secret",
                            "LLM_BACKEND": "gemini",
                            "GEMINI_MODEL": "gemini-2.5-flash"
                        }
                    }
                }
            }), encoding="utf-8")

            env = desktop_launcher.load_mcp_env(config_path)

        self.assertEqual(env["GEMINI_API_KEY"], "secret")
        self.assertEqual(env["LLM_BACKEND"], "gemini")
        self.assertEqual(env["GEMINI_MODEL"], "gemini-2.5-flash")

    def test_load_mcp_env_returns_empty_dict_for_missing_file(self):
        env = desktop_launcher.load_mcp_env(Path("missing-mcp.json"))
        self.assertEqual(env, {})

    def test_is_backend_healthy_true_on_200(self):
        response = Mock()
        response.status_code = 200
        with patch("desktop_launcher.request.urlopen", return_value=response):
            self.assertTrue(desktop_launcher.is_backend_healthy("http://127.0.0.1:59712/api/health"))

    def test_is_backend_healthy_false_on_exception(self):
        with patch("desktop_launcher.request.urlopen", side_effect=OSError("offline")):
            self.assertFalse(desktop_launcher.is_backend_healthy("http://127.0.0.1:59712/api/health"))

    def test_build_backend_env_forces_port_and_browser_flag(self):
        env = desktop_launcher.build_backend_env({"LLM_BACKEND": "gemini"}, port=59712)
        self.assertEqual(env["PORT"], "59712")
        self.assertEqual(env["OPEN_BROWSER"], "0")
        self.assertEqual(env["LLM_BACKEND"], "gemini")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_desktop_launcher -v
```

Expected: FAIL because `desktop_launcher.py` does not exist.

- [ ] **Step 3: Implement the launcher module**

Create `desktop_launcher.py`:

```python
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = int(os.environ.get("PORT", "59712"))
HEALTH_TIMEOUT_SECONDS = 30


def load_mcp_env(config_path: Path) -> dict[str, str]:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    server = data.get("mcpServers", {}).get("cursor-copilot", {})
    env = server.get("env", {})
    if not isinstance(env, dict):
        return {}
    return {str(key): str(value) for key, value in env.items() if value is not None}


def build_backend_env(extra_env: dict[str, str], port: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra_env)
    env["PORT"] = str(port)
    env["OPEN_BROWSER"] = "0"
    return env


def is_backend_healthy(health_url: str, timeout: float = 1.5) -> bool:
    try:
        with request.urlopen(health_url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except OSError:
        return False


def wait_for_backend(health_url: str, timeout_seconds: int = HEALTH_TIMEOUT_SECONDS) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_backend_healthy(health_url):
            return True
        time.sleep(0.5)
    return False


def python_executable() -> Path:
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def start_backend(port: int) -> subprocess.Popen:
    env = build_backend_env(load_mcp_env(ROOT / ".cursor" / "mcp.json"), port)
    return subprocess.Popen(
        [str(python_executable()), str(ROOT / "app.py")],
        cwd=str(ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )


def start_companion() -> subprocess.Popen:
    return subprocess.Popen(
        [str(python_executable()), str(ROOT / "companion.py")],
        cwd=str(ROOT),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )


def main() -> int:
    port = DEFAULT_PORT
    health_url = f"http://127.0.0.1:{port}/api/health"

    if is_backend_healthy(health_url):
        print(f"Backend already healthy at {health_url}")
    else:
        print(f"Starting backend on port {port}...")
        start_backend(port)
        if not wait_for_backend(health_url):
            print(f"Backend did not become healthy at {health_url}", file=sys.stderr)
            return 1

    print("Launching floating companion...")
    start_companion()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the launcher tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_desktop_launcher -v
```

Expected: PASS.

---

### Task 3: User-Facing Batch Entrypoint

**Files:**
- Create: `run_desktop_companion.bat`
- Modify: `README.md`
- Modify: `INTEGRATIONS.md`

- [ ] **Step 1: Create the batch entrypoint**

Create `run_desktop_companion.bat`:

```bat
@echo off
title Cursor Co-pilot Desktop Companion Launcher
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo Starting Cursor Co-pilot backend and floating companion...
%PYTHON% desktop_launcher.py

if errorlevel 1 (
  echo.
  echo Failed to launch Cursor Co-pilot desktop companion.
  pause
)
```

- [ ] **Step 2: Update documentation**

In `README.md`, add a short section after the web chat section:

```markdown
## 4. Use the floating desktop companion

```bat
run_desktop_companion.bat
```

This starts or reuses the local Flask backend on port `59712`, waits for it to become healthy, then launches the transparent Tkinter companion. The backend is started with `OPEN_BROWSER=0` so the dashboard does not steal focus; double-click the companion to open it when needed.
```

In `INTEGRATIONS.md`, update the desktop companion section so it points to:

```bat
run_desktop_companion.bat
```

and explains that the launcher starts both backend and floating widget.

- [ ] **Step 3: Run syntax and launcher smoke checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m py_compile desktop_launcher.py app.py companion.py
.\run_desktop_companion.bat
```

Expected:

- `py_compile` exits successfully.
- Launcher reports backend healthy or starts it.
- Floating companion appears.

---

### Task 4: QA and Optimization Pass

**Files:**
- Modify only if verification reveals issues: `desktop_launcher.py`, `app.py`, `companion.py`, docs.

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Expected: all tests pass.

- [ ] **Step 2: Confirm backend health**

Run:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/health" -TimeoutSec 10 | ConvertTo-Json -Compress
```

Expected: JSON contains `"chunks":191` or another positive chunk count, and `llm.active` reflects the configured usable backend.

- [ ] **Step 3: Confirm project scan still works through MCP**

Run the existing stdio MCP client smoke test:

```powershell
@'
import asyncio, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command=r"c:\Users\ryanj\OneDrive\Desktop\cursor-co-pilot\.venv\Scripts\python.exe",
        args=[r"c:\Users\ryanj\OneDrive\Desktop\cursor-co-pilot\mcp_server.py"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("scan_notebooks", {"path": r"c:\Users\ryanj\OneDrive\Desktop\cursor-co-pilot"})
            print(result.content[0].text)

asyncio.run(main())
'@ | .\.venv\Scripts\python.exe -
```

Expected: output includes `test_notebook.ipynb` and `execution_health` of `out_of_order`.

- [ ] **Step 4: Optimize startup behavior if needed**

If startup is slow or noisy:

- Keep health polling at `0.5` second intervals.
- Keep the overall timeout bounded at `30` seconds.
- Do not start the companion until backend health succeeds.
- Do not open the dashboard automatically during companion launch.

- [ ] **Step 5: Final lints**

Run lints/diagnostics on changed Python files using Cursor lints and `py_compile`.

Expected: no introduced syntax or linter errors in `app.py`, `desktop_launcher.py`, or `companion.py`.
