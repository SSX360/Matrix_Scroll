"""
Cursor Co-pilot — an MCP server that turns this docs bot into a context-aware
assistant Cursor's agent can call directly.

It does four things for you while you work in Cursor:
  1. Answers questions grounded in the Cursor documentation.
  2. Scans your project to understand what you're building.
  3. Recommends MCP servers / skills from an ingested catalog that fit your goal.
  4. Generates the config artifacts to wire them up (.cursor/rules, .cursor/mcp.json).

Transport: stdio. IMPORTANT: stdout belongs to the MCP transport — everything
here logs to stderr only. Run it with:  python mcp_server.py
Register it in Cursor via .cursor/mcp.json (see README / self_registration_snippet).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Intercept all built-in print calls to prevent stdout pollution, which breaks the MCP stdio channel
import builtins
_original_print = builtins.print
def _safe_mcp_print(*args, **kwargs):
    file = kwargs.get("file")
    if file is None or file is sys.stdout:
        kwargs["file"] = sys.stderr
    _original_print(*args, **kwargs)
builtins.print = _safe_mcp_print


import search as S
import scanner
import llm
import cursor_artifacts as ca
import vault
import workspace_config as wc
import brainstorm as bs

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "data" / "index.json"

mcp = FastMCP("cursor-copilot")
_bm25: S.BM25 | None = None


def _log(msg: str) -> None:
    print(f"[mcp] {msg}", file=sys.stderr)


def get_index() -> S.BM25:
    """Load the BM25 index once, building it if missing."""
    global _bm25
    if _bm25 is None:
        if not INDEX_PATH.exists():
            _log("No index found — building it (scraping docs + catalog)…")
            import ingest
            ingest.main()
        _bm25 = S.BM25(S.load_index(INDEX_PATH))
        _log(f"Loaded index: {_bm25.N} chunks.")
    return _bm25


def _default_project_path() -> str:
    ws, _ = wc.resolve_workspace()
    return str(ws)


def _scan_path(path: str) -> dict:
    if path in (".", ""):
        path = _default_project_path()
    ws = Path(path).expanduser().resolve()
    cfg = wc.load_config(ws)
    nb_cfg = cfg.get("notebooks", {})
    if not nb_cfg.get("enabled", True):
        return scanner.scan_project(path, max_notebooks=0)
    return scanner.scan_project(
        path,
        max_notebooks=int(nb_cfg.get("max_notebooks", 10)),
        exclude_dirs=list(nb_cfg.get("exclude_dirs") or []),
    )


def _catalog_lookup() -> dict[str, dict]:
    """Map lowercased server name -> its catalog chunk (for scaffold lookups)."""
    bm = get_index()
    out: dict[str, dict] = {}
    for c in bm.chunks:
        if c.get("source_type") == "mcp_catalog":
            name = (c.get("name") or c.get("doc_title") or "").strip()
            if name:
                out[name.lower()] = c
    return out


# ---------------------------------------------------------------------------
# Grounded-answer helper (kept local so the stdio server doesn't import Flask)
# ---------------------------------------------------------------------------

DOCS_SYSTEM = """You are the Cursor Co-pilot, an expert on the Cursor AI code \
editor. Answer using the documentation excerpts provided. Be concise and \
practical: short paragraphs, steps or code blocks where useful, and cite facts \
inline like [1], [2] matching the numbered sources. If the answer isn't in the \
excerpts, say so and suggest where to look. Never invent settings or commands."""


def _grounded_answer(question: str, k: int) -> tuple[str, list[dict]]:
    bm = get_index()
    contexts = bm.search(question, k=k, source_type="cursor_doc")
    blocks = []
    for i, c in enumerate(contexts, 1):
        head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
        blocks.append(f"[{i}] {head}\nURL: {c['url']}\n{c['text']}")
    ctx = "\n\n---\n\n".join(blocks) if blocks else "(no relevant docs found)"
    prompt = (f"Documentation context:\n\n{ctx}\n\n---\n\n"
              f"Question: {question}\n\nAnswer using only the context above.")
    sources = [{"n": i + 1, "title": c["doc_title"], "heading": c.get("heading", ""),
                "url": c["url"]} for i, c in enumerate(contexts)]
    try:
        answer = llm.generate(DOCS_SYSTEM, [{"role": "user", "content": prompt}])
    except llm.LLMError as e:
        answer = (f"(No LLM backend available: {e})\n\nRelevant docs:\n" +
                  "\n".join(f"- {s['title']} — {s['url']}" for s in sources))
    return answer, sources


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def ask_cursor_docs(question: str, k: int = 5) -> str:
    """Answer a question about Cursor, grounded in the official documentation.

    Use this for "how do I…" / "what is…" questions about Cursor features
    (Agent, Plan Mode, Rules, MCP, models, keybindings, settings).
    """
    answer, sources = _grounded_answer(question, k)
    if sources:
        cites = "\n".join(f"[{s['n']}] {s['title']} — {s['url']}" for s in sources)
        return f"{answer}\n\nSources:\n{cites}"
    return answer


@mcp.tool()
def search_cursor_docs(query: str, k: int = 8) -> str:
    """Retrieve the most relevant Cursor documentation chunks for a query.

    No LLM is used — this is fast, deterministic, and offline. Returns a ranked
    list of matching source passages.
    """
    bm = get_index()
    results = bm.search(query, k=k, source_type="cursor_doc")
    if not results:
        return "No relevant documentation found."
    out = []
    for i, c in enumerate(results, 1):
        head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
        out.append(f"### [{i}] {head}\nURL: {c['url']}\nScore: {c.get('score', 0)}\n\n{c['text']}\n")
    return "\n---\n\n".join(out)


@mcp.tool()
def scan_project(path: str = ".") -> str:
    """Scan a project directory and return a stack profile summary.

    Reads manifests, lockfiles, config files, the file tree, and the README to
    infer languages, frameworks, notable SDKs, and package managers.
    """
    p = _scan_path(path)
    if "error" in p:
        return f"Scan failed: {p['error']}"
    
    out = [f"# Project Stack Profile: {p['path']}"]
    if p.get("languages"):
        out.append(f"- **Languages**: {', '.join(p['languages'])}")
    if p.get("frameworks"):
        out.append(f"- **Frameworks**: {', '.join(p['frameworks'])}")
    if p.get("notable_sdks"):
        out.append(f"- **Notable SDKs/Integrations**: {', '.join(p['notable_sdks'])}")
    if p.get("package_managers"):
        out.append(f"- **Package Managers**: {', '.join(p['package_managers'])}")
    if p.get("manifests"):
        out.append(f"- **Manifests Detected**: {', '.join(p['manifests'])}")
    if p.get("signals"):
        out.append(f"- **Config/File Signals**: {', '.join(p['signals'])}")
    if p.get("readme_excerpt"):
        out.append(f"\n## README Excerpt\n{p['readme_excerpt'][:400]}...")
        
    return "\n".join(out)


def _get_suggested_mcp_servers(goal: str, project_path: str = "", k: int = 6) -> list[dict]:
    query_parts = [goal]
    if project_path:
        prof = _scan_path(project_path)
        query_parts.append(scanner.profile_summary(prof))
        query_parts.extend(prof.get("notable_sdks", []))
        query_parts.extend(prof.get("frameworks", []))
    query = " ".join(query_parts)
    bm = get_index()
    results = bm.search(query, k=k, source_type="mcp_catalog")
    return [{"name": c.get("name") or c["doc_title"], "description": c["text"],
             "tags": c.get("tags", ""), "github_url": c.get("github_url", ""),
             "source_url": c["url"], "install_snippet": c.get("install_snippet", ""),
             "score": c.get("score")}
            for c in results]


@mcp.tool()
def suggest_mcp_servers(goal: str, project_path: str = "", k: int = 6) -> str:
    """Recommend MCP servers / skills from the ingested catalog for a goal.

    Combines the stated `goal` with signals from an optional `project_path` scan
    to build the search query, then ranks catalog entries.
    """
    servers = _get_suggested_mcp_servers(goal, project_path, k)
    if not servers:
        return "No recommended MCP servers found for this goal."
    
    out = ["# Recommended MCP Servers"]
    for s in servers:
        out.append(f"### {s['name']} (Score: {s['score']})")
        out.append(f"- **Description**: {s['description']}")
        if s.get("tags"):
            out.append(f"- **Tags**: {s['tags']}")
        if s.get("github_url"):
            out.append(f"- **GitHub**: {s['github_url']}")
        if s.get("install_snippet"):
            out.append(f"- **Install Command/Snippet**:\n```json\n{s['install_snippet']}\n```")
        out.append("")
    return "\n".join(out)


@mcp.tool()
def generate_cursor_rule(intent: str, globs: str = "", always_apply: bool = False) -> str:
    """Generate a Cursor project rule (.cursor/rules/*.mdc) for an intent.

    `intent` describes the behavior you want enforced (e.g. "always use the repo's
    logging helper instead of print"). `globs` optionally scopes the rule to files
    (e.g. "**/*.ts"). Returns the full .mdc file content to save under .cursor/rules/.
    """
    docs_ctx, _ = _grounded_answer(
        f"Best practices and conventions relevant to: {intent}", k=4)
    sys_prompt = ("You write Cursor project rules. Given an intent, produce a crisp, "
                  "actionable rule body in markdown (imperative bullet points, no "
                  "preamble, no frontmatter). Keep it under 200 words.")
    user = (f"Intent: {intent}\n\nRelevant Cursor guidance (for grounding):\n"
            f"{docs_ctx}\n\nWrite the rule body now.")
    try:
        body = llm.generate(sys_prompt, [{"role": "user", "content": user}])
    except llm.LLMError:
        body = f"- {intent}\n\n(Generated without an LLM backend — edit as needed.)"
    description = intent if len(intent) <= 100 else intent[:97] + "…"
    return ca.render_rule(description, body, globs=globs, always_apply=always_apply)


@mcp.tool()
def scaffold_mcp_config(server_names: list[str]) -> str:
    """Generate a .cursor/mcp.json snippet for the named catalog servers.

    Pass server names returned by suggest_mcp_servers. Looks up each entry's
    published install command and emits a merge-ready mcpServers map, with
    secrets as ${env:VAR} placeholders. Unknown names are reported in a comment.
    """
    lookup = _catalog_lookup()
    entries, missing = [], []
    for name in server_names:
        hit = lookup.get(name.strip().lower())
        if hit:
            entries.append(hit)
        else:
            missing.append(name)
    out = ca.render_mcp_json(entries)
    if missing:
        out += f"\n\n// Not found in catalog: {', '.join(missing)}"
    return out


@mcp.tool()
def recommend_setup(project_path: str = ".", goal: str = "") -> str:
    """The co-pilot's full recommendation: scan the project + the goal, then
    propose MCP servers, Cursor rules, and a ready-to-paste mcp.json.
    """
    profile = _scan_path(project_path)
    stack = scanner.profile_summary(profile)
    servers = _get_suggested_mcp_servers(goal or stack, project_path=project_path, k=6)
    mcp_json = ca.render_mcp_json(
        [s for s in servers if s.get("install_snippet")][:4])
    tips, _ = _grounded_answer(
        f"How should I configure Cursor (rules, MCP, agent) for this project? "
        f"Goal: {goal}. Stack: {stack}.", k=4)

    notes = ""
    try:
        synth_sys = ("You are a Cursor setup advisor. Given a project's stack, the "
                     "user's goal, and candidate MCP servers, give a short prioritized "
                     "plan (3-6 bullets): which MCP servers to add and why, and 1-2 "
                     "Cursor rules worth creating. Be specific and concise.")
        synth_user = (f"Goal: {goal}\nStack: {stack}\n"
                      f"Candidate MCP servers: "
                      f"{json.dumps([{'name': s['name'], 'description': s['description'][:160]} for s in servers])}")
        notes = llm.generate(synth_sys, [{"role": "user", "content": synth_user}],
                             max_tokens=1200)
    except llm.LLMError as e:
        notes = f"(No LLM backend for synthesis: {e}.)"

    out = [
        f"# Setup Recommendation Report for {profile.get('path', project_path)}",
        "## Stack Profile Summary",
        f"- {stack}",
        "",
        "## Setup Plan & Advice",
        notes,
        "",
        "## Recommended MCP Servers Configuration",
        "Add this configuration into your `.cursor/mcp.json`:",
        f"```json\n{mcp_json}\n```",
        "",
        "## Cursor Documentation Tips & Best Practices",
        tips
    ]
    return "\n".join(out)



@mcp.tool()
def create_cursor_rule(name: str, intent: str, globs: str = "", always_apply: bool = False, project_path: str = ".") -> str:
    """Generate and write a Cursor project rule (.cursor/rules/*.mdc) directly to disk.

    `name` is the filename (e.g. "python-logs").
    `intent` describes the rule (e.g. "always use standard logging").
    """
    docs_ctx, _ = _grounded_answer(
        f"Best practices and conventions relevant to: {intent}", k=4)
    sys_prompt = ("You write Cursor project rules. Given an intent, produce a crisp, "
                  "actionable rule body in markdown (imperative bullet points, no "
                  "preamble, no frontmatter). Keep it under 200 words.")
    user = (f"Intent: {intent}\n\nRelevant Cursor guidance (for grounding):\n"
            f"{docs_ctx}\n\nWrite the rule body now.")
    try:
        body = llm.generate(sys_prompt, [{"role": "user", "content": user}])
    except llm.LLMError:
        body = f"- {intent}\n\n(Generated without an LLM backend — edit as needed.)"
    description = intent if len(intent) <= 100 else intent[:97] + "…"
    
    try:
        file_path = ca.write_rule(project_path, name, description, body, globs=globs, always_apply=always_apply)
        return f"Successfully generated and wrote rule to relative path: {file_path.relative_to(Path(project_path).resolve())}"
    except Exception as e:
        return f"Error writing rule file: {e}"


@mcp.tool()
def install_mcp_server(name: str, project_or_global: str = "project", project_path: str = ".") -> str:
    """Install/merge an MCP server from the catalog into mcp.json.

    `name` is the name of the MCP server.
    `project_or_global` is either 'project' or 'global'.
    """
    lookup = _catalog_lookup()
    hit = lookup.get(name.strip().lower())
    if not hit:
        return f"Error: MCP server '{name}' not found in catalog. Run suggest_mcp_servers to find available servers."
    
    try:
        file_path = ca.install_mcp_server(project_path, hit, project_or_global)
        return f"Successfully installed MCP server '{name}' to {file_path.name} in {project_or_global} mode."
    except Exception as e:
        return f"Error installing MCP server: {e}"



@mcp.tool()
def scan_notebooks(path: str = ".") -> str:
    """Scan Jupyter Notebooks (.ipynb) in the project and return variables, imports, and execution order health.

    Enables reasoning about code state and notebook health.
    """
    profile = _scan_path(path)
    notebooks = profile.get("notebooks") or []
    if not notebooks:
        return "No Jupyter notebooks found in this project."
        
    out = ["# Jupyter Notebooks Context"]
    for nb in notebooks:
        out.append(f"### Notebook: {nb['filename']}")
        out.append(f"- **Execution Health**: {nb['execution_health']}")
        if nb.get("imports"):
            out.append(f"- **Imports**: {', '.join(nb['imports'])}")
        if nb.get("variables"):
            out.append(f"- **Variables**: {', '.join(nb['variables'])}")
        if nb.get("headers"):
            out.append("- **Key Sections**:")
            for h in nb["headers"]:
                out.append(f"  - {h}")
        out.append("")
    return "\n".join(out)


@mcp.tool()
def search_knowledge_vault(query: str, vault_path: str = "", k: int = 5) -> str:
    """Search personal Obsidian or Markdown notes using BM25 ranking.

    Grounds recommendations or coding instructions in your personal notes.
    """
    if not vault_path:
        resolved = wc.resolve_vault_path()
        vault_path = str(resolved) if resolved else ""
    results = vault.search_vault(query, vault_path, k)
    if not results:
        return "No relevant notes found in your vault."
        
    out = ["# Vault Search Results"]
    for i, r in enumerate(results, 1):
        head = f"{r['doc_title']} — {r['heading']}" if r.get("heading") else r["doc_title"]
        out.append(f"### [{i}] {head}")
        out.append(f"Score: {r.get('score', 0)}")
        out.append(f"URL: {r['url']}")
        out.append(f"\n{r['text']}\n")
    return "\n---\n\n".join(out)


def _mcp_list_rules(project_path: str) -> list[dict]:
    rules_dir = Path(project_path).resolve() / ".cursor" / "rules"
    if not rules_dir.is_dir():
        return []
    return [{"filename": f.name, "description": f.stem} for f in rules_dir.glob("*.mdc")]


def _mcp_catalog_search(goal: str, k: int) -> list[dict]:
    bm = get_index()
    results = bm.search(goal, k=k, source_type="mcp_catalog")
    return [{"name": c.get("name") or c["doc_title"], "title": c.get("name") or c["doc_title"]} for c in results]


@mcp.tool()
def brainstorm_project(goal: str = "", limit: int = 6) -> str:
    """Brainstorm tailored next steps for the active workspace."""
    result = bs.brainstorm(
        limit=limit,
        list_rules=_mcp_list_rules,
        catalog_search=_mcp_catalog_search,
        llm_generate=llm.generate,
    )
    lines = [
        f"# Brainstorm: {result.get('context_summary', 'project')}",
        f"Workspace: {result.get('workspace')}",
        "",
    ]
    for i, s in enumerate(result.get("suggestions") or [], 1):
        lines.append(f"### {i}. {s.get('title')}")
        lines.append(f"- **Tag**: {s.get('tag')}")
        lines.append(f"- **Prompt**: {s.get('prompt')}")
        lines.append("")
    if goal:
        lines.append(f"\n(User goal: {goal})")
    return "\n".join(lines)


if __name__ == "__main__":
    get_index()  # warm the index before serving
    mcp.run(transport="stdio")

