"""
Detect and execute actionable chat requests (write rules, install MCP).

The dashboard chat is otherwise RAG-only over Cursor docs. When the user asks
to generate/create/write project artifacts, we act on disk instead of explaining how.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

import cursor_artifacts as ca
import llm
import scanner

_CREATE_VERBS = ("generate", "create", "write", "add", "make", "scaffold", "build")
_RULE_TARGETS = (
    ".cursor/rules",
    "cursor rule",
    "cursor rules",
    "project rule",
    "project rules",
    "rules file",
    "rule file",
    "rules.mdc",
    ".mdc",
)
_INSTALL_MCP = ("install", "add", "enable", "set up", "setup")


def detect_chat_action(question: str) -> dict[str, Any] | None:
    """Return an action descriptor when the user wants us to act, not explain."""
    low = question.lower()
    has_create = any(v in low for v in _CREATE_VERBS)
    has_rule_target = any(t in low for t in _RULE_TARGETS)

    if has_create and has_rule_target:
        return {"type": "create_rule", "question": question}

    if any(v in low for v in _INSTALL_MCP) and "mcp" in low:
        name = _extract_mcp_name(question)
        if name:
            return {"type": "install_mcp", "name": name, "question": question}

    return None


def _extract_mcp_name(question: str) -> str | None:
    low = question.lower()
    patterns = (
        r"(?:install|add|enable|set up|setup)\s+(?:the\s+)?([a-z0-9_-]+)\s+mcp",
        r"mcp\s+(?:server\s+)?([a-z0-9_-]+)",
        r"(?:install|add)\s+(?:the\s+)?([a-z0-9_-]+)\s+(?:server|integration)",
    )
    for pat in patterns:
        m = re.search(pat, low)
        if m:
            return m.group(1).strip("-_")
    return None


def infer_rule_name(question: str, profile: dict[str, Any]) -> str:
    low = question.lower()
    m = re.search(r"(?:named|called)\s+['\"]?([a-z0-9_-]+)", low)
    if m:
        return ca.slugify(m.group(1))

    for fw in profile.get("frameworks") or []:
        if fw.lower() in low:
            return ca.slugify(f"{fw}-conventions")

    for lang in profile.get("languages") or []:
        if lang.lower() in low:
            return ca.slugify(f"{lang}-conventions")

    m = re.search(
        r"for\s+([a-z0-9][a-z0-9 ./_-]{1,40}?)\s+(?:conventions|rules|standards)",
        low,
    )
    if m:
        return ca.slugify(m.group(1).strip())

    return "project-conventions"


def infer_rule_globs(question: str, profile: dict[str, Any]) -> str:
    low = question.lower()
    if "fastapi" in low or "fastapi" in (profile.get("frameworks") or []):
        return "**/*.py"
    if "javascript" in (profile.get("languages") or []) or "typescript" in low:
        return "**/*.{js,ts,tsx}"
    if "python" in (profile.get("languages") or []):
        return "**/*.py"
    return ""


def build_rule_intent(question: str, profile: dict[str, Any]) -> str:
    summary = scanner.profile_summary(profile)
    frameworks = ", ".join(profile.get("frameworks") or []) or "none"
    sdks = ", ".join(profile.get("notable_sdks") or []) or "none"
    return (
        f"{question.strip()}\n\n"
        f"Ground this rule in the scanned project: {summary}. "
        f"Frameworks: {frameworks}. Notable SDKs: {sdks}."
    )


def generate_rule_body(
    intent: str,
    search_docs: Callable[[str, int], list[dict]],
) -> str:
    docs_ctx = ""
    try:
        contexts = search_docs(f"Best practices and conventions relevant to: {intent}", 4)
        blocks = []
        for i, c in enumerate(contexts, 1):
            head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
            blocks.append(f"[{i}] {head}\n{c['text']}")
        docs_ctx = "\n\n".join(blocks)
    except Exception:
        pass

    sys_prompt = (
        "You write Cursor project rules. Given an intent and project scan context, "
        "produce a crisp, actionable rule body in markdown (imperative bullet points, "
        "no preamble, no frontmatter). Reference concrete conventions for the stack "
        "detected. Keep it under 200 words."
    )
    user = (
        f"Intent: {intent}\n\nRelevant Cursor guidance (for grounding):\n"
        f"{docs_ctx or '(none)'}\n\nWrite the rule body now."
    )
    try:
        body = llm.generate(
            sys_prompt,
            [{"role": "user", "content": user}],
            ollama_num_predict=768,
        )
        if not (body or "").strip():
            raise llm.LLMError("empty model response")
        return body
    except llm.LLMError:
        return f"- {intent}\n\n(Edit this rule — LLM backend unavailable or returned empty output.)"


def rule_description(question: str, profile: dict[str, Any]) -> str:
    name = infer_rule_name(question, profile).replace("-", " ")
    return name[:100] if len(name) <= 100 else name[:97] + "…"


def write_project_rule(
    workspace: Path,
    question: str,
    profile: dict[str, Any],
    search_docs: Callable[[str, int], list[dict]],
) -> tuple[str, dict[str, Any]]:
    name = infer_rule_name(question, profile)
    intent = build_rule_intent(question, profile)
    globs = infer_rule_globs(question, profile)
    body = generate_rule_body(intent, search_docs)
    description = rule_description(question, profile)

    file_path = ca.write_rule(
        str(workspace), name, description, body, globs=globs, always_apply=False
    )
    rel = file_path.relative_to(workspace.resolve())
    summary = scanner.profile_summary(profile)
    preview = body.strip().splitlines()[:6]
    preview_text = "\n".join(f"> {line}" for line in preview)

    message = (
        f"**Created** `{rel}` for your active workspace.\n\n"
        f"Based on project scan: {summary}.\n\n"
        f"Preview:\n\n{preview_text}\n\n"
        "The rule is on disk — reload Cursor or open the file to review. "
        "The rules panel will refresh automatically."
    )
    meta = {
        "type": "create_rule",
        "path": str(file_path),
        "relative_path": str(rel),
        "name": name,
    }
    return message, meta


def install_mcp_from_catalog(
    workspace: Path,
    server_name: str,
    catalog_lookup: Callable[[], dict[str, dict]],
) -> tuple[str, dict[str, Any]]:
    lookup = catalog_lookup()
    hit = lookup.get(server_name.strip().lower())
    if not hit:
        known = ", ".join(sorted(lookup.keys())[:12])
        raise ValueError(
            f"MCP server '{server_name}' not found in catalog. "
            f"Try one of: {known}…"
        )

    file_path = ca.install_mcp_server(str(workspace), hit, "project")
    rel = file_path.relative_to(workspace.resolve() / ".cursor")
    message = (
        f"**Installed** `{hit.get('name', server_name)}` into `{rel}`.\n\n"
        "Restart MCP in Cursor (or reload the window) for the server to connect."
    )
    meta = {
        "type": "install_mcp",
        "path": str(file_path),
        "relative_path": str(rel),
        "name": server_name,
    }
    return message, meta


def execute_chat_action(
    action: dict[str, Any],
    workspace: Path,
    profile: dict[str, Any],
    *,
    search_docs: Callable[[str, int], list[dict]],
    catalog_lookup: Callable[[], dict[str, dict]],
) -> tuple[str, dict[str, Any]]:
    if action["type"] == "create_rule":
        return write_project_rule(
            workspace, action["question"], profile, search_docs
        )
    if action["type"] == "install_mcp":
        return install_mcp_from_catalog(
            workspace, action["name"], catalog_lookup
        )
    raise ValueError(f"Unknown action type: {action['type']}")
