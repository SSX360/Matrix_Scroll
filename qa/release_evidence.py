"""Build a GTM release evidence pack from repeatable local checks."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import identity
from qa import run_gates, supply_chain


ROOT = Path(__file__).resolve().parents[1]


def _sign_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Attach a Matrix Scroll root-of-trust signature to the manifest.

    Signing is additive evidence; if the active provider is unavailable we record
    an explicit unsigned marker rather than failing the whole evidence run.
    """
    try:
        return identity.sign_manifest(manifest)
    except Exception as exc:  # pragma: no cover - defensive
        manifest["signature"] = {"status": "unsigned", "error": str(exc)}
        return manifest
CORE_MODULES = (
    "app.py",
    "brainstorm.py",
    "chat_actions.py",
    "chat_advisor.py",
    "companion.py",
    "cursor_artifacts.py",
    "desktop_launcher.py",
    "ingest.py",
    "llm.py",
    "mcp_server.py",
    "scanner.py",
    "search.py",
    "vault.py",
    "workspace_config.py",
    "qa/run_gates.py",
    "qa/release_evidence.py",
    "qa/supply_chain.py",
)
DEFAULT_WORKSPACES = ("empty", "python", "typescript", "monorepo", "notebook", "security")
LOCAL_EXPERIMENT_NOTES = {
    "empty": {
        "scenario": "Brand-new empty project",
        "build_style": "first-run/offline-first",
        "pros": [
            "proves the product does not depend on a preconfigured active repo",
            "keeps buyer demos safe when the customer opens a blank or unfamiliar folder",
        ],
        "cons": [
            "limited project-specific guidance until the user adds files or connects sources",
        ],
        "optimization": "keep first-run prompts and vault/rule setup highly visible for empty workspaces",
    },
    "python": {
        "scenario": "Minimal Python web app",
        "build_style": "conventional app repo",
        "pros": [
            "validates language and framework detection on a common GTM demo shape",
            "exercises project-aware chat without cloud keys or live model access",
        ],
        "cons": [
            "does not yet compare deeper dependency graphs, package managers, or test runners",
        ],
        "optimization": "validate inferred install and launch commands against real Python pilot repos",
    },
    "typescript": {
        "scenario": "TypeScript frontend app",
        "build_style": "modern web app",
        "pros": [
            "validates Next and React detection for the most likely developer-facing demo path",
            "checks package-manager and SaaS SDK signals that drive setup recommendations",
        ],
        "cons": [
            "does not run a real frontend build or browser route test for generated app code",
        ],
        "optimization": "browser-test inferred frontend launch commands before customer demos",
    },
    "monorepo": {
        "scenario": "Mixed frontend/API monorepo",
        "build_style": "multi-service repo",
        "pros": [
            "validates nested manifest detection across apps and services",
            "tests whether Cursor config and mixed-language stacks survive first-run scanning",
        ],
        "cons": [
            "does not yet validate service dependency ordering or cross-service launch commands",
        ],
        "optimization": "validate cross-service command ordering before enterprise pilots",
    },
    "notebook": {
        "scenario": "Notebook-heavy analysis project",
        "build_style": "data-science workflow",
        "pros": [
            "validates notebook inventory and out-of-order execution warnings",
            "gives Data Analytics users a concrete local QA lane",
        ],
        "cons": [
            "does not execute kernels or validate notebook outputs",
        ],
        "optimization": "surface notebook health warnings more prominently in the product UI",
    },
    "security": {
        "scenario": "Security-sensitive app fixture",
        "build_style": "secret-redaction and local-trust workflow",
        "pros": [
            "proves project scanning can surface useful stack data without exposing known secret values",
            "keeps the software-node security story grounded in a repeatable local redaction gate",
        ],
        "cons": [
            "does not replace a full secret-scanning, SBOM, SAST, or artifact-attestation pipeline",
        ],
        "optimization": "expand software launch evidence with SBOM, dependency vulnerability review, and signed build provenance before paid device GTM",
    },
}


def utc_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def run_command(name: str, args: list[str], *, timeout_s: float = 180) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return {
            "name": name,
            "command": args,
            "passed": completed.returncode == 0,
            "exit_code": completed.returncode,
            "duration_ms": int((time.time() - started) * 1000),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": args,
            "passed": False,
            "exit_code": None,
            "duration_ms": int((time.time() - started) * 1000),
            "stdout_tail": (exc.stdout or "")[-4000:],
            "stderr_tail": f"Timed out after {timeout_s} seconds\n{exc.stderr or ''}"[-4000:],
        }


def gate_status(report: dict[str, Any], gate_name: str) -> bool:
    return any(
        gate.get("name") == gate_name and bool(gate.get("passed"))
        for gate in report.get("gates", [])
    )


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def summarize_gate_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total = len(reports)
    passed = sum(1 for report in reports.values() if report.get("passed"))
    degraded_success = sum(
        1 for report in reports.values() if gate_status(report, "chat_offline_project_answer")
    )
    diagnostics_success = sum(
        1 for report in reports.values() if gate_status(report, "redacted_diagnostics")
    )
    launch_readiness_success = sum(
        1 for report in reports.values() if gate_status(report, "launch_readiness_static_validation")
    )
    no_stale_success = sum(
        1 for report in reports.values() if gate_status(report, "no_stale_workspace_leak")
    )
    project_secret_success = sum(
        1 for report in reports.values() if gate_status(report, "project_secret_redaction")
    )
    return {
        "workspace_count": total,
        "workspace_pass_count": passed,
        "fresh_project_qa_pass_rate": percent(passed, total),
        "degraded_chat_success_rate": percent(degraded_success, total),
        "diagnostics_redaction_rate": percent(diagnostics_success, total),
        "launch_readiness_validation_rate": percent(launch_readiness_success, total),
        "project_secret_redaction_rate": percent(project_secret_success, total),
        "stale_workspace_leak_count": total - no_stale_success,
    }


def build_kpis(
    gate_summary: dict[str, Any],
    supply_chain_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    kpis = [
        {
            "id": "fresh_project_qa_pass_rate",
            "label": "Fresh-project QA pass rate",
            "target": ">=95%",
            "actual": f"{gate_summary['fresh_project_qa_pass_rate']}%",
            "status": "pass" if gate_summary["fresh_project_qa_pass_rate"] >= 95 else "fail",
            "source": "qa.run_gates synthetic workspace fixtures",
        },
        {
            "id": "chat_degraded_mode_success",
            "label": "Offline/degraded chat success",
            "target": ">=95%",
            "actual": f"{gate_summary['degraded_chat_success_rate']}%",
            "status": "pass" if gate_summary["degraded_chat_success_rate"] >= 95 else "fail",
            "source": "chat_offline_project_answer gate",
        },
        {
            "id": "diagnostics_redaction",
            "label": "Diagnostics redaction coverage",
            "target": "100%",
            "actual": f"{gate_summary['diagnostics_redaction_rate']}%",
            "status": "pass" if gate_summary["diagnostics_redaction_rate"] == 100 else "fail",
            "source": "redacted_diagnostics gate",
        },
        {
            "id": "launch_readiness_validation",
            "label": "Launch command static validation",
            "target": "100%",
            "actual": f"{gate_summary['launch_readiness_validation_rate']}%",
            "status": "pass" if gate_summary["launch_readiness_validation_rate"] == 100 else "fail",
            "source": "launch_readiness_static_validation gate",
        },
        {
            "id": "project_secret_redaction",
            "label": "Project secret redaction",
            "target": "100%",
            "actual": f"{gate_summary['project_secret_redaction_rate']}%",
            "status": "pass" if gate_summary["project_secret_redaction_rate"] == 100 else "fail",
            "source": "project_secret_redaction gate",
        },
        {
            "id": "stale_workspace_leaks",
            "label": "Stale workspace leaks",
            "target": "0",
            "actual": str(gate_summary["stale_workspace_leak_count"]),
            "status": "pass" if gate_summary["stale_workspace_leak_count"] == 0 else "fail",
            "source": "no_stale_workspace_leak gate",
        },
    ]
    if supply_chain_summary is not None:
        kpis.append(
            {
                "id": "supply_chain_inventory",
                "label": "SBOM/dependency inventory",
                "target": "generated for every release",
                "actual": f"{supply_chain_summary.get('component_count', 0)} components",
                "status": "pass" if supply_chain_summary.get("inventory_ready") else "fail",
                "source": "qa.supply_chain CycloneDX-shaped SBOM",
            }
        )
    kpis.extend(
        [
            {
                "id": "install_success_rate",
                "label": "Install success rate",
                "target": ">=90%",
                "actual": "needs alpha/pilot data",
                "status": "needs_field_data",
                "source": "customer or clean-profile install telemetry",
            },
            {
                "id": "first_week_retention",
                "label": "First-week retained usage",
                "target": ">=40%",
                "actual": "needs alpha/pilot data",
                "status": "needs_field_data",
                "source": "customer usage follow-up or telemetry",
            },
        ]
    )
    return kpis


def build_experiment_matrix(reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    experiments: list[dict[str, Any]] = []
    for workspace, report in reports.items():
        notes = LOCAL_EXPERIMENT_NOTES.get(workspace, {})
        experiments.append(
            {
                "workspace": workspace,
                "scenario": notes.get("scenario", workspace),
                "build_style": notes.get("build_style", "local fixture"),
                "passed": bool(report.get("passed")),
                "duration_ms": report.get("duration_ms"),
                "pros": notes.get("pros", []),
                "cons": notes.get("cons", []),
                "optimization": notes.get("optimization", ""),
                "validated_gates": [
                    gate.get("name")
                    for gate in report.get("gates", [])
                    if gate.get("passed")
                ],
            }
        )
    return experiments


def git_metadata() -> dict[str, Any]:
    def run_git(args: list[str]) -> str | None:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    return {
        "commit": run_git(["rev-parse", "HEAD"]),
        "branch": run_git(["branch", "--show-current"]),
        "dirty": bool(run_git(["status", "--porcelain"])),
    }


def release_decision(
    commands: list[dict[str, Any]],
    gate_reports: dict[str, dict[str, Any]],
    kpis: list[dict[str, Any]],
    supply_chain_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    field_evidence_needed: list[str] = []
    for command in commands:
        if not command.get("passed"):
            blockers.append(f"{command['name']} failed")
    for workspace, report in gate_reports.items():
        if not report.get("passed"):
            blockers.append(f"{workspace} workspace QA gates failed")
    for kpi in kpis:
        if kpi["status"] == "fail":
            blockers.append(f"{kpi['label']} below target")
        elif kpi["status"] == "needs_field_data":
            field_evidence_needed.append(kpi["label"])
    if supply_chain_summary is not None:
        for item in supply_chain_summary.get("field_evidence_needed", []):
            if item not in field_evidence_needed:
                field_evidence_needed.append(item)

    return {
        "software_release_candidate": not blockers,
        "device_gtm_ready": not blockers and not field_evidence_needed,
        "blockers": blockers,
        "field_evidence_needed": field_evidence_needed,
    }


def build_summary_markdown(manifest: dict[str, Any]) -> str:
    decision = manifest["release_decision"]
    lines = [
        "# Digital Rain Release Evidence",
        "",
        f"- Run ID: `{manifest['run_id']}`",
        f"- Generated: `{manifest['generated_at']}`",
        f"- Software release candidate: `{str(decision['software_release_candidate']).lower()}`",
        f"- Device GTM ready: `{str(decision['device_gtm_ready']).lower()}`",
    ]
    signature = manifest.get("signature") or {}
    if signature.get("value"):
        lines.append(
            f"- Signed by: `{signature.get('device_id', 'unknown')}` "
            f"({signature.get('mode', 'unknown')} root of trust)"
        )
    lines += [
        "",
        "## Checks",
        "",
        "| Check | Result | Duration |",
        "| --- | --- | ---: |",
    ]
    for command in manifest["commands"]:
        result = "pass" if command["passed"] else "fail"
        lines.append(f"| {command['name']} | {result} | {command['duration_ms']} ms |")

    lines.extend(["", "## Synthetic Workspaces", "", "| Workspace | Result | Duration |", "| --- | --- | ---: |"])
    for workspace, report in manifest["qa_reports"].items():
        result = "pass" if report["passed"] else "fail"
        lines.append(f"| {workspace} | {result} | {report['duration_ms']} ms |")

    supply_chain_summary = manifest.get("supply_chain")
    if supply_chain_summary:
        lines.extend(
            [
                "",
                "## Supply Chain Evidence",
                "",
                "| Evidence | Result | Detail |",
                "| --- | --- | --- |",
                (
                    "| SBOM/dependency inventory | "
                    f"{supply_chain_summary.get('status', 'review')} | "
                    f"{supply_chain_summary.get('component_count', 0)} components |"
                ),
                (
                    "| Manifest inventory | "
                    f"{supply_chain_summary.get('manifest_count', 0)} files | "
                    f"{supply_chain_summary.get('warning_count', 0)} warnings |"
                ),
            ]
        )

    lines.extend(["", "## GTM KPIs", "", "| KPI | Target | Actual | Status |", "| --- | --- | --- | --- |"])
    for kpi in manifest["kpis"]:
        lines.append(f"| {kpi['label']} | {kpi['target']} | {kpi['actual']} | {kpi['status']} |")

    lines.extend(
        [
            "",
            "## Local Experiment Matrix",
            "",
            "| Scenario | Build Style | Result | Optimization Signal |",
            "| --- | --- | --- | --- |",
        ]
    )
    for experiment in manifest["local_experiments"]:
        result = "pass" if experiment["passed"] else "fail"
        lines.append(
            f"| {experiment['scenario']} | {experiment['build_style']} | "
            f"{result} | {experiment['optimization']} |"
        )

    if decision["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in decision["blockers"])
    if decision["field_evidence_needed"]:
        lines.extend(["", "## Field Evidence Needed", ""])
        lines.extend(f"- {item}" for item in decision["field_evidence_needed"])

    lines.append("")
    return "\n".join(lines)


def generate_evidence(
    output_root: Path,
    *,
    run_id: str | None = None,
    timeout_s: float = 45,
    live_model: bool = False,
    skip_unit_tests: bool = False,
    skip_compile: bool = False,
    workspaces: tuple[str, ...] = DEFAULT_WORKSPACES,
) -> dict[str, Any]:
    run_id = run_id or f"release-evidence-{utc_stamp()}"
    evidence_dir = (output_root / run_id).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)

    commands: list[dict[str, Any]] = []
    if not skip_unit_tests:
        commands.append(
            run_command(
                "unit_tests",
                [sys.executable, "-m", "unittest", "discover", "-v", "tests"],
                timeout_s=240,
            )
        )
    if not skip_compile:
        commands.append(
            run_command(
                "compile_core_modules",
                [sys.executable, "-m", "py_compile", *CORE_MODULES],
                timeout_s=120,
            )
        )

    qa_reports: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, str] = {}
    for workspace in workspaces:
        report = run_gates.run_gates(workspace, timeout_s=timeout_s, live_model=live_model)
        qa_reports[workspace] = report
        report_path = evidence_dir / f"qa-{workspace}-report.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        artifacts[f"qa_{workspace}_report"] = str(report_path)

    supply_chain_summary = supply_chain.generate_supply_chain_evidence(ROOT, evidence_dir)
    artifacts.update(supply_chain_summary.get("artifacts", {}))

    gate_summary = summarize_gate_reports(qa_reports)
    kpis = build_kpis(gate_summary, supply_chain_summary)
    local_experiments = build_experiment_matrix(qa_reports)
    manifest = {
        "schema": "cursor_copilot_release_evidence.v1",
        "product": "Digital Rain",
        "run_id": run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": git_metadata(),
        "commands": commands,
        "qa_summary": gate_summary,
        "qa_reports": qa_reports,
        "supply_chain": supply_chain_summary,
        "local_experiments": local_experiments,
        "kpis": kpis,
        "release_decision": release_decision(commands, qa_reports, kpis, supply_chain_summary),
        "artifacts": artifacts,
    }
    manifest_path = evidence_dir / "manifest.json"
    summary_path = evidence_dir / "summary.md"
    manifest["artifacts"]["manifest"] = str(manifest_path)
    manifest["artifacts"]["summary"] = str(summary_path)
    manifest = _sign_manifest(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(build_summary_markdown(manifest), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a GTM release evidence pack.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "out" / "release-evidence")
    parser.add_argument("--run-id")
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--live-model", action="store_true")
    parser.add_argument("--skip-unit-tests", action="store_true")
    parser.add_argument("--skip-compile", action="store_true")
    parser.add_argument(
        "--workspace",
        action="append",
        choices=DEFAULT_WORKSPACES,
        help="Workspace fixture to include. May be repeated. Defaults to all fixtures.",
    )
    args = parser.parse_args(argv)

    manifest = generate_evidence(
        args.output_dir,
        run_id=args.run_id,
        timeout_s=args.timeout,
        live_model=args.live_model,
        skip_unit_tests=args.skip_unit_tests,
        skip_compile=args.skip_compile,
        workspaces=tuple(args.workspace or DEFAULT_WORKSPACES),
    )
    print(json.dumps({
        "run_id": manifest["run_id"],
        "software_release_candidate": manifest["release_decision"]["software_release_candidate"],
        "device_gtm_ready": manifest["release_decision"]["device_gtm_ready"],
        "summary": manifest["artifacts"]["summary"],
        "manifest": manifest["artifacts"]["manifest"],
    }, indent=2))
    return 0 if manifest["release_decision"]["software_release_candidate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
