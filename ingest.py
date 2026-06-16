"""
Scrape the full Cursor documentation and build a local search index.

Cursor publishes an LLM-friendly index at https://cursor.com/llms.txt that lists
every documentation page. Each page is available as raw markdown by appending
`.md` to its URL. This script downloads them all into ./data/docs and builds
./data/index.json for the chat app.

The bot also recommends MCP servers/skills. We ingest an MCP *catalog* from
several sources into the SAME index (tagged source_type="mcp_catalog"), so the
co-pilot can rank-search servers offline alongside the docs.

Usage:
    python ingest.py                 # docs + catalog -> build index
    python ingest.py --seed          # (re)build index from local docs (+ cached catalog)
    python ingest.py --catalog-only  # refresh only the MCP catalog, then rebuild index
    python ingest.py --no-catalog    # docs only, skip the MCP catalog
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

import search as S

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = DATA / "docs"
CATALOG = DATA / "catalog"
INDEX = DATA / "index.json"
LLMS_TXT = "https://cursor.com/llms.txt"

HEADERS = {"User-Agent": "cursor-docs-bot/1.0 (local docs assistant)"}

# MCP catalog sources.
REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"
SERVERS_README = ("https://raw.githubusercontent.com/modelcontextprotocol/"
                  "servers/main/README.md")
MCPMARKET_SITEMAP = "https://mcpmarket.com/sitemap.xml"


def discover_urls() -> list[str]:
    """Pull every *.md doc URL from the published llms.txt index."""
    print(f"Fetching index: {LLMS_TXT}")
    resp = requests.get(LLMS_TXT, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    raw = resp.text

    urls = re.findall(r"https://cursor\.com[^\s)\]]+?\.md", raw)
    cleaned = set()
    for u in urls:
        # Fix a known malformed entry like "https://cursor.comhttps://cursor.com/..."
        u = u.replace("https://cursor.comhttps://cursor.com", "https://cursor.com")
        cleaned.add(u)
    out = sorted(cleaned)
    print(f"Discovered {len(out)} documentation pages.")
    return out


def slug_for(url: str) -> str:
    path = urlparse(url).path.lstrip("/")
    if path.endswith(".md"):
        path = path[:-3]
    return path.replace("/", "__") + ".md"


def download_all(urls: list[str]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls, 1):
        dest = DOCS / slug_for(url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200 or not resp.text.strip():
                print(f"  [{i}/{len(urls)}] skip ({resp.status_code}) {url}")
                continue
            dest.write_text(resp.text, encoding="utf-8")
            print(f"  [{i}/{len(urls)}] saved {dest.name}")
        except requests.RequestException as e:
            print(f"  [{i}/{len(urls)}] error {url}: {e}")
        time.sleep(0.15)  # be polite


def url_for_slug(slug: str) -> str:
    path = slug[:-3] if slug.endswith(".md") else slug
    path = path.replace("__", "/")
    return f"https://cursor.com/{path}"


# ---------------------------------------------------------------------------
# MCP catalog ingestion
# ---------------------------------------------------------------------------
#
# Each cached catalog file is a JSON list of normalized entries:
#   {name, description, tags[], source_url, github_url, install_snippet}
# install_snippet is a JSON string holding the .cursor/mcp.json config value for
# that server (e.g. {"command": "npx", "args": ["-y", "..."]} or {"url": "..."}).

def _registry_install_snippet(server: dict) -> str:
    """Derive a .cursor/mcp.json config fragment from a registry entry."""
    for pkg in server.get("packages") or []:
        rt = pkg.get("registryType")
        ident = pkg.get("identifier")
        if not ident:
            continue
        if rt == "npm":
            cfg: dict = {"command": "npx", "args": ["-y", ident]}
        elif rt == "pypi":
            cfg = {"command": "uvx", "args": [ident]}
        elif rt == "oci":
            cfg = {"command": "docker", "args": ["run", "-i", "--rm", ident]}
        else:
            continue
        envs = pkg.get("environmentVariables") or []
        env = {e["name"]: "${env:" + e["name"] + "}"
               for e in envs if e.get("name")}
        if env:
            cfg["env"] = env
        return json.dumps(cfg)
    for r in server.get("remotes") or []:
        if r.get("url"):
            return json.dumps({"url": r["url"], "type": r.get("type", "http")})
    return ""


def fetch_registry_catalog(max_servers: int = 400) -> list[dict]:
    """Page through the official MCP registry API into normalized entries."""
    entries: list[dict] = []
    cursor = None
    print(f"Fetching MCP registry: {REGISTRY_API}")
    while len(entries) < max_servers:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        try:
            r = requests.get(REGISTRY_API, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  registry fetch stopped: {e}")
            break
        for item in data.get("servers", []):
            s = item.get("server", {})
            name = s.get("name", "")
            if not name:
                continue
            github = name.split("/")[0] if "/" in name else ""
            entries.append({
                "name": s.get("title") or name,
                "description": s.get("description", ""),
                "tags": _tags_from_name(name),
                "source_url": f"https://registry.modelcontextprotocol.io/?search={name}",
                "github_url": f"https://{github}" if "." in github else "",
                "install_snippet": _registry_install_snippet(s),
            })
        cursor = (data.get("metadata") or {}).get("nextCursor")
        if not cursor:
            break
        time.sleep(0.1)
    print(f"  registry: {len(entries)} servers")
    return entries


def _tags_from_name(name: str) -> str:
    # Turn "io.github.acme/postgres-mcp" into "acme postgres mcp" for ranking.
    bits = re.split(r"[./_-]", name.lower())
    drop = {"io", "com", "ai", "app", "github", "mcp", "server", "www", "co", ""}
    return " ".join(b for b in bits if b not in drop)


def fetch_servers_readme_catalog() -> list[dict]:
    """Parse the modelcontextprotocol/servers README list as enrichment."""
    print(f"Fetching reference servers: {SERVERS_README}")
    try:
        r = requests.get(SERVERS_README, headers=HEADERS, timeout=30)
        r.raise_for_status()
        md = r.text
    except requests.RequestException as e:
        print(f"  servers README skipped: {e}")
        return []
    entries = []
    # Lines like: "- **[Name](url)** - description"
    pat = re.compile(r"^\s*[-*]\s*\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s*[-–—:]?\s*(.*)$")
    for line in md.splitlines():
        m = pat.match(line)
        if not m:
            continue
        name, url, desc = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if not name or len(name) > 80:
            continue
        github = url if "github.com" in url else ""
        entries.append({
            "name": name,
            "description": re.sub(r"\*\*|`", "", desc)[:400],
            "tags": _tags_from_name(name),
            "source_url": url,
            "github_url": github,
            "install_snippet": "",
        })
    print(f"  reference servers: {len(entries)} entries")
    return entries


def fetch_mcpmarket_catalog(max_pages: int = 60) -> list[dict]:
    """Best-effort mcpmarket.com scrape. It rate-limits aggressively (429); we
    back off and give up rather than fail the whole ingest."""
    print(f"Fetching mcpmarket sitemap: {MCPMARKET_SITEMAP}")
    ua = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36")}
    try:
        r = requests.get(MCPMARKET_SITEMAP, headers=ua, timeout=20)
        if r.status_code == 429:
            print("  mcpmarket rate-limited (429); skipping.")
            return []
        r.raise_for_status()
        urls = re.findall(r"<loc>(https://mcpmarket\.com/server/[^<]+)</loc>", r.text)
    except requests.RequestException as e:
        print(f"  mcpmarket skipped: {e}")
        return []
    entries = []
    misses = 0
    for i, url in enumerate(urls[:max_pages]):
        try:
            pr = requests.get(url, headers=ua, timeout=20)
            if pr.status_code == 429:
                misses += 1
                if misses >= 3:
                    print("  mcpmarket repeated 429; stopping early.")
                    break
                time.sleep(2.0)
                continue
            if pr.status_code != 200:
                continue
            slug = url.rstrip("/").split("/")[-1]
            title = re.search(r"<title>([^<]+)</title>", pr.text)
            desc = re.search(r'<meta name="description" content="([^"]+)"', pr.text)
            entries.append({
                "name": (title.group(1).split("|")[0].strip() if title else slug),
                "description": desc.group(1).strip() if desc else "",
                "tags": _tags_from_name(slug),
                "source_url": url,
                "github_url": "",
                "install_snippet": "",
            })
            misses = 0
        except requests.RequestException:
            continue
        time.sleep(0.6)  # polite throttle
    print(f"  mcpmarket: {len(entries)} entries")
    return entries


def refresh_catalog() -> None:
    """Pull every catalog source and cache each to data/catalog/*.json."""
    CATALOG.mkdir(parents=True, exist_ok=True)
    sources = {
        "registry": fetch_registry_catalog,
        "servers_readme": fetch_servers_readme_catalog,
        "mcpmarket": fetch_mcpmarket_catalog,
    }
    for fname, fetch in sources.items():
        try:
            entries = fetch()
        except Exception as e:  # noqa: BLE001 - one bad source must not abort the rest
            print(f"  {fname} errored: {e}")
            entries = []
        if entries:
            (CATALOG / f"{fname}.json").write_text(
                json.dumps(entries, indent=1), encoding="utf-8")


def load_catalog_entries() -> list[dict]:
    """Read all cached catalog files, deduped by lowercased name."""
    if not CATALOG.exists():
        return []
    seen, out = set(), []
    for f in sorted(CATALOG.glob("*.json")):
        try:
            entries = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for e in entries:
            key = (e.get("name") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(e)
    return out


def catalog_chunks(entries: list[dict]) -> list[S.Chunk]:
    chunks = []
    for e in entries:
        name = e.get("name", "")
        desc = e.get("description", "")
        tags = e.get("tags", "")
        chunks.append(S.Chunk(
            doc_title=name,
            url=e.get("source_url", ""),
            heading="",
            text=f"{desc}\n\nTags: {tags}".strip(),
            source_type="mcp_catalog",
            name=name,
            tags=tags,
            github_url=e.get("github_url", ""),
            install_snippet=e.get("install_snippet", ""),
        ))
    return chunks


# ---------------------------------------------------------------------------
# Index build
# ---------------------------------------------------------------------------

def build() -> int:
    files = sorted(DOCS.glob("*.md"))
    all_chunks: list[S.Chunk] = []
    for f in files:
        md = f.read_text(encoding="utf-8")
        url = url_for_slug(f.name)
        fallback = f.stem.replace("__", " / ")
        all_chunks.extend(S.chunk_markdown(md, url, fallback))
    doc_n = len(all_chunks)

    cat_entries = load_catalog_entries()
    all_chunks.extend(catalog_chunks(cat_entries))

    if not all_chunks:
        print("No docs or catalog found - run without --seed to fetch them.")
        return 0
    index = S.build_index(all_chunks)
    S.save_index(index, INDEX)
    print(f"Indexed {doc_n} doc chunks from {len(files)} pages "
          f"+ {len(cat_entries)} catalog entries -> {INDEX}")
    return len(all_chunks)


def main() -> None:
    args = set(sys.argv[1:])
    catalog_only = "--catalog-only" in args
    seed_only = "--seed" in args
    skip_catalog = "--no-catalog" in args

    if catalog_only:
        refresh_catalog()
        build()
        return

    if not seed_only:
        try:
            urls = discover_urls()
            download_all(urls)
        except requests.RequestException as e:
            print(f"Could not reach cursor.com ({e}). Building index from local docs only.")

    # --seed rebuilds from local docs but still uses whatever catalog is cached;
    # a full run refreshes the catalog from the network unless --no-catalog.
    if not skip_catalog and not seed_only:
        refresh_catalog()
    build()


if __name__ == "__main__":
    main()
