from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Cursor-Co-pilot-Feature-Guide.pdf"
MASCOT = ROOT / "static" / "mascot.png"


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("&", "&amp;"), style)


def bullet(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(para(item, style), bulletColor=colors.HexColor("#f06432")) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
    )


def code(text: str, styles) -> KeepTogether:
    rows = []
    for line in text.strip().splitlines():
        rows.append([Paragraph(line.replace("&", "&amp;"), styles["Code"])])
    table = Table(rows, colWidths=[6.8 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#141311")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#f5f3ef")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#37322a")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return KeepTogether([table, Spacer(1, 8)])


def make_table(headers: list[str], rows: list[list[str]], styles, widths=None) -> Table:
    data = [[para(h, styles["TableHead"]) for h in headers]]
    data.extend([[para(cell, styles["TableCell"]) for cell in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f06432")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fbf8f1")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8d0c4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7a7368"))
    canvas.drawString(0.7 * inch, 0.45 * inch, "Cursor Co-pilot Feature Guide")
    canvas.drawRightString(7.8 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Cursor Co-pilot Feature Guide",
        author="Cursor Co-pilot",
        subject="Feature guide and operating instructions",
    )

    sample = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#141311"),
            spaceAfter=10,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=sample["BodyText"],
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4f473d"),
            spaceAfter=16,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#f06432"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#141311"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#262420"),
            spaceAfter=7,
            alignment=TA_LEFT,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#4f473d"),
            spaceAfter=5,
        ),
        "Code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#f5f3ef"),
        ),
        "TableHead": ParagraphStyle(
            "TableHead",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#262420"),
        ),
    }

    story = []
    story.append(Spacer(1, 0.25 * inch))
    if MASCOT.exists():
        img = Image(str(MASCOT), width=1.25 * inch, height=1.25 * inch)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 10))
    story.append(para("Cursor Co-pilot", styles["Title"]))
    story.append(para("Full Feature Guide and Operating Instructions", styles["Subtitle"]))
    story.append(para(f"Generated {date.today().isoformat()} from the local project workspace.", styles["Subtitle"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(para(
        "Cursor Co-pilot is a context-aware assistant for Cursor that combines an MCP server, "
        "local project scanner, official Cursor documentation retrieval, MCP recommendations, "
        "rule/config scaffolding, a web dashboard, and a native floating desktop companion.",
        styles["Body"],
    ))

    story.append(para("Executive Summary", styles["H1"]))
    story.append(bullet([
        "Primary mode: a Cursor MCP server named cursor-copilot with 11 callable tools.",
        "Desktop mode: a transparent always-on-top mascot launched by run_desktop_companion.bat.",
        "Project intelligence: scans manifests, file tree, README, Cursor rules, and Jupyter notebooks.",
        "Knowledge layer: BM25 retrieval over Cursor docs plus MCP catalog data.",
        "LLM layer: Anthropic, Gemini, and Ollama fallback chain with full backend error reporting.",
        "QA surface: health, project status, chat SSE, and MCP stdio smoke tests.",
    ], styles["Body"]))

    story.append(para("System Architecture", styles["H1"]))
    story.append(make_table(
        ["Component", "Files", "Role"],
        [
            ["MCP server", "mcp_server.py", "Exposes tools over stdio so Cursor and other MCP clients can call project-aware capabilities."],
            ["LLM backend", "llm.py", "Selects Anthropic, Gemini, or Ollama; falls through usable backends and reports the full failure chain."],
            ["Project scanner", "scanner.py", "Infers language, framework, package manager, SDKs, file summaries, and notebook health."],
            ["Retrieval and ingestion", "search.py, ingest.py", "Builds and queries a BM25 index over Cursor docs and the MCP catalog."],
            ["Artifact generation", "cursor_artifacts.py", "Renders Cursor rules and MCP config snippets."],
            ["Web dashboard", "app.py, ui.py", "Serves chat, project status, install/rule APIs, and health checks."],
            ["Desktop companion", "companion.py", "Native Tkinter overlay with drag, chat, dashboard open, and notebook warnings."],
            ["Desktop launcher", "desktop_launcher.py, run_desktop_companion.bat", "Starts or reuses the backend, waits for health, and launches the companion."],
        ],
        styles,
        widths=[1.35 * inch, 1.65 * inch, 4.1 * inch],
    ))

    story.append(PageBreak())
    story.append(para("Launch and Use Modes", styles["H1"]))
    story.append(para("Recommended desktop launch", styles["H2"]))
    story.append(code(r"""
run_desktop_companion.bat
""", styles))
    story.append(bullet([
        "Reuses a healthy backend on http://127.0.0.1:59712 when one is already running.",
        "Starts app.py on port 59712 when no backend is available.",
        "Sets OPEN_BROWSER=0 so the web dashboard does not steal focus.",
        "Launches companion.py after the health endpoint responds.",
        "Legacy run_companion.bat forwards to the same orchestrated launcher.",
    ], styles["Body"]))

    story.append(para("Floating companion interactions", styles["H2"]))
    story.append(bullet([
        "Left-click and drag to reposition the mascot.",
        "Right-click to open a small chat box and ask a question.",
        "Double-click to open the full dashboard.",
        "On launch, the companion calls /api/project/status and warns about Jupyter notebooks with out-of-order execution.",
        "A socket lock prevents duplicate companion widgets.",
    ], styles["Body"]))

    story.append(para("Web dashboard", styles["H2"]))
    story.append(code(r"""
python app.py
""", styles))
    story.append(para(
        "The dashboard starts on a random free port by default and opens a browser. "
        "Set PORT to pin the port and OPEN_BROWSER=0 to suppress browser auto-open.",
        styles["Body"],
    ))

    story.append(para("Local API usage", styles["H2"]))
    story.append(code(r"""
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/health"
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/project/status"
""", styles))
    story.append(para(
        "The chat endpoint streams Server-Sent Events. Project-aware questions such as stack scans "
        "and notebook health include local scanner context before the LLM answers.",
        styles["Body"],
    ))

    story.append(para("MCP Server Features", styles["H1"]))
    story.append(make_table(
        ["Tool", "Purpose", "LLM"],
        [
            ["ask_cursor_docs", "Answer Cursor feature questions grounded in official Cursor docs.", "Yes"],
            ["search_cursor_docs", "Return ranked Cursor documentation chunks without synthesis.", "No"],
            ["scan_project", "Scan a project for language, framework, package manager, SDKs, files, README, and notebook data.", "No"],
            ["suggest_mcp_servers", "Recommend MCP servers or skills from the indexed catalog for a goal and optional project scan.", "Optional"],
            ["generate_cursor_rule", "Generate .cursor/rules/*.mdc content for a behavior or convention.", "Yes"],
            ["scaffold_mcp_config", "Create merge-ready .cursor/mcp.json snippets from catalog server names.", "No"],
            ["recommend_setup", "One-call setup advisor: scan project, recommend servers, produce snippets and tips.", "Yes"],
            ["create_cursor_rule", "Generate and write a Cursor project rule file directly to disk.", "Yes"],
            ["install_mcp_server", "Install or merge a catalog MCP server into project/global MCP config.", "No"],
            ["scan_notebooks", "Report Jupyter notebook imports, variables, headers, execution counts, and order health.", "No"],
            ["search_knowledge_vault", "Search personal Markdown or Obsidian notes with BM25 ranking.", "No"],
        ],
        styles,
        widths=[1.45 * inch, 4.45 * inch, 0.65 * inch],
    ))

    story.append(PageBreak())
    story.append(para("Project Intelligence", styles["H1"]))
    story.append(bullet([
        "Detects Python, JavaScript/TypeScript, Go, Rust, Java, and other languages from file extensions.",
        "Reads package manifests such as requirements.txt and package.json.",
        "Infers frameworks such as Flask, FastAPI, Django, React, Next.js, Express, and others from dependencies.",
        "Detects notable SDKs and services such as Anthropic, Gemini/OpenAI-related libraries, Stripe, Supabase, AWS, Redis, Postgres, and ML/data libraries.",
        "Scans Jupyter notebooks for code/markdown cell counts, imports, variables, headers, execution counts, and out-of-order execution.",
        "Injects local project context into chat prompts for stack, project scan, Jupyter, and notebook questions.",
    ], styles["Body"]))

    story.append(para("Example project-aware prompts", styles["H2"]))
    story.append(code(r"""
Co-pilot, scan my project and tell me what stack we are using.
Does my Jupyter Notebook have any out-of-order execution issues?
Recommend MCP servers for this Python Flask project.
Create a Cursor rule for this repository's Python conventions.
""", styles))

    story.append(para("LLM and Retrieval Behavior", styles["H1"]))
    story.append(bullet([
        "Cursor docs answers are grounded in retrieved documentation chunks.",
        "Retrieval uses a local BM25 index built from Cursor docs and MCP catalog sources.",
        "LLM preference is configured with LLM_BACKEND; supported values are anthropic, gemini, and ollama.",
        "Backend resolution moves the preferred backend to the front, then falls through Anthropic, Gemini, and Ollama order.",
        "When all backends fail, the user-facing error reports every backend failure in order.",
        "Project/status API redacts secret-like MCP environment values before returning config data.",
    ], styles["Body"]))

    story.append(para("Configuration", styles["H1"]))
    story.append(make_table(
        ["Variable", "Default", "Meaning"],
        [
            ["ANTHROPIC_API_KEY", "unset", "Enables Claude backend."],
            ["ANTHROPIC_MODEL", "claude-opus-4-8", "Claude model selection."],
            ["GEMINI_API_KEY", "unset", "Enables Gemini backend."],
            ["GEMINI_MODEL", "gemini-2.5-flash", "Gemini model selection."],
            ["LLM_BACKEND", "anthropic", "Preferred backend; moved to the front of the fallback chain."],
            ["OLLAMA_MODEL", "gemma3:4b", "Local model name for Ollama."],
            ["OLLAMA_URL", "http://localhost:11434", "Ollama server URL."],
            ["TOP_K", "5", "Number of doc chunks retrieved for web chat."],
            ["PORT", "random", "Forces the web UI/API port."],
            ["OPEN_BROWSER", "1", "Set to 0 to suppress browser auto-open."],
        ],
        styles,
        widths=[1.45 * inch, 1.55 * inch, 4.1 * inch],
    ))

    story.append(PageBreak())
    story.append(para("Cursor and External Editor Integration", styles["H1"]))
    story.append(para("Cursor project MCP config", styles["H2"]))
    story.append(code(r"""
{
  "mcpServers": {
    "cursor-copilot": {
      "command": "C:/path/to/.venv/Scripts/python.exe",
      "args": ["C:/path/to/cursor-co-pilot/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "LLM_BACKEND": "gemini",
        "GEMINI_MODEL": "gemini-2.5-flash"
      }
    }
  }
}
""", styles))
    story.append(bullet([
        "In Cursor, enable the server from Cursor Settings > Features > MCP.",
        "Use an absolute venv python path on Windows so Cursor runs the correct interpreter.",
        "The same stdio MCP server can be registered in other MCP-capable editors such as Cline, Roo-Code, Windsurf, or Claude Desktop.",
        "Do not place literal API keys in docs or shared config examples; use environment placeholders.",
    ], styles["Body"]))

    story.append(para("Superpowers Workflow", styles["H1"]))
    story.append(code(r"""
/using-superpowers
/using-superpowers QA this companion integration end to end.
/using-superpowers Write an implementation plan before changing behavior.
/using-superpowers Debug why chat fallback is not using Gemini.
""", styles))
    story.append(bullet([
        "Use brainstorming before creative feature work or behavior changes.",
        "Use writing-plans before multi-step implementation.",
        "Use test-driven-development for bug fixes and behavior changes.",
        "Use systematic-debugging before fixes when behavior is unexpected.",
        "Use verification-before-completion before claiming anything is fixed or complete.",
    ], styles["Body"]))

    story.append(para("QA Checklist", styles["H1"]))
    story.append(code(r"""
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m py_compile app.py llm.py desktop_launcher.py companion.py mcp_server.py
Invoke-RestMethod -Uri "http://127.0.0.1:59712/api/health"
.\run_desktop_companion.bat
""", styles))
    story.append(bullet([
        "Health should report chunks > 0 and an active LLM backend.",
        "Launcher should say Backend already healthy when the backend is already running.",
        "Stack chat should mention Python, Flask, pip, SDKs, and notebook health for this project.",
        "MCP smoke test should list 11 tools and confirm scan_project plus scan_notebooks.",
        "Project status should redact GEMINI_API_KEY and other secret-like env values.",
    ], styles["Body"]))

    story.append(para("Troubleshooting", styles["H1"]))
    story.append(make_table(
        ["Symptom", "Likely Cause", "Action"],
        [
            ["MCP server will not connect", "Wrong Python path, missing deps, stdout pollution.", "Use absolute venv python path, install requirements, keep MCP logs on stderr."],
            ["Gemini 429 RESOURCE_EXHAUSTED", "Key is valid but credits or billing are depleted.", "Add credits, use another key, configure Anthropic, or start Ollama."],
            ["Chat says local model unreachable", "Ollama fallback is selected or reached but not running.", "Run ollama serve and pull the model, or configure a cloud backend."],
            ["Companion launches but no answer", "Backend unavailable or every LLM backend failed.", "Check /api/health and the SSE chat error chain."],
            ["Dashboard steals focus", "app.py launched directly with browser auto-open.", "Use run_desktop_companion.bat or set OPEN_BROWSER=0."],
            ["Notebook warning appears", "Scanner found out-of-order execution counts.", "Re-run notebook cells in order or clear outputs/execution counts."],
        ],
        styles,
        widths=[1.75 * inch, 2.25 * inch, 3.1 * inch],
    ))

    story.append(para("Verified Current State", styles["H1"]))
    story.append(bullet([
        "Desktop launcher reboot/reuse path verified.",
        "Backend health verified on port 59712 with Gemini active and 191 indexed chunks.",
        "Live project-aware chat verified for stack and notebook health questions.",
        "Unit suite verified with 13 passing tests.",
        "Python compile check verified for app.py, llm.py, desktop_launcher.py, companion.py, and mcp_server.py.",
        "Linter diagnostics reported no errors for touched files.",
    ], styles["Body"]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
    print(OUT)
