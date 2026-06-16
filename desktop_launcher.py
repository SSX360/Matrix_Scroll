from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = int(os.environ.get("PORT", "59712"))
COMPANION_LOCK_PORT = 52809
HEALTH_TIMEOUT_SECONDS = 30
HEALTH_REQUEST_TIMEOUT_SECONDS = 5.0

_PLACEHOLDER_WORKSPACE = "${workspaceFolder}"


def _resolve_mcp_env_value(key: str, value: str) -> str | None:
    """Expand MCP env placeholders from the real OS environment."""
    if value == _PLACEHOLDER_WORKSPACE:
        return None
    if value.startswith("${env:") and value.endswith("}"):
        var_name = value[6:-1]
        resolved = os.environ.get(var_name, "").strip()
        return resolved or None
    return value


def load_mcp_env(config_path: Path) -> dict[str, str]:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    server = data.get("mcpServers", {}).get("cursor-copilot", {})
    env = server.get("env", {})
    if not isinstance(env, dict):
        return {}
    resolved: dict[str, str] = {}
    for key, value in env.items():
        if value is None:
            continue
        out = _resolve_mcp_env_value(str(key), str(value))
        if out is not None:
            resolved[str(key)] = out
    return resolved


def build_backend_env(extra_env: dict[str, str], port: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra_env)
    ws = env.get("COPILOT_WORKSPACE", "").strip()
    if not ws or ws == _PLACEHOLDER_WORKSPACE:
        try:
            import workspace_config as wc

            active = wc.get_active_workspace_raw()
            if active:
                env["COPILOT_WORKSPACE"] = str(active)
        except Exception:
            pass
    env["PORT"] = str(port)
    env["OPEN_BROWSER"] = "0"
    return env


def is_port_in_use(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_companion_running(lock_port: int = COMPANION_LOCK_PORT) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", lock_port))
        return False
    except OSError:
        return True
    finally:
        probe.close()


def is_backend_healthy(health_url: str, timeout: float = HEALTH_REQUEST_TIMEOUT_SECONDS) -> bool:
    try:
        with request.urlopen(health_url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, error.URLError):
        return False


def wait_for_backend(
    health_url: str,
    timeout_seconds: int = HEALTH_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_backend_healthy(health_url):
            return True, ""
        time.sleep(0.5)

    elapsed = timeout_seconds
    if is_port_in_use("127.0.0.1", DEFAULT_PORT):
        detail = (
            f"Port {DEFAULT_PORT} is in use but /api/health did not respond within "
            f"{elapsed}s. Stop the stale backend process and retry."
        )
    else:
        detail = f"Backend did not become healthy at {health_url} within {elapsed}s."
    return False, detail


def python_executable() -> Path:
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def _creationflags() -> int:
    return subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0


def start_backend(port: int) -> subprocess.Popen:
    env = build_backend_env(load_mcp_env(ROOT / ".cursor" / "mcp.json"), port)
    return subprocess.Popen(
        [str(python_executable()), str(ROOT / "app.py")],
        cwd=str(ROOT),
        env=env,
        creationflags=_creationflags(),
    )


def start_companion() -> subprocess.Popen:
    return subprocess.Popen(
        [str(python_executable()), str(ROOT / "companion.py")],
        cwd=str(ROOT),
        creationflags=_creationflags(),
    )


def main() -> int:
    port = DEFAULT_PORT
    health_url = f"http://127.0.0.1:{port}/api/health"

    if is_backend_healthy(health_url):
        print(f"Backend already healthy at {health_url}", flush=True)
    elif is_port_in_use("127.0.0.1", port):
        print(
            f"Port {port} is already in use but {health_url} is not healthy. "
            "Stop the stale backend process and retry.",
            file=sys.stderr,
        )
        return 1
    else:
        print(f"Starting backend on port {port}...", flush=True)
        start_backend(port)
        healthy, detail = wait_for_backend(health_url)
        if not healthy:
            print(detail, file=sys.stderr)
            return 1

    if is_companion_running():
        print("Floating companion is already running.", flush=True)
        return 0

    print("Launching floating companion...", flush=True)
    start_companion()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
