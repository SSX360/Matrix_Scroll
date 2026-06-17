"""
Render the config artifacts Cursor actually consumes.

Two formats (verified against Cursor's docs):

1. Project rules: `.cursor/rules/<name>.mdc`
   YAML frontmatter (description / globs / alwaysApply) + a markdown body.
   NOTE: the file MUST be `.mdc` inside `.cursor/rules/`. Plain `.md` is ignored
   by Cursor's rules system.

2. MCP servers: `.cursor/mcp.json`
   { "mcpServers": { "<name>": { "command", "args", "env"? } | { "url" } } }
   Secrets are emitted as ${env:VAR} placeholders, never inlined.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import os


# --- rules -----------------------------------------------------------------

def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "rule"


def render_rule(description: str, body: str, *,
                globs: str = "", always_apply: bool = False) -> str:
    """Return a valid `.cursor/rules/*.mdc` file as a string.

    - description: short trigger description (used for Agent-requested rules)
    - globs: comma-separated file patterns the rule auto-attaches to (optional)
    - always_apply: if True the rule is always in context
    """
    fm = ["---"]
    fm.append(f"description: {_yaml_scalar(description)}")
    fm.append(f"globs: {globs}")  # empty is fine; Cursor treats it as no auto-glob
    fm.append(f"alwaysApply: {'true' if always_apply else 'false'}")
    fm.append("---")
    return "\n".join(fm) + "\n\n" + body.strip() + "\n"


def _yaml_scalar(text: str) -> str:
    """Quote a one-line YAML scalar if it contains risky characters."""
    one_line = " ".join(text.splitlines()).strip()
    if one_line and re.search(r"[:#\"'\[\]{}]", one_line):
        escaped = one_line.replace('"', '\\"')
        return f'"{escaped}"'
    return one_line


# --- mcp.json --------------------------------------------------------------

def _config_from_entry(entry: dict) -> dict:
    """Resolve a catalog entry's stored install_snippet into a config object.

    install_snippet is a JSON string like {"command": "npx", "args": [...]} or
    {"url": "..."}. When absent we emit a clearly-marked placeholder so the user
    knows to fill it in rather than getting silent broken config.
    """
    raw = entry.get("install_snippet") or ""
    if raw:
        try:
            cfg = json.loads(raw)
            if isinstance(cfg, dict) and (cfg.get("command") or cfg.get("url")):
                return cfg
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "command": "<command>",
        "args": [],
        "_note": f"No install command published. See {entry.get('source_url', '')}",
    }


def render_mcp_json(entries: list[dict], *, merge_into: dict | None = None) -> str:
    """Build a `.cursor/mcp.json` document from catalog entries.

    Pass `merge_into` (a parsed existing mcp.json) to preserve already-configured
    servers; otherwise a fresh document is produced.
    """
    doc = dict(merge_into) if merge_into else {}
    servers = dict(doc.get("mcpServers") or {})
    for e in entries:
        key = slugify(e.get("name", "server"))
        servers[key] = _config_from_entry(e)
    doc["mcpServers"] = servers
    return json.dumps(doc, indent=2)


def self_registration_snippet(server_path: str, *, python: str = "python") -> str:
    """The mcp.json entry that registers THIS Digital Rain server in Cursor."""
    doc = {
        "mcpServers": {
            "cursor-copilot": {
                "command": python,
                "args": [server_path],
                "env": {
                    "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}",
                    # Fallback backend; leave the env var unset to skip it.
                    "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
                },
            }
        }
    }
    return json.dumps(doc, indent=2)


def write_rule(project_path: str, filename: str, description: str, body: str,
               globs: str = "", always_apply: bool = False) -> Path:
    """Generate and write a rule file into project_path/.cursor/rules/."""
    p_path = Path(project_path).expanduser().resolve()
    rules_dir = p_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    
    name = filename
    if name.endswith(".mdc"):
        name = name[:-4]
    name = slugify(name) + ".mdc"
    
    file_path = rules_dir / name
    content = render_rule(description, body, globs=globs, always_apply=always_apply)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def install_mcp_server(project_path: str, entry: dict, project_or_global: str = "project") -> Path:
    """Install/merge an MCP server config into project-specific or global mcp.json."""
    if project_or_global == "global":
        mcp_dir = Path("~/.cursor").expanduser()
    else:
        mcp_dir = Path(project_path).expanduser().resolve() / ".cursor"
        
    mcp_dir.mkdir(parents=True, exist_ok=True)
    file_path = mcp_dir / "mcp.json"
    
    existing_config = {}
    if file_path.exists():
        try:
            existing_config = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
            
    content = render_mcp_json([entry], merge_into=existing_config)
    file_path.write_text(content, encoding="utf-8")
    return file_path

