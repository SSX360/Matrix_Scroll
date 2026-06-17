"""
Project-advisor chat mode: answer domain/codebase questions using scan, README,
vault, brainstorm, and rules — not Cursor docs alone.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Callable

import brainstorm as bs
import scanner
import vault
import workspace_config as wc

ADVISOR_CACHE_TTL = int(os.environ.get("STATUS_CACHE_TTL", "30"))
_advisor_cache: dict[str, Any] = {"key": "", "context": "", "ts": 0.0}

_PROJECT_SIGNALS = (
    "this codebase",
    "this project",
    "my project",
    "my repo",
    "this repo",
    "for this codebase",
    "in this codebase",
    "in this project",
    "our codebase",
    "our project",
)
_ADVICE_SIGNALS = (
    "next step",
    "next steps",
    "best step",
    "best steps",
    "continue with",
    "what should i",
    "what should we",
    "how do i improve",
    "how can i improve",
    "recommend",
    "maximize",
    "optimiz",
    "improve",
    "profit",
    "strategy",
    "roadmap",
    "priorit",
)
_ADVICE_VERBS = ("how", "what should", "recommend", "steps", "suggest", "advise")
_CURSOR_FAQ_ONLY = (
    "what is plan mode",
    "how do cursor rules work",
    "how do i configure cursor rules",
    "what are cursor rules",
    "how does agent work",
    "what is agent mode",
    "how do i use agent",
    "what is mcp in cursor",
)

ADVISOR_SYSTEM_PROMPT = """You are the Digital Rain project advisor for the user's \
active codebase.

Rules:
- Answer using the project context provided (README, scan, vault notes, rules, brainstorm seeds).
- Give numbered, actionable next steps tailored to the user's goal and this project's stack.
- Ground recommendations in the README excerpt and vault snippets when present.
- Mention Cursor setup (rules, MCP servers) only when it directly helps the stated goal.
- Supplementary Cursor documentation excerpts are secondary — use them for editor workflow tips only.
- Do not refuse to answer because domain topics are absent from Cursor docs.
- Be concise and practical. Prefer specific steps over generic advice."""


def wants_project_advice(question: str, profile: dict[str, Any] | None = None) -> bool:
    """True when the user wants codebase/domain advice, not pure Cursor docs FAQ."""
    low = question.lower().strip()
    if not low:
        return False

    if any(faq in low for faq in _CURSOR_FAQ_ONLY):
        if not any(sig in low for sig in _PROJECT_SIGNALS):
            return False

    if any(sig in low for sig in _PROJECT_SIGNALS):
        return True
    if any(sig in low for sig in _ADVICE_SIGNALS):
        return True

    if profile:
        stack_terms = list(profile.get("frameworks") or []) + list(profile.get("languages") or [])
        stack_terms += list(profile.get("notable_sdks") or [])[:6]
        has_stack = any(term.lower() in low for term in stack_terms if term)
        has_advice_verb = any(v in low for v in _ADVICE_VERBS)
        if has_stack and has_advice_verb:
            return True

    return False


def _cache_key(workspace: Path, question: str) -> str:
    prefix = hashlib.sha256(question.encode()).hexdigest()[:12]
    return f"{workspace.resolve()}:{prefix}"


def _get_cached_context(key: str) -> str | None:
    now = time.monotonic()
    if (
        _advisor_cache.get("key") == key
        and _advisor_cache.get("context")
        and now - float(_advisor_cache.get("ts", 0)) < ADVISOR_CACHE_TTL
    ):
        return _advisor_cache["context"]
    return None


def _set_cached_context(key: str, context: str) -> None:
    _advisor_cache.update({"key": key, "context": context, "ts": time.monotonic()})


def build_advisor_context(
    question: str,
    workspace: Path,
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    list_rules: Callable[[str], list[dict]] | None = None,
    catalog_search: Callable[[str, int], list[dict]] | None = None,
) -> str:
    key = _cache_key(workspace, question)
    cached = _get_cached_context(key)
    if cached is not None:
        return cached

    lines = [
        "=== Active workspace ===",
        str(workspace.resolve()),
        "",
        "=== Stack scan ===",
        scanner.profile_summary(profile),
    ]

    langs = profile.get("languages") or []
    frameworks = profile.get("frameworks") or []
    sdks = profile.get("notable_sdks") or []
    if langs:
        lines.append(f"Languages: {', '.join(langs)}")
    if frameworks:
        lines.append(f"Frameworks: {', '.join(frameworks)}")
    if sdks:
        lines.append(f"Notable SDKs: {', '.join(sdks)}")

    readme = (profile.get("readme_excerpt") or "").strip()
    if readme:
        lines.extend(["", "=== README excerpt ===", readme[:1500]])

    vault_path = wc.resolve_vault_path(workspace, config)
    if vault_path and vault_path.is_dir() and question.strip():
        try:
            hits = vault.search_vault(question, str(vault_path), k=3)
            if hits:
                lines.append("")
                lines.append("=== Vault notes (relevant) ===")
                for i, hit in enumerate(hits, 1):
                    title = hit.get("doc_title") or hit.get("heading") or "note"
                    text = (hit.get("text") or "")[:400]
                    lines.append(f"[{i}] {title}\n{text}")
        except Exception:
            pass

    rules = list_rules(str(workspace)) if list_rules else []
    if rules:
        lines.append("")
        lines.append("=== Active Cursor rules ===")
        for rule in rules[:8]:
            name = rule.get("filename") or rule.get("description") or "rule"
            desc = rule.get("description") or ""
            lines.append(f"- {name}: {desc}")

    ctx = bs.gather_context(
        workspace=workspace,
        config=config,
        list_rules=list_rules,
        catalog_search=None,
    )
    suggestions = bs.suggest_offline(ctx, limit=3)
    if suggestions:
        lines.append("")
        lines.append("=== Suggested next-step seeds ===")
        for item in suggestions:
            lines.append(f"- {item.title}: {item.prompt}")

    if catalog_search and question.strip():
        try:
            mcp_hits = catalog_search(question, 2)
            if mcp_hits:
                lines.append("")
                lines.append("=== Relevant MCP catalog ===")
                for hit in mcp_hits:
                    name = hit.get("name") or hit.get("title") or "server"
                    desc = (hit.get("description") or "")[:120]
                    lines.append(f"- {name}: {desc}")
        except Exception:
            pass

    notebooks = profile.get("notebooks") or []
    if notebooks:
        lines.append("")
        lines.append("=== Jupyter notebooks ===")
        for nb in notebooks[:5]:
            name = nb.get("filename", "unknown")
            health = nb.get("execution_health", "unknown")
            lines.append(f"- {name}: {health}")

    context = "\n".join(lines)
    _set_cached_context(key, context)
    return context


def build_advisor_prompt(
    question: str,
    advisor_context: str,
    doc_contexts: list[dict] | None = None,
) -> str:
    blocks = [advisor_context]
    if doc_contexts:
        blocks.append("")
        blocks.append("=== Supplementary Cursor docs (secondary) ===")
        for i, c in enumerate(doc_contexts, 1):
            head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
            blocks.append(f"[{i}] {head}\n{c['text'][:600]}")

    context = "\n\n".join(blocks)
    return (
        f"Project context:\n\n{context}\n\n"
        f"---\n\nUser question: {question}\n\n"
        "Answer with numbered actionable steps grounded in the project context above."
    )


def build_offline_advisor_answer(
    question: str,
    advisor_context: str,
) -> str:
    """Fallback when LLM backends fail or return empty output in advisor mode."""
    lines = [
        "Project advisor (offline — using scanned project context):",
        "",
    ]

    section = None
    readme_lines: list[str] = []
    seeds: list[str] = []
    stack_line = ""

    for line in advisor_context.splitlines():
        if line.startswith("=== Stack scan ==="):
            section = "stack"
            continue
        if line.startswith("=== README excerpt ==="):
            section = "readme"
            continue
        if line.startswith("=== Suggested next-step seeds ==="):
            section = "seeds"
            continue
        if line.startswith("==="):
            section = None
            continue
        if section == "stack" and line.strip() and not stack_line:
            stack_line = line.strip()
        elif section == "readme" and line.strip():
            readme_lines.append(line.strip())
        elif section == "seeds" and line.strip().startswith("-"):
            seeds.append(line.strip()[2:])

    if stack_line:
        lines.append(f"**Stack:** {stack_line}")
        lines.append("")

    if readme_lines:
        lines.append("**From README:**")
        lines.append(readme_lines[0][:600])
        lines.append("")

    lines.append("**Suggested next steps:**")
    if seeds:
        for i, seed in enumerate(seeds[:5], 1):
            lines.append(f"{i}. {seed}")
    else:
        lines.extend([
            "1. Review README priorities and restart live trading sessions when ready.",
            "2. Validate model pipelines (TimesFM, MLForecast) on current data.",
            "3. Run project tests and fix failing weather-domain suites.",
            "4. Ask Digital Rain to install MCP servers (postgres, redis) or generate domain rules.",
        ])

    lines.extend([
        "",
        f"*(Question: {question[:120]})*",
        "",
        "Tip: ensure Ollama is responding or set ANTHROPIC_API_KEY / GEMINI_API_KEY for full AI synthesis.",
    ])
    return "\n".join(lines)
