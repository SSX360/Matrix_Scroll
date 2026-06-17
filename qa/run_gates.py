"""Run GTM production-readiness gates against a fresh synthetic workspace.

The harness intentionally ignores the user's active workspace pointer. This keeps
release checks honest: a passing run proves first-run behavior works for a brand
new project, not only for whatever repo happened to be active locally.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_WORKSPACE_MARKERS = tuple(
    marker.strip().lower()
    for marker in os.environ.get(
        "COPILOT_FORBIDDEN_WORKSPACE_MARKERS",
        "legacy-demo-project;archived-demo-workspace",
    ).split(";")
    if marker.strip()
)

# Optional dev-team notifier. Kept defensive so QA never breaks if the notifier
# or its deps are unavailable (e.g. run from an unusual working directory).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    import env_loader
    import notifications

    env_loader.load()
except Exception:  # pragma: no cover - notifier is strictly optional
    notifications = None  # type: ignore[assignment]


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_workspace(kind: str, base_dir: Path | None = None) -> Path:
    root = Path(
        tempfile.mkdtemp(prefix=f"cursor-copilot-{kind}-qa-", dir=str(base_dir) if base_dir else None)
    ).resolve()
    if kind == "empty":
        return root
    if kind == "python":
        _write(
            root / "README.md",
            "# Synthetic Flask Project\n\nA clean QA fixture for first-run Digital Rain checks.\n",
        )
        _write(root / "requirements.txt", "flask>=3.0\nrequests>=2.31\n")
        _write(
            root / "app.py",
            "from flask import Flask\n\napp = Flask(__name__)\n\n@app.get('/')\ndef home():\n    return 'ok'\n",
        )
        return root
    if kind == "typescript":
        _write(
            root / "README.md",
            "# Synthetic Next Project\n\nA local TypeScript frontend fixture for GTM QA.\n",
        )
        _write(
            root / "package.json",
            json.dumps(
                {
                    "scripts": {"dev": "next dev", "build": "next build"},
                    "dependencies": {
                        "next": "^15.0.0",
                        "react": "^19.0.0",
                        "react-dom": "^19.0.0",
                        "@supabase/supabase-js": "^2.0.0",
                        "@clerk/nextjs": "^6.0.0",
                    },
                    "devDependencies": {"typescript": "^5.0.0"},
                },
                indent=2,
            ),
        )
        _write(root / "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        _write(root / "tsconfig.json", json.dumps({"compilerOptions": {"strict": True}}, indent=2))
        _write(
            root / "app" / "page.tsx",
            "export default function Page() {\n  return <main>Launch QA</main>;\n}\n",
        )
        return root
    if kind == "monorepo":
        _write(
            root / "README.md",
            "# Synthetic Monorepo\n\nA mixed frontend/API fixture for local QA experiments.\n",
        )
        _write(
            root / "package.json",
            json.dumps(
                {
                    "private": True,
                    "workspaces": ["apps/*", "services/*"],
                    "devDependencies": {"turbo": "^2.0.0"},
                },
                indent=2,
            ),
        )
        _write(root / "pnpm-workspace.yaml", "packages:\n  - apps/*\n  - services/*\n")
        _write(root / "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        _write(
            root / "apps" / "web" / "package.json",
            json.dumps(
                {
                    "scripts": {"dev": "vite --host 127.0.0.1", "build": "vite build"},
                    "dependencies": {
                        "@vitejs/plugin-react": "^5.0.0",
                        "vite": "^7.0.0",
                        "react": "^19.0.0",
                        "react-dom": "^19.0.0",
                        "@sentry/react": "^9.0.0",
                    },
                    "devDependencies": {"typescript": "^5.0.0"},
                },
                indent=2,
            ),
        )
        _write(root / "apps" / "web" / "src" / "App.tsx", "export function App() { return null; }\n")
        _write(
            root / "services" / "api" / "pyproject.toml",
            "[project]\nname = \"synthetic-api\"\ndependencies = [\"fastapi\", \"uvicorn\", \"psycopg[binary]\"]\n",
        )
        _write(root / "services" / "api" / "main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
        _write(root / ".cursor" / "rules" / "gtm.mdc", "---\nalwaysApply: true\n---\nUse GTM QA evidence.\n")
        return root
    if kind == "notebook":
        _write(root / "README.md", "# Synthetic Notebook Project\n")
        _write(
            root / "analysis.ipynb",
            json.dumps(
                {
                    "cells": [
                        {
                            "cell_type": "code",
                            "execution_count": 2,
                            "metadata": {},
                            "outputs": [],
                            "source": ["import pandas as pd\n", "df = pd.DataFrame()\n"],
                        },
                        {
                            "cell_type": "code",
                            "execution_count": 1,
                            "metadata": {},
                            "outputs": [],
                            "source": ["model = 'demo'\n"],
                        },
                    ],
                    "metadata": {},
                    "nbformat": 4,
                    "nbformat_minor": 5,
                },
                indent=2,
            ),
        )
        return root
    if kind == "security":
        _write(
            root / "README.md",
            "# Synthetic Secure Node Project\n\n"
            "Use INTERNAL_API_KEY=readme-secret-123 for local-only development.\n",
        )
        _write(
            root / "package.json",
            json.dumps(
                {
                    "scripts": {
                        "dev": "SERVICE_TOKEN=script-secret-456 vite --host 127.0.0.1",
                        "build": "vite build",
                    },
                    "dependencies": {"vite": "^7.0.0", "react": "^19.0.0"},
                    "devDependencies": {"typescript": "^5.0.0"},
                },
                indent=2,
            ),
        )
        _write(root / ".env.local", "DATABASE_PASSWORD=env-secret-789\n")
        _write(root / "src" / "App.tsx", "export function App() { return null; }\n")
        return root
    raise ValueError(f"Unknown workspace fixture: {kind}")


def contains_forbidden_workspace_reference(payload: Any) -> bool:
    text = json.dumps(payload, sort_keys=True).lower()
    return any(marker in text for marker in FORBIDDEN_WORKSPACE_MARKERS)


def component_with(
    profile: dict[str, Any],
    path: str,
    *,
    kind: str | None = None,
    frameworks: tuple[str, ...] = (),
) -> bool:
    for component in profile.get("components") or []:
        if component.get("path") != path:
            continue
        if kind and component.get("kind") != kind:
            continue
        component_frameworks = set(component.get("frameworks") or [])
        if not all(framework in component_frameworks for framework in frameworks):
            continue
        return True
    return False


def suggested_command(profile: dict[str, Any], cwd: str, command: str) -> bool:
    return any(
        item.get("cwd") == cwd and item.get("command") == command
        for item in profile.get("suggested_commands") or []
    )


def launch_readiness_passed(profile: dict[str, Any]) -> bool:
    readiness = profile.get("launch_readiness") or {}
    return (
        readiness.get("status") in {"ready", "no_commands"}
        and int(readiness.get("blocking_issue_count") or 0) == 0
    )


def http_json(url: str, *, timeout: float = 10) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def post_json_sse(url: str, payload: dict[str, Any], *, timeout: float = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    events: list[dict[str, Any]] = []
    current_event = "message"
    with urllib.request.urlopen(req, timeout=timeout) as response:
        for raw in response:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("event: "):
                current_event = line[7:].strip()
                continue
            if not line.startswith("data: "):
                continue
            body = line[6:]
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
            events.append({"event": current_event, "data": parsed})
            if current_event == "done":
                break
    tokens = [str(item["data"]) for item in events if item["event"] == "token"]
    errors = [str(item["data"]) for item in events if item["event"] == "error"]
    return {"events": events, "text": "".join(tokens), "errors": errors}


def start_backend(workspace: Path, port: int, *, live_model: bool) -> subprocess.Popen:
    env = os.environ.copy()
    secret_keys = {"ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"}
    for key in list(env):
        if key.upper() in secret_keys:
            env.pop(key, None)
    env.update(
        {
            "COPILOT_WORKSPACE": str(workspace),
            "PORT": str(port),
            "OPEN_BROWSER": "0",
            "LLM_BACKEND": "ollama",
        }
    )
    if not live_model:
        env["OLLAMA_URL"] = "http://127.0.0.1:9"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
    )


def wait_for_health(base_url: str, timeout_s: float) -> Any:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return http_json(f"{base_url}/api/health", timeout=3)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"backend did not become healthy: {last_error}")


def _tail_pipe(pipe: Any) -> str:
    if pipe is None:
        return ""
    try:
        return pipe.read()[-4000:]
    except Exception:
        return ""


def run_gates(workspace_kind: str, *, timeout_s: float = 45, live_model: bool = False) -> dict[str, Any]:
    started = time.time()
    workspace = create_workspace(workspace_kind)
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    gates: list[GateResult] = []
    process: subprocess.Popen | None = None
    stdout_tail = ""
    stderr_tail = ""
    try:
        process = start_backend(workspace, port, live_model=live_model)
        health = wait_for_health(base_url, timeout_s)
        gates.append(
            GateResult(
                "health",
                bool(health.get("chunks")) and "llm" in health,
                "backend returned index and LLM status",
                {"active_llm": (health.get("llm") or {}).get("active"), "chunks": health.get("chunks")},
            )
        )

        workspace_status = http_json(f"{base_url}/api/workspace/status", timeout=10)
        gates.append(
            GateResult(
                "fresh_workspace_binding",
                Path(workspace_status.get("workspace", "")).resolve() == workspace,
                "backend is bound to the synthetic workspace",
                {"workspace": workspace_status.get("workspace")},
            )
        )

        diagnostics = http_json(f"{base_url}/api/diagnostics", timeout=10)
        diagnostic_workspace = diagnostics.get("workspace") or {}
        diagnostic_env = diagnostics.get("environment") or {}
        secret_keys = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
        diagnostics_passed = (
            diagnostics.get("product") == "Digital Rain"
            and diagnostics.get("diagnostics_version") == 1
            and bool((diagnostics.get("redaction") or {}).get("secrets_redacted"))
            and Path(diagnostic_workspace.get("path", "")).resolve() == workspace
            and all(diagnostic_env.get(key) in ("<unset>", "<redacted:set>") for key in secret_keys)
        )
        gates.append(
            GateResult(
                "redacted_diagnostics",
                diagnostics_passed,
                "diagnostics bundle is versioned, workspace-bound, and secret-redacted",
                {
                    "workspace": diagnostic_workspace.get("path"),
                    "diagnostics_version": diagnostics.get("diagnostics_version"),
                    "secret_fields": {key: diagnostic_env.get(key) for key in secret_keys},
                },
            )
        )

        project_status = http_json(f"{base_url}/api/project/status", timeout=15)
        profile = project_status.get("profile") or {}
        gates.append(
            GateResult(
                "project_status_profile",
                Path(profile.get("path", "")).resolve() == workspace,
                "project status reports the synthetic project path",
                {
                    "path": profile.get("path"),
                    "languages": profile.get("languages", []),
                    "frameworks": profile.get("frameworks", []),
                },
            )
        )
        readiness = profile.get("launch_readiness") or {}
        gates.append(
            GateResult(
                "launch_readiness_static_validation",
                launch_readiness_passed(profile),
                "inferred commands are statically validated without executing installs or servers",
                {
                    "status": readiness.get("status"),
                    "command_count": readiness.get("command_count"),
                    "warning_count": readiness.get("warning_count"),
                    "blocking_issue_count": readiness.get("blocking_issue_count"),
                    "launch_order": [
                        {
                            "cwd": item.get("cwd"),
                            "command": item.get("command"),
                            "stage": item.get("stage"),
                            "safety": item.get("safety"),
                        }
                        for item in (readiness.get("launch_order") or [])[:8]
                    ],
                },
            )
        )
        if workspace_kind == "empty":
            fixture_passed = not profile.get("languages") and not profile.get("frameworks")
            fixture_detail = "empty fixture has no detected stack"
            fixture_data = {
                "languages": profile.get("languages", []),
                "frameworks": profile.get("frameworks", []),
            }
        elif workspace_kind == "python":
            fixture_passed = "python" in profile.get("languages", []) and "flask" in profile.get("frameworks", [])
            fixture_detail = "python fixture detects Python and Flask"
            fixture_data = {
                "languages": profile.get("languages", []),
                "frameworks": profile.get("frameworks", []),
            }
        elif workspace_kind == "typescript":
            fixture_passed = (
                "typescript" in profile.get("languages", [])
                and "next" in profile.get("frameworks", [])
                and "react" in profile.get("frameworks", [])
                and "pnpm" in profile.get("package_managers", [])
                and "supabase" in profile.get("notable_sdks", [])
                and component_with(profile, ".", kind="node", frameworks=("next", "react"))
                and suggested_command(profile, ".", "pnpm install")
                and suggested_command(profile, ".", "pnpm dev")
                and suggested_command(profile, ".", "pnpm build")
                and (profile.get("launch_readiness") or {}).get("status") == "ready"
            )
            fixture_detail = "typescript fixture detects Next, React, pnpm, Supabase, and runnable commands"
            fixture_data = {
                "languages": profile.get("languages", []),
                "frameworks": profile.get("frameworks", []),
                "package_managers": profile.get("package_managers", []),
                "notable_sdks": profile.get("notable_sdks", []),
                "signals": profile.get("signals", []),
                "components": profile.get("components", []),
                "suggested_commands": profile.get("suggested_commands", []),
                "launch_readiness": profile.get("launch_readiness", {}),
            }
        elif workspace_kind == "monorepo":
            fixture_passed = (
                "typescript" in profile.get("languages", [])
                and "python" in profile.get("languages", [])
                and "react" in profile.get("frameworks", [])
                and "vite" in profile.get("frameworks", [])
                and "fastapi" in profile.get("frameworks", [])
                and "pnpm" in profile.get("package_managers", [])
                and "cursor-config" in profile.get("signals", [])
                and component_with(profile, "apps/web", kind="node", frameworks=("react", "vite"))
                and component_with(profile, "services/api", kind="python", frameworks=("fastapi",))
                and suggested_command(profile, ".", "pnpm install")
                and suggested_command(profile, "apps/web", "pnpm dev")
                and suggested_command(profile, "services/api", "python -m uvicorn main:app --reload")
                and (profile.get("launch_readiness") or {}).get("status") == "ready"
            )
            fixture_detail = "monorepo fixture detects nested frontend, API, Cursor config, and service commands"
            fixture_data = {
                "languages": profile.get("languages", []),
                "frameworks": profile.get("frameworks", []),
                "package_managers": profile.get("package_managers", []),
                "notable_sdks": profile.get("notable_sdks", []),
                "manifests": profile.get("manifests", []),
                "signals": profile.get("signals", []),
                "components": profile.get("components", []),
                "suggested_commands": profile.get("suggested_commands", []),
                "launch_readiness": profile.get("launch_readiness", {}),
            }
        elif workspace_kind == "notebook":
            notebooks = profile.get("notebooks") or []
            fixture_passed = any(
                nb.get("filename") == "analysis.ipynb"
                and nb.get("execution_health") == "out_of_order"
                for nb in notebooks
            )
            fixture_detail = "notebook fixture detects out-of-order execution"
            fixture_data = {"notebooks": notebooks}
        else:
            security = profile.get("security_posture") or {}
            fixture_passed = (
                "secret-file" in profile.get("signals", [])
                and security.get("status") == "review"
                and int(security.get("secret_file_count") or 0) >= 1
                and int(security.get("redacted_value_count") or 0) >= 2
                and (profile.get("launch_readiness") or {}).get("status") == "ready"
            )
            fixture_detail = "security fixture detects sensitive files and redacts surfaced secret values"
            fixture_data = {
                "signals": profile.get("signals", []),
                "security_posture": security,
                "readme_excerpt": profile.get("readme_excerpt", ""),
                "components": profile.get("components", []),
                "launch_readiness": profile.get("launch_readiness", {}),
            }
        gates.append(
            GateResult(
                "fixture_expectations",
                fixture_passed,
                fixture_detail,
                fixture_data,
            )
        )

        brainstorm = http_json(f"{base_url}/api/brainstorm?limit=3", timeout=15)
        gates.append(
            GateResult(
                "brainstorm_first_run",
                bool(brainstorm.get("suggestions")) and brainstorm.get("workspace") == str(workspace),
                "brainstorm returns first-run suggestions for the synthetic workspace",
                {"suggestion_count": len(brainstorm.get("suggestions") or [])},
            )
        )

        chat = post_json_sse(
            f"{base_url}/api/chat",
            {"message": "scan my project and summarize the stack", "history": []},
            timeout=30,
        )
        gates.append(
            GateResult(
                "chat_offline_project_answer",
                bool(chat["text"]) and not chat["errors"],
                "chat can answer project-scan request without cloud or live model access",
                {"sample": chat["text"][:240]},
            )
        )

        leak_payload = {
            "health": health,
            "workspace_status": workspace_status,
            "diagnostics": diagnostics,
            "project_status": project_status,
            "brainstorm": brainstorm,
            "chat": chat,
        }
        sentinel_secrets = ("readme-secret-123", "script-secret-456", "env-secret-789")
        serialized_payload = json.dumps(leak_payload, sort_keys=True)
        leaked_sentinels = [secret for secret in sentinel_secrets if secret in serialized_payload]
        gates.append(
            GateResult(
                "project_secret_redaction",
                not leaked_sentinels,
                "project scan, diagnostics, brainstorm, and chat payloads do not expose sentinel secret values",
                {"leaked_secret_count": len(leaked_sentinels)},
            )
        )
        gates.append(
            GateResult(
                "no_stale_workspace_leak",
                not contains_forbidden_workspace_reference(leak_payload),
                "responses do not contain stale production/demo workspace markers",
                {"forbidden_marker_count": len(FORBIDDEN_WORKSPACE_MARKERS)},
            )
        )
    except Exception as exc:  # noqa: BLE001 - captured in report for release triage
        gates.append(GateResult("harness_exception", False, str(exc)))
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            stdout_tail = _tail_pipe(process.stdout)
            stderr_tail = _tail_pipe(process.stderr)
        shutil.rmtree(workspace, ignore_errors=True)

    passed = all(gate.passed for gate in gates)
    return {
        "passed": passed,
        "workspace_kind": workspace_kind,
        "duration_ms": int((time.time() - started) * 1000),
        "base_url": base_url,
        "gates": [gate.__dict__ for gate in gates],
        "process": {"stdout_tail": stdout_tail, "stderr_tail": stderr_tail},
    }


def _notify_gate_result(workspace_kind: str, report: dict[str, Any]) -> None:
    if notifications is None or not notifications.enabled("cicd"):
        return
    gates = report.get("gates") or []
    failed = [g.get("name") for g in gates if not g.get("passed")]
    passed = report.get("passed")
    emoji = ":white_check_mark:" if passed else ":x:"
    status = "PASS" if passed else "FAIL"
    text = (
        f"{emoji} QA gates {status} — workspace `{workspace_kind}` "
        f"({len(gates)} gates, {report.get('duration_ms', 0)} ms)"
    )
    if failed:
        text += "\nFailed: " + ", ".join(f"`{n}`" for n in failed)
    notifications.notify("cicd", text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Digital Rain GTM QA gates.")
    parser.add_argument(
        "--workspace",
        choices=["empty", "python", "typescript", "monorepo", "notebook", "security"],
        default="empty",
    )
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--live-model",
        action="store_true",
        help="Use the configured Ollama endpoint instead of the deterministic offline fallback path.",
    )
    args = parser.parse_args(argv)

    report = run_gates(args.workspace, timeout_s=args.timeout, live_model=args.live_model)
    text = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    _notify_gate_result(args.workspace, report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
