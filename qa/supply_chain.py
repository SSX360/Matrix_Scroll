"""Generate local supply-chain evidence for GTM release candidates."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import time
import uuid
from importlib import metadata
from pathlib import Path
from typing import Any


MANIFEST_FILES = ("requirements.txt", "requirements-dev.txt", "pyproject.toml")
LOCK_FILES = (
    "requirements.lock",
    "requirements.txt.lock",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
)
PROVENANCE_FILES = (
    "dist/provenance.json",
    "dist/attestation.intoto.jsonl",
    "dist/SHA256SUMS.sig",
)
REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
EXACT_VERSION_RE = re.compile(r"==\s*([A-Za-z0-9_.!+\-]+)")


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_requirement_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    if line.startswith(("-", "--")):
        return ""
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    return line


def parse_requirements(path: Path, *, scope: str = "required") -> list[dict[str, Any]]:
    """Parse a pip requirements file into dependency records.

    This intentionally stays conservative. Unsupported pip options are skipped
    rather than guessed, because the evidence pack should avoid false precision.
    """

    if not path.exists():
        return []

    dependencies: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = _clean_requirement_line(raw_line)
        if not line:
            continue

        if " @ " in line:
            name, specifier = line.split(" @ ", 1)
            name = name.strip()
            specifier = f"@ {specifier.strip()}"
        else:
            match = REQUIREMENT_NAME_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            specifier = match.group(2).strip()

        version_match = EXACT_VERSION_RE.search(specifier)
        dependencies.append(
            {
                "name": normalized_name(name),
                "raw_name": name,
                "specifier": specifier,
                "version": version_match.group(1) if version_match else None,
                "scope": scope,
                "source": path.name,
                "raw": line,
            }
        )
    return dependencies


def installed_python_components() -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        version = dist.version
        normalized = normalized_name(name)
        component: dict[str, Any] = {
            "type": "library",
            "name": normalized,
            "version": version,
            "scope": "environment",
            "purl": f"pkg:pypi/{normalized}@{version}",
            "properties": [
                {"name": "cursor-copilot:evidence-source", "value": "installed-python-environment"},
            ],
        }
        components.append(component)
    return sorted(components, key=lambda item: (item["name"], item.get("version") or ""))


def requirement_components(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifests = [
        (root / "requirements.txt", "required"),
        (root / "requirements-dev.txt", "optional"),
    ]
    components: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    for path, scope in manifests:
        for dependency in parse_requirements(path, scope=scope):
            dependencies.append(dependency)
            component: dict[str, Any] = {
                "type": "library",
                "name": dependency["name"],
                "scope": dependency["scope"],
                "properties": [
                    {"name": "cursor-copilot:manifest", "value": dependency["source"]},
                    {"name": "cursor-copilot:specifier", "value": dependency["specifier"] or "*"},
                ],
            }
            if dependency["version"]:
                component["version"] = dependency["version"]
                component["purl"] = f"pkg:pypi/{dependency['name']}@{dependency['version']}"
            components.append(component)
    return components, dependencies


def manifest_inventory(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for relative in MANIFEST_FILES + LOCK_FILES + PROVENANCE_FILES:
        path = root / relative
        if path.exists() and path.is_file():
            files.append(
                {
                    "path": relative,
                    "sha256": file_digest(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return files


def build_bom(root: Path, *, include_environment: bool = True) -> dict[str, Any]:
    root = root.resolve()
    requirement_bom_components, dependencies = requirement_components(root)
    components = list(requirement_bom_components)
    if include_environment:
        environment_components = installed_python_components()
        known = {
            (component.get("name"), component.get("version"), component.get("scope"))
            for component in components
        }
        for component in environment_components:
            key = (component.get("name"), component.get("version"), component.get("scope"))
            if key not in known:
                components.append(component)

    components = sorted(components, key=lambda item: (item.get("name") or "", item.get("scope") or ""))
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": utc_now(),
            "tools": [
                {
                    "vendor": "Digital Rain",
                    "name": "qa.supply_chain",
                    "version": "1",
                }
            ],
            "component": {
                "type": "application",
                "name": "cursor-co-pilot",
                "version": "local",
            },
            "properties": [
                {"name": "python", "value": sys.version.split()[0]},
                {"name": "platform", "value": platform.platform()},
            ],
        },
        "components": components,
        "externalReferences": [
            {
                "type": "distribution",
                "url": str(root),
                "comment": "Local release candidate workspace",
            }
        ],
        "properties": [
            {"name": "cursor-copilot:requirements-count", "value": str(len(dependencies))},
        ],
    }


def assess_supply_chain(root: Path, bom: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    manifests = manifest_inventory(root)
    manifest_paths = {item["path"] for item in manifests}
    component_count = len(bom.get("components") or [])
    requirement_components_count = sum(
        1
        for component in bom.get("components") or []
        if any(prop.get("name") == "cursor-copilot:manifest" for prop in component.get("properties") or [])
    )
    lockfiles = sorted(path for path in manifest_paths if path in LOCK_FILES)
    provenance_files = sorted(path for path in manifest_paths if path in PROVENANCE_FILES)

    warnings: list[str] = []
    if "requirements.txt" not in manifest_paths:
        warnings.append("requirements.txt is missing from the release candidate.")
    if not lockfiles:
        warnings.append("No dependency lockfile or hash-pinned manifest was found.")
    if not provenance_files:
        warnings.append("No signed release provenance or attestation artifact was found.")
    if requirement_components_count == 0:
        warnings.append("No first-party requirement dependencies were inventoried.")

    inventory_ready = component_count > 0 and requirement_components_count > 0 and "requirements.txt" in manifest_paths
    return {
        "status": "inventory_ready" if inventory_ready else "review",
        "inventory_ready": inventory_ready,
        "component_count": component_count,
        "requirement_component_count": requirement_components_count,
        "manifest_count": len(manifests),
        "manifests": manifests,
        "lockfiles": lockfiles,
        "provenance_files": provenance_files,
        "warnings": warnings,
        "warning_count": len(warnings),
        "field_evidence_needed": [
            "Dependency vulnerability review",
            "Signed installer provenance",
            "Release artifact attestation",
        ],
    }


def generate_supply_chain_evidence(root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    bom = build_bom(root)
    assessment = assess_supply_chain(root, bom)
    sbom_path = output_dir / "supply-chain-sbom.cdx.json"
    summary_path = output_dir / "supply-chain-summary.json"

    sbom_path.write_text(json.dumps(bom, indent=2) + "\n", encoding="utf-8")
    summary = {
        "generated_at": bom["metadata"]["timestamp"],
        "root": str(root.resolve()),
        **assessment,
        "artifacts": {
            "supply_chain_sbom": str(sbom_path.resolve()),
            "supply_chain_summary": str(summary_path.resolve()),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
