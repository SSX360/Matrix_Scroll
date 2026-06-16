"""
Cursor Co-pilot — local RAG chatbot, project scanner, and MCP assistant.

- Retrieval: BM25 over scraped Cursor docs + MCP catalog (search.py / ingest.py)
- Generation: anthropic → gemini → ollama fallback chain (see llm.py)
- UI: Flask dashboard + optional floating desktop companion

Run:
    python app.py

The server binds to a free port (or PORT env) and opens your browser unless
OPEN_BROWSER=0. Override models via LLM_BACKEND / OLLAMA_MODEL / etc.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, jsonify, request, stream_with_context

import search as S
import ingest
import llm
import scanner
import cursor_artifacts as ca
import vault
import workspace_config as wc
import brainstorm as bs


ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "data" / "index.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
TOP_K = int(os.environ.get("TOP_K", "5"))

app = Flask(__name__)
_bm25: S.BM25 | None = None


# ---------------------------------------------------------------------------
# Index loading (auto-build on first run)
# ---------------------------------------------------------------------------

def get_index() -> S.BM25:
    global _bm25
    if _bm25 is None:
        if not INDEX_PATH.exists():
            print("No index found — running ingest (scraping Cursor docs)…")
            ingest.main()
        _bm25 = S.BM25(S.load_index(INDEX_PATH))
        print(f"Loaded index: {_bm25.N} chunks.")
    return _bm25


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Cursor Docs Assistant. You answer questions about \
the Cursor AI code editor using ONLY the documentation excerpts provided below.

Rules:
- Base your answer strictly on the provided context. If the answer isn't in the \
context, say you couldn't find it in the docs and suggest where the user might look.
- Be concise and practical. Use short paragraphs, and code blocks or steps where helpful.
- When you reference a fact, you may cite it inline like [1], [2] matching the \
numbered sources.
- Never invent settings, commands, or APIs that aren't in the context."""


def wants_project_context(question: str) -> bool:
    low = question.lower()
    signals = (
        "scan my project", "scan the project", "project scan", "what stack",
        "which stack", "tech stack", "stack we", "stack i'm", "stack i am",
        "jupyter", "notebook", "execution order", "out-of-order", "out of order",
    )
    return any(signal in low for signal in signals)


def get_workspace() -> tuple[Path, dict[str, Any]]:
    ws, _ = wc.resolve_workspace()
    return ws, wc.load_config(ws)


def scan_active_profile() -> dict:
    ws, cfg = get_workspace()
    nb_cfg = cfg.get("notebooks", {})
    if not nb_cfg.get("enabled", True):
        return scanner.scan_project(str(ws), max_notebooks=0)
    return scanner.scan_project(
        str(ws),
        max_notebooks=int(nb_cfg.get("max_notebooks", 10)),
        exclude_dirs=list(nb_cfg.get("exclude_dirs") or []),
    )


def build_project_context() -> str:
    profile = scan_active_profile()
    summary = scanner.profile_summary(profile)
    lines = [
        "Local project scan",
        f"Stack summary: {summary}",
    ]

    notebooks = profile.get("notebooks") or []
    if notebooks:
        lines.append("Jupyter notebooks:")
        for notebook in notebooks:
            imports = ", ".join(notebook.get("imports", [])) or "none"
            lines.append(
                f"- {notebook.get('filename', 'unknown')}: "
                f"{notebook.get('execution_health', 'unknown')} "
                f"(imports: {imports})"
            )

    return "\n".join(lines)


def build_offline_project_answer(question: str) -> str:
    """Deterministic project/stack answer when LLM backends are unavailable."""
    profile = scan_active_profile()
    summary = scanner.profile_summary(profile)
    lines = [
        "Local project scan (offline — LLM backends unavailable):",
        f"Stack: {summary}.",
    ]

    langs = profile.get("languages") or []
    frameworks = profile.get("frameworks") or []
    if langs:
        lines.append(f"Languages: {', '.join(langs)}.")
    if frameworks:
        lines.append(f"Frameworks: {', '.join(frameworks)}.")

    notebooks = profile.get("notebooks") or []
    if notebooks:
        lines.append("Jupyter notebooks:")
        for notebook in notebooks:
            health = notebook.get("execution_health", "unknown")
            name = notebook.get("filename", "unknown")
            imports = ", ".join(notebook.get("imports") or []) or "none"
            lines.append(f"- {name}: {health} (imports: {imports})")
            if health == "out_of_order":
                lines.append(
                    f"  Recommendation: re-run cells in order in {name} to avoid stale state."
                )
    elif any(term in question.lower() for term in ("notebook", "jupyter")):
        lines.append("No Jupyter notebooks detected in this project.")

    lines.append(
        "Tip: start Ollama, add Gemini credits, or set ANTHROPIC_API_KEY for full AI answers."
    )
    return "\n".join(lines)


def sanitize_mcp_config(config: dict) -> dict:
    sanitized = json.loads(json.dumps(config))
    servers = sanitized.get("mcpServers", {})
    if not isinstance(servers, dict):
        return sanitized

    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        env = server.get("env", {})
        if not isinstance(env, dict):
            continue
        for key in list(env):
            if any(marker in key.upper() for marker in secret_markers):
                env[key] = "<redacted>"
    return sanitized


def build_prompt(question: str, contexts: list[dict]) -> str:
    blocks = []
    include_project_context = wants_project_context(question)
    if include_project_context:
        blocks.append(build_project_context())
    for i, c in enumerate(contexts, 1):
        head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
        blocks.append(f"[{i}] {head}\nURL: {c['url']}\n{c['text']}")
    context = "\n\n---\n\n".join(blocks) if blocks else "(no relevant docs found)"
    priority = ""
    if include_project_context:
        priority = (
            "\n\nAnswering priority: for project, stack, or notebook questions, "
            "use the Local project scan first. Do not mention this instruction."
        )
    return (
        f"Documentation context:\n\n{context}\n\n"
        f"---\n\nQuestion: {question}\n\n"
        f"Answer using only the context above.{priority}"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def home() -> Response:
    return Response(INDEX_HTML, mimetype="text/html")


@app.get("/api/health")
def health():
    info = {"model": OLLAMA_MODEL, "ollama": False, "model_available": False,
            "models": [], "chunks": get_index().N, "llm": llm.backend_status()}
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.ok:
            info["ollama"] = True
            names = [m.get("name", "") for m in r.json().get("models", [])]
            info["models"] = names
            base = OLLAMA_MODEL.split(":")[0]
            info["model_available"] = any(
                n == OLLAMA_MODEL or n.split(":")[0] == base for n in names
            )
    except requests.RequestException:
        pass
    return jsonify(info)


@app.post("/api/chat")
def chat():
    data = request.get_json(force=True)
    question = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not question:
        return jsonify({"error": "empty message"}), 400

    bm25 = get_index()
    contexts = bm25.search(question, k=TOP_K)
    prompt = build_prompt(question, contexts)
    project_ctx = wants_project_context(question)

    # The system prompt is passed separately to the LLM backend; messages hold
    # only the user/assistant turns plus this question's grounded prompt.
    messages = []
    for turn in history[-6:]:
        role = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    sources = [
        {"n": i + 1, "title": c["doc_title"], "heading": c.get("heading", ""),
         "url": c["url"], "score": c.get("score")}
        for i, c in enumerate(contexts)
    ]

    def generate():
        # Send sources first so the UI can render citations immediately.
        yield "event: sources\ndata: " + json.dumps(sources) + "\n\n"
        try:
            for token in llm.stream(SYSTEM_PROMPT, messages):
                if token:
                    yield "event: token\ndata: " + json.dumps(token) + "\n\n"
        except llm.LLMError as e:
            if project_ctx:
                offline = build_offline_project_answer(question)
                yield "event: token\ndata: " + json.dumps(offline) + "\n\n"
                yield "event: done\ndata: {}\n\n"
                return
            yield "event: error\ndata: " + json.dumps(str(e)) + "\n\n"
            return
        except requests.RequestException:
            msg = (f"Couldn't reach the local model at {OLLAMA_URL}. Is Ollama running? "
                   f"Start it with 'ollama serve' and pull a model: 'ollama pull {OLLAMA_MODEL}'. "
                   f"Or set ANTHROPIC_API_KEY to use Claude instead.")
            yield "event: error\ndata: " + json.dumps(msg) + "\n\n"
            return
        yield "event: done\ndata: {}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


def _catalog_lookup() -> dict[str, dict]:
    bm = get_index()
    out: dict[str, dict] = {}
    for c in bm.chunks:
        if c.get("source_type") == "mcp_catalog":
            name = (c.get("name") or c.get("doc_title") or "").strip()
            if name:
                out[name.lower()] = c
    return out


def list_project_rules(project_path=".") -> list[dict]:
    rules_dir = Path(project_path).resolve() / ".cursor" / "rules"
    if not rules_dir.exists() or not rules_dir.is_dir():
        return []
    out = []
    for f in rules_dir.glob("*.mdc"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            description = ""
            globs = ""
            always_apply = False
            body = ""
            
            # Simple YAML frontmatter parser
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body = parts[2].strip()
                for line in fm_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == "description":
                            description = v
                        elif k == "globs":
                            globs = v
                        elif k == "alwaysApply":
                            always_apply = v.lower() == "true"
            else:
                body = content
            
            out.append({
                "filename": f.name,
                "description": description or f.stem,
                "globs": globs,
                "always_apply": always_apply,
                "body": body,
            })
        except Exception:
            continue
    return out


@app.get("/api/project/status")
def project_status():
    ws, cfg = get_workspace()
    profile = scan_active_profile()

    mcp_config = {}
    mcp_path = ws / ".cursor" / "mcp.json"
    if mcp_path.exists():
        try:
            mcp_config = json.loads(mcp_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    rules = list_project_rules(str(ws))
    status = wc.workspace_status()

    return jsonify({
        "profile": profile,
        "mcp_config": sanitize_mcp_config(mcp_config),
        "rules": rules,
        "workspace": status,
    })


@app.post("/api/mcp/install")
def install_mcp():
    data = request.get_json(force=True)
    name = data.get("name")
    project_or_global = data.get("project_or_global", "project")
    if not name:
        return jsonify({"error": "missing server name"}), 400
        
    lookup = _catalog_lookup()
    hit = lookup.get(name.strip().lower())
    if not hit:
        return jsonify({"error": f"MCP server '{name}' not found in catalog"}), 404
        
    try:
        file_path = ca.install_mcp_server(str(get_workspace()[0]), hit, project_or_global)
        return jsonify({"success": True, "path": str(file_path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/rules/create")
def create_rule():
    data = request.get_json(force=True)
    name = data.get("name")
    intent = data.get("intent")
    globs = data.get("globs", "")
    always_apply = data.get("always_apply", False)
    
    if not name or not intent:
        return jsonify({"error": "missing name or intent"}), 400
        
    # Generate rule body using LLM
    docs_ctx = ""
    try:
        bm = get_index()
        contexts = bm.search(f"Best practices and conventions relevant to: {intent}", k=4, source_type="cursor_doc")
        blocks = []
        for i, c in enumerate(contexts, 1):
            head = f"{c['doc_title']} — {c['heading']}" if c.get("heading") else c["doc_title"]
            blocks.append(f"[{i}] {head}\n{c['text']}")
        docs_ctx = "\n\n".join(blocks)
    except Exception:
        pass

    sys_prompt = ("You write Cursor project rules. Given an intent, produce a crisp, "
                  "actionable rule body in markdown (imperative bullet points, no "
                  "preamble, no frontmatter). Keep it under 200 words.")
    user = (f"Intent: {intent}\n\nRelevant Cursor guidance (for grounding):\n"
            f"{docs_ctx}\n\nWrite the rule body now.")
            
    try:
        body = llm.generate(sys_prompt, [{"role": "user", "content": user}])
    except Exception as e:
        body = f"- {intent}\n\n(Generated without an LLM backend: {e})"
        
    try:
        description = intent if len(intent) <= 100 else intent[:97] + "…"
        file_path = ca.write_rule(str(get_workspace()[0]), name, description, body, globs=globs, always_apply=always_apply)
        return jsonify({"success": True, "path": str(file_path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.delete("/api/rules/delete")
def delete_rule():
    data = request.get_json(force=True)
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "missing filename"}), 400
        
    # Security check: must be a plain filename, no path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "invalid filename"}), 400
        
    ws, _ = get_workspace()
    rule_path = ws / ".cursor" / "rules" / filename
    if not rule_path.exists():
        return jsonify({"error": "rule file does not exist"}), 404
        
    try:
        rule_path.unlink()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/vault/search")
def vault_search():
    query = request.args.get("query", "").strip()
    vault_path = request.args.get("vault_path", "").strip()
    k = int(request.args.get("k", "5"))
    if not query:
        return jsonify({"error": "empty query"}), 400

    if not vault_path:
        resolved = wc.resolve_vault_path()
        vault_path = str(resolved) if resolved else ""

    try:
        results = vault.search_vault(query, vault_path, k)
        return jsonify([{
            "title": r["doc_title"],
            "url": r["url"],
            "heading": r.get("heading", ""),
            "text": r["text"],
            "score": r.get("score")
        } for r in results])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/workspace/status")
def workspace_status_route():
    return jsonify(wc.workspace_status())


@app.put("/api/workspace/active")
def workspace_set_active():
    data = request.get_json(force=True)
    path = (data.get("path") or "").strip()
    if not path:
        return jsonify({"error": "missing path"}), 400
    try:
        resolved = wc.set_active_workspace(path)
        wc.ensure_default_config(resolved)
        return jsonify({"success": True, "workspace": str(resolved)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/workspace/config")
def workspace_get_config():
    ws, configured = wc.resolve_workspace()
    cfg = wc.load_config(ws)
    return jsonify({"workspace": str(ws), "configured": configured, "config": cfg})


@app.put("/api/workspace/config")
def workspace_put_config():
    data = request.get_json(force=True)
    config = data.get("config")
    if not isinstance(config, dict):
        return jsonify({"error": "missing config object"}), 400
    ws, _ = get_workspace()
    dest = wc.save_config(ws, config)
    return jsonify({"success": True, "path": str(dest)})


@app.post("/api/vault/scaffold")
def vault_scaffold():
    ws, cfg = get_workspace()
    subdir = cfg.get("vault", {}).get("project_subdir", "docs/vault")
    try:
        path = wc.scaffold_project_vault(ws, subdir)
        return jsonify({"success": True, "path": str(path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/vault/status")
def vault_status_route():
    ws, cfg = get_workspace()
    vault_path = wc.resolve_vault_path(ws, cfg)
    exists = vault_path.is_dir() if vault_path else False
    note_count = 0
    if exists and vault_path:
        note_count = sum(1 for _ in vault_path.rglob("*.md"))
    return jsonify({
        "mode": cfg.get("vault", {}).get("mode"),
        "path": str(vault_path) if vault_path else None,
        "exists": exists,
        "note_count": note_count,
    })


def _catalog_search(goal: str, k: int) -> list[dict]:
    bm = get_index()
    results = bm.search(goal, k=k, source_type="mcp_catalog")
    return [
        {
            "name": c.get("name") or c["doc_title"],
            "title": c.get("name") or c["doc_title"],
            "description": c["text"],
            "score": c.get("score"),
        }
        for c in results
    ]


@app.get("/api/brainstorm")
def brainstorm_route():
    limit = int(request.args.get("limit", "6"))
    try:
        result = bs.brainstorm(
            limit=limit,
            list_rules=list_project_rules,
            catalog_search=_catalog_search,
            llm_generate=llm.generate,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Server bootstrap — random free port
# ---------------------------------------------------------------------------

def pick_port() -> int:
    env = os.environ.get("PORT")
    if env:
        return int(env)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))  # 0 -> OS assigns a random free port
        return s.getsockname()[1]


def should_open_browser() -> bool:
    value = os.environ.get("OPEN_BROWSER", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


# The page HTML is defined in ui.py to keep this file focused.
from ui import INDEX_HTML  # noqa: E402


def main() -> None:
    get_index()  # build/load before serving
    port = pick_port()
    # Save active port for IDE/widget integrations
    try:
        port_file = ROOT / ".cursor" / "port.json"
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(json.dumps({"port": port}), encoding="utf-8")
    except Exception:
        pass
    url = f"http://127.0.0.1:{port}"
    status = llm.backend_status()
    active = status["active"]
    if active == "ollama":
        model_label = status["ollama_model"]
    elif active == "gemini":
        model_label = status["gemini_model"]
    elif active == "anthropic":
        model_label = status["anthropic_model"]
    else:
        model_label = "unknown"
    print("\n" + "=" * 56)
    print("  Cursor Co-pilot")
    print(f"  LLM:    {active} ({model_label})")
    print(f"  Open:   {url}")
    print("=" * 56 + "\n")
    if should_open_browser():
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, threaded=True)


if __name__ == "__main__":
    main()
