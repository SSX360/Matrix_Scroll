"""
Project scanner — reads a project directory and infers a "stack profile".

This is the co-pilot's eyes: it answers "what is the user actually building?"
from concrete on-disk signals (manifests, lockfiles, config files, the file tree,
and the README) so recommendations are grounded in the real project rather than a
vague description. Pure stdlib, no third-party dependencies.

Output is a plain dict (JSON-serialisable) consumed by the MCP tools:

    {
      "path": "...",
      "languages": ["python", "typescript"],
      "package_managers": ["pip", "npm"],
      "frameworks": ["flask", "next"],
      "notable_sdks": ["stripe", "supabase"],
      "manifests": ["package.json", "requirements.txt"],
      "signals": ["Dockerfile", "tsconfig.json", "tailwind"],
      "readme_excerpt": "...",
      "file_summary": {"py": 12, "ts": 30, ...}
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Directories that are noise for stack detection.
_SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".venv", "venv",
    "__pycache__", ".mypy_cache", ".pytest_cache", "target", "vendor",
    ".idea", ".vscode", "coverage", ".turbo", ".cache", "scratch",
}

# Extension -> language.
_EXT_LANG = {
    "py": "python", "ts": "typescript", "tsx": "typescript", "js": "javascript",
    "jsx": "javascript", "go": "go", "rs": "rust", "rb": "ruby", "java": "java",
    "kt": "kotlin", "php": "php", "cs": "csharp", "swift": "swift", "c": "c",
    "cpp": "cpp", "cc": "cpp", "h": "c", "hpp": "cpp", "scala": "scala",
    "ex": "elixir", "exs": "elixir", "dart": "dart", "vue": "vue", "svelte": "svelte",
}

# Substrings that appear in dependency lists -> framework label.
_FRAMEWORK_HINTS = {
    "next": "next", "react": "react", "vue": "vue", "svelte": "svelte",
    "@angular/core": "angular", "express": "express", "fastify": "fastify",
    "nestjs": "nestjs", "@nestjs/core": "nestjs", "fastapi": "fastapi",
    "flask": "flask", "django": "django", "starlette": "starlette",
    "rails": "rails", "sinatra": "sinatra", "spring-boot": "spring",
    "gin-gonic": "gin", "fiber": "fiber", "axum": "axum", "actix": "actix",
    "remix": "remix", "nuxt": "nuxt", "astro": "astro", "solid-js": "solid",
}

# Substrings -> notable SDK/service the project integrates with. These drive the
# best MCP-server recommendations ("you use Stripe -> here's the Stripe MCP").
_SDK_HINTS = {
    "stripe": "stripe", "supabase": "supabase", "openai": "openai",
    "anthropic": "anthropic", "@anthropic-ai": "anthropic", "twilio": "twilio",
    "prisma": "prisma", "drizzle": "drizzle", "mongoose": "mongodb",
    "mongodb": "mongodb", "pg": "postgres", "psycopg": "postgres",
    "redis": "redis", "ioredis": "redis", "boto3": "aws", "aws-sdk": "aws",
    "@aws-sdk": "aws", "firebase": "firebase", "firebase-admin": "firebase",
    "@vercel": "vercel", "sentry": "sentry", "@sentry": "sentry",
    "sendgrid": "sendgrid", "resend": "resend", "clerk": "clerk",
    "@clerk": "clerk", "auth0": "auth0", "graphql": "graphql",
    "playwright": "playwright", "puppeteer": "puppeteer", "langchain": "langchain",
    "pinecone": "pinecone", "weaviate": "weaviate", "shopify": "shopify",
    "slack": "slack", "@slack": "slack", "discord.js": "discord", "discord": "discord",
    "notion": "notion", "@notionhq": "notion", "octokit": "github", "PyGithub": "github",
    # ML & Data Analysis libraries
    "pandas": "pandas", "numpy": "numpy", "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn", "matplotlib": "matplotlib", "seaborn": "seaborn",
    "tensorflow": "tensorflow", "torch": "pytorch", "pytorch": "pytorch",
    "keras": "keras", "jax": "jax", "xgboost": "xgboost", "lightgbm": "lightgbm",
}


def _add(seq: list, value: str) -> None:
    if value and value not in seq:
        seq.append(value)


def _hint_scan(haystack: str, hints: dict, into: list) -> None:
    low = haystack.lower()
    for needle, label in hints.items():
        if needle.lower() in low:
            _add(into, label)


def _read(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def parse_notebook_file(path: Path) -> dict:
    """Parse a Jupyter notebook (.ipynb) to extract cells, imports, variables, and headers."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception as e:
        return {"filename": path.name, "error": f"Failed to parse JSON: {e}"}

    cells = data.get("cells", [])
    code_cells_count = 0
    markdown_cells_count = 0
    execution_counts = []
    imports = set()
    variables = set()
    headers = []

    # Common Python import patterns
    import_re = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z0-9_]+)")
    # Simple assignment pattern to find defined variables (like df = ..., model = ...)
    var_re = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=[^=]")

    for cell in cells:
        cell_type = cell.get("cell_type")
        source = cell.get("source", [])
        if isinstance(source, str):
            source_lines = source.splitlines()
        elif isinstance(source, list):
            source_lines = source
        else:
            source_lines = []

        if cell_type == "code":
            code_cells_count += 1
            exec_count = cell.get("execution_count")
            if exec_count is not None:
                execution_counts.append(exec_count)
            
            for line in source_lines:
                imp_match = import_re.match(line)
                if imp_match:
                    imports.add(imp_match.group(1))
                
                var_match = var_re.match(line)
                if var_match:
                    var_name = var_match.group(1)
                    if var_name not in ("import", "from", "print", "if", "for", "while", "return", "def", "class"):
                        variables.add(var_name)
                        
        elif cell_type == "markdown":
            markdown_cells_count += 1
            for line in source_lines:
                if line.strip().startswith("#"):
                    headers.append(line.strip())

    # Check execution order health
    out_of_order = False
    if len(execution_counts) > 1:
        # Check if they are non-decreasing
        for i in range(len(execution_counts) - 1):
            if execution_counts[i] > execution_counts[i + 1]:
                out_of_order = True
                break

    return {
        "filename": path.name,
        "code_cells": code_cells_count,
        "markdown_cells": markdown_cells_count,
        "execution_counts": execution_counts[:30],
        "execution_health": "out_of_order" if out_of_order else "ordered",
        "imports": sorted(list(imports)),
        "variables": sorted(list(variables))[:20],
        "headers": headers[:10],
    }


def scan_project(
    path: str,
    max_files: int = 4000,
    max_notebooks: int = 5,
    exclude_dirs: list[str] | None = None,
) -> dict:
    """Build a stack profile for the project rooted at `path`."""
    root = Path(path).expanduser().resolve()
    skip_dirs = set(_SKIP_DIRS)
    if exclude_dirs:
        skip_dirs.update(exclude_dirs)
    profile = {
        "path": str(root),
        "languages": [],
        "package_managers": [],
        "frameworks": [],
        "notable_sdks": [],
        "manifests": [],
        "signals": [],
        "readme_excerpt": "",
        "file_summary": {},
    }
    if not root.exists() or not root.is_dir():
        profile["error"] = f"Not a directory: {root}"
        return profile

    ext_counts: dict[str, int] = {}
    notebook_paths = []
    seen = 0
    try:
        iterator = root.rglob("*")
        while True:
            try:
                p = next(iterator)
            except StopIteration:
                break
            except Exception:
                continue # Skip files or directories that raise permission/read errors

            if any(part in skip_dirs for part in p.parts):
                continue
            if p.is_dir():
                continue
            seen += 1
            if seen > max_files:
                break
            ext = p.suffix.lstrip(".").lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
            name = p.name.lower()
            # Config-file signals (presence is meaningful regardless of content).
            if name == "dockerfile":
                _add(profile["signals"], "Dockerfile")
            elif name == "docker-compose.yml" or name == "docker-compose.yaml":
                _add(profile["signals"], "docker-compose")
            elif name == "tsconfig.json":
                _add(profile["signals"], "tsconfig.json")
            elif name.startswith("tailwind.config"):
                _add(profile["signals"], "tailwind")
            elif name.startswith("vite.config"):
                _add(profile["signals"], "vite")
            elif name == "schema.prisma":
                _add(profile["signals"], "prisma")
                _add(profile["notable_sdks"], "prisma")
            elif name == ".cursorrules" or ".cursor" in p.parts:
                _add(profile["signals"], "cursor-config")
            
            # Collect Jupyter Notebooks
            if ext == "ipynb" and len(notebook_paths) < max_notebooks:
                notebook_paths.append(p)
    except Exception as e:
        profile["error"] = f"Scan error: {e}"

    profile["file_summary"] = dict(
        sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True)[:15]
    )
    for ext, _n in ext_counts.items():
        lang = _EXT_LANG.get(ext)
        if lang:
            _add(profile["languages"], lang)

    _scan_manifests(root, profile)
    _scan_readme(root, profile)

    if notebook_paths:
        profile["notebooks"] = []
        for np_path in notebook_paths:
            nb_profile = parse_notebook_file(np_path)
            profile["notebooks"].append(nb_profile)
            for imp in nb_profile.get("imports", []):
                _hint_scan(imp, _SDK_HINTS, profile["notable_sdks"])

    return profile


def _scan_manifests(root: Path, profile: dict) -> None:
    # --- Node / npm-family ---
    pkg = root / "package.json"
    if pkg.exists():
        _add(profile["manifests"], "package.json")
        raw = _read(pkg)
        try:
            data = json.loads(raw)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            blob = " ".join(deps.keys())
        except (json.JSONDecodeError, AttributeError):
            blob = raw
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
        _hint_scan(blob, _SDK_HINTS, profile["notable_sdks"])
        if (root / "pnpm-lock.yaml").exists():
            _add(profile["package_managers"], "pnpm")
        elif (root / "yarn.lock").exists():
            _add(profile["package_managers"], "yarn")
        else:
            _add(profile["package_managers"], "npm")

    # --- Python ---
    req = root / "requirements.txt"
    if req.exists():
        _add(profile["manifests"], "requirements.txt")
        _add(profile["package_managers"], "pip")
        blob = _read(req)
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
        _hint_scan(blob, _SDK_HINTS, profile["notable_sdks"])
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        _add(profile["manifests"], "pyproject.toml")
        blob = _read(pyproject)
        if "poetry" in blob:
            _add(profile["package_managers"], "poetry")
        elif "[tool.uv]" in blob or (root / "uv.lock").exists():
            _add(profile["package_managers"], "uv")
        else:
            _add(profile["package_managers"], "pip")
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
        _hint_scan(blob, _SDK_HINTS, profile["notable_sdks"])

    # --- Go ---
    gomod = root / "go.mod"
    if gomod.exists():
        _add(profile["manifests"], "go.mod")
        _add(profile["package_managers"], "go modules")
        blob = _read(gomod)
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
        _hint_scan(blob, _SDK_HINTS, profile["notable_sdks"])

    # --- Rust ---
    cargo = root / "Cargo.toml"
    if cargo.exists():
        _add(profile["manifests"], "Cargo.toml")
        _add(profile["package_managers"], "cargo")
        blob = _read(cargo)
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
        _hint_scan(blob, _SDK_HINTS, profile["notable_sdks"])

    # --- Ruby / PHP / Java (lighter touch) ---
    if (root / "Gemfile").exists():
        _add(profile["manifests"], "Gemfile")
        _add(profile["package_managers"], "bundler")
        blob = _read(root / "Gemfile")
        _hint_scan(blob, _FRAMEWORK_HINTS, profile["frameworks"])
    if (root / "composer.json").exists():
        _add(profile["manifests"], "composer.json")
        _add(profile["package_managers"], "composer")
    if (root / "pom.xml").exists():
        _add(profile["manifests"], "pom.xml")
        _add(profile["package_managers"], "maven")
        _hint_scan(_read(root / "pom.xml"), _FRAMEWORK_HINTS, profile["frameworks"])
    for gradle in ("build.gradle", "build.gradle.kts"):
        if (root / gradle).exists():
            _add(profile["manifests"], gradle)
            _add(profile["package_managers"], "gradle")
            _hint_scan(_read(root / gradle), _FRAMEWORK_HINTS, profile["frameworks"])
    if list(root.glob("*.csproj")):
        _add(profile["manifests"], "*.csproj")
        _add(profile["package_managers"], "nuget")


def _scan_readme(root: Path, profile: dict) -> None:
    for name in ("README.md", "README.rst", "README.txt", "readme.md", "README"):
        f = root / name
        if f.exists():
            text = _read(f, limit=4000).strip()
            # Collapse whitespace for a compact excerpt.
            excerpt = re.sub(r"\s+", " ", text)[:1500]
            profile["readme_excerpt"] = excerpt
            return


def profile_summary(profile: dict) -> str:
    """One-line human/LLM-friendly summary of a stack profile."""
    parts = []
    if profile.get("languages"):
        parts.append("langs=" + ",".join(profile["languages"]))
    if profile.get("frameworks"):
        parts.append("frameworks=" + ",".join(profile["frameworks"]))
    if profile.get("notable_sdks"):
        parts.append("sdks=" + ",".join(profile["notable_sdks"]))
    if profile.get("package_managers"):
        parts.append("pkg=" + ",".join(profile["package_managers"]))
    return "; ".join(parts) or "no clear stack detected"


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(scan_project(target), indent=2))
