"""The single-page chat UI, served by app.py."""

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Cursor Co-pilot Dashboard</title>
<link rel="preconnect" href="https://cdnjs.cloudflare.com" />
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.11/purify.min.js"></script>
<style>
  :root{
    --bg:#090908; --bg-2:#0f0e0c; --panel:#141311; --panel-2:#1c1a16;
    --border:#262420; --border-soft:#1d1b18;
    --text:#f5f3ef; --muted:#a9a59d; --faint:#7b766c;
    --accent:#f0a842; --accent-2:#e08028; --accent-soft:rgba(240,168,66,.12);
    --user:#23201a; --ok:#5ccc84; --bad:#e85a5a; --warn:#f0b242;
    --shadow:0 10px 30px rgba(0,0,0,.6);
    --radius:16px;
    --radius-sm:10px;
    --font:'Inter', sans-serif;
    --font-display:'Outfit', sans-serif;
    --mono:'SFMono-Regular',ui-monospace,'JetBrains Mono',monospace;
  }
  *{box-sizing:border-box}
  html,body{height:100%;margin:0;font-family:var(--font);color:var(--text);background:var(--bg);overflow:hidden}
  
  /* App Layout */
  .app-layout{
    display:flex;
    height:100vh;
    width:100vw;
  }

  /* Sidebars common */
  .sidebar{
    width:320px;
    flex-shrink:0;
    background:var(--bg-2);
    border-right:1px solid var(--border);
    display:flex;
    flex-direction:column;
    height:100%;
    z-index:2;
    transition:all .3s ease;
    overflow-y:auto;
  }
  .sidebar.right-sidebar{
    border-right:none;
    border-left:1px solid var(--border);
  }
  .sidebar-header{
    padding:16px 20px;
    border-bottom:1px solid var(--border-soft);
    display:flex;
    align-items:center;
    justify-content:space-between;
  }
  .sidebar-header h3{
    font-family:var(--font-display);
    font-size:15px;
    font-weight:600;
    margin:0;
    letter-spacing:.5px;
    color:var(--accent);
    text-transform:uppercase;
  }
  .sidebar-section{
    padding:20px;
    border-bottom:1px solid var(--border-soft);
  }
  .sidebar-section:last-child{
    border-bottom:none;
  }
  .section-title{
    font-size:11px;
    font-weight:700;
    text-transform:uppercase;
    color:var(--faint);
    margin-bottom:12px;
    letter-spacing:.8px;
    display:flex;
    align-items:center;
    justify-content:space-between;
  }

  /* Left Sidebar Elements */
  .stack-pills{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
  }
  .pill{
    font-size:11px;
    padding:4px 8px;
    border-radius:6px;
    background:var(--panel);
    border:1px solid var(--border);
    color:var(--muted);
    font-weight:550;
  }
  .pill.highlight{
    color:var(--accent);
    border-color:var(--accent-soft);
    background:var(--accent-soft);
  }

  /* Notebook list */
  .notebook-card{
    background:var(--panel);
    border:1px solid var(--border-soft);
    border-radius:var(--radius-sm);
    padding:10px 12px;
    margin-bottom:10px;
    font-size:12px;
  }
  .notebook-name{
    font-weight:600;
    color:var(--text);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    margin-bottom:6px;
  }
  .notebook-meta{
    display:flex;
    justify-content:space-between;
    align-items:center;
    color:var(--faint);
    font-size:11px;
    margin-bottom:6px;
  }
  .health-dot{
    display:inline-block;
    width:7px;
    height:7px;
    border-radius:50%;
    margin-right:4px;
  }
  .health-dot.ordered{
    background:var(--ok);
  }
  .health-dot.out_of_order{
    background:var(--warn);
    box-shadow:0 0 8px var(--warn);
  }
  .notebook-details{
    border-top:1px solid var(--border-soft);
    padding-top:6px;
    margin-top:6px;
  }
  .notebook-details summary{
    cursor:pointer;
    color:var(--muted);
    font-size:10.5px;
    outline:none;
  }
  .notebook-details ul{
    margin:4px 0 0;
    padding-left:14px;
    color:var(--muted);
  }

  /* Rules list */
  .rule-item{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:8px 10px;
    background:var(--panel);
    border:1px solid var(--border-soft);
    border-radius:var(--radius-sm);
    margin-bottom:8px;
    font-size:12.5px;
  }
  .rule-info{
    min-width:0;
    flex:1;
  }
  .rule-title{
    font-weight:600;
    color:var(--text);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  .rule-desc{
    font-size:11px;
    color:var(--muted);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  .action-btn{
    background:none;
    border:none;
    color:var(--faint);
    cursor:pointer;
    padding:4px;
    display:grid;
    place-items:center;
    border-radius:4px;
    transition:all .15s;
  }
  .action-btn:hover{
    color:var(--bad);
    background:rgba(232,90,90,.08);
  }
  .add-rule-trigger{
    width:100%;
    padding:8px;
    background:none;
    border:1px dashed var(--border);
    border-radius:var(--radius-sm);
    color:var(--muted);
    font-size:12px;
    cursor:pointer;
    font-weight:550;
    transition:all .2s;
  }
  .add-rule-trigger:hover{
    border-color:var(--accent);
    color:var(--accent);
  }

  /* Right Sidebar Elements - Vault & MCP catalog */
  .vault-config{
    margin-bottom:12px;
  }
  .input-group{
    display:flex;
    flex-direction:column;
    gap:4px;
    margin-bottom:10px;
  }
  .input-label{
    font-size:10px;
    font-weight:600;
    color:var(--faint);
    text-transform:uppercase;
  }
  .sidebar-input{
    width:100%;
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:var(--radius-sm);
    padding:8px 12px;
    color:var(--text);
    font-size:12px;
    outline:none;
    transition:border-color .15s;
  }
  .sidebar-input:focus{
    border-color:var(--accent);
  }
  .search-results{
    margin-top:10px;
    max-height:220px;
    overflow-y:auto;
  }
  .search-result-item{
    background:var(--panel);
    border:1px solid var(--border-soft);
    border-radius:var(--radius-sm);
    padding:8px;
    margin-bottom:6px;
    font-size:11.5px;
    cursor:pointer;
  }
  .search-result-item:hover{
    border-color:var(--accent);
  }
  .search-result-title{
    font-weight:600;
    color:var(--accent);
    margin-bottom:3px;
  }
  .search-result-text{
    color:var(--muted);
    font-size:11px;
    line-height:1.4;
    display:-webkit-box;
    -webkit-line-clamp:2;
    -webkit-box-orient:vertical;
    overflow:hidden;
  }

  /* MCP catalog items */
  .mcp-item{
    background:var(--panel);
    border:1px solid var(--border-soft);
    border-radius:var(--radius-sm);
    padding:10px 12px;
    margin-bottom:8px;
    font-size:12px;
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:10px;
  }
  .mcp-info{
    flex:1;
    min-width:0;
  }
  .mcp-name{
    font-weight:600;
    color:var(--text);
    display:flex;
    align-items:center;
    gap:5px;
  }
  .mcp-desc{
    font-size:11px;
    color:var(--muted);
    line-height:1.4;
    margin-top:2px;
  }
  .mcp-tag{
    font-size:9.5px;
    color:var(--faint);
    background:rgba(255,255,255,.03);
    padding:2px 4px;
    border-radius:3px;
    margin-top:4px;
    display:inline-block;
  }
  .install-btn{
    padding:4px 8px;
    background:var(--accent-soft);
    border:1px solid var(--accent-soft);
    border-radius:6px;
    color:var(--accent);
    font-size:11px;
    font-weight:600;
    cursor:pointer;
    white-space:nowrap;
    transition:all .15s;
  }
  .install-btn:hover{
    background:var(--accent);
    color:#12100a;
  }
  .install-btn.installed{
    background:none;
    border-color:var(--border);
    color:var(--faint);
    cursor:default;
  }

  /* Main Chat Area */
  .chat-container{
    flex:1;
    display:flex;
    flex-direction:column;
    height:100%;
    position:relative;
    background:radial-gradient(1000px 500px at 50% -10%,rgba(240,168,66,.04),transparent 65%), var(--bg);
  }
  header{
    display:flex;
    align-items:center;
    gap:14px;
    padding:16px 24px;
    border-bottom:1px solid var(--border-soft);
    background:rgba(9,9,8,.7);
    backdrop-filter:blur(12px);
    z-index:5;
  }
  .mark{
    width:36px;
    height:36px;
    border-radius:10px;
    flex:none;
    background:linear-gradient(140deg,var(--accent),var(--accent-2));
    display:grid;
    place-items:center;
    color:#12100a;
    font-family:var(--font-display);
    font-weight:800;
    font-size:18px;
    box-shadow:0 4px 20px rgba(240,168,66,.25);
  }
  .titles h1{
    font-family:var(--font-display);
    font-size:16px;
    margin:0;
    letter-spacing:.2px;
    font-weight:700;
  }
  .titles p{
    font-size:12px;
    margin:2px 0 0;
    color:var(--faint);
  }
  .status{
    margin-left:auto;
    display:flex;
    align-items:center;
    gap:8px;
    font-size:12px;
    color:var(--muted);
    padding:6px 14px;
    border-radius:999px;
    border:1px solid var(--border);
    background:var(--panel);
  }
  .dot{width:8px;height:8px;border-radius:50%;background:var(--faint);transition:.3s}
  .dot.ok{background:var(--ok);box-shadow:0 0 10px rgba(92,204,132,.4)}
  .dot.bad{background:var(--bad);box-shadow:0 0 10px rgba(232,90,90,.4)}

  /* Chat list */
  main{
    flex:1;
    overflow-y:auto;
    scroll-behavior:smooth;
  }
  .wrap{
    max-width:760px;
    margin:0 auto;
    padding:24px 20px 140px;
  }

  /* Empty state */
  .hero{text-align:center;padding:10vh 0 4vh;animation:fade .6s ease}
  .hero .big{
    width:64px;
    height:64px;
    border-radius:18px;
    margin:0 auto 20px;
    background:linear-gradient(140deg,var(--accent),var(--accent-2));
    display:grid;
    place-items:center;
    color:#12100a;
    font-family:var(--font-display);
    font-weight:800;
    font-size:30px;
    box-shadow:0 10px 30px rgba(240,168,66,.25);
  }
  .hero h2{font-family:var(--font-display);font-size:26px;margin:0 0 8px;letter-spacing:-.4px;font-weight:600}
  .hero p{color:var(--muted);margin:0 auto;max-width:440px;line-height:1.6;font-size:14.5px}
  .chips{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:30px}
  .chip{
    text-align:left;border:1px solid var(--border);background:var(--panel);
    color:var(--text);padding:14px 16px;border-radius:14px;cursor:pointer;
    font-size:13.5px;line-height:1.45;transition:.18s;font-family:inherit;
  }
  .chip:hover{border-color:var(--accent);background:var(--panel-2);transform:translateY(-2px)}
  .chip span{display:block;color:var(--faint);font-size:11px;margin-top:4px;font-weight:550}

  /* Messages */
  .msg{display:flex;gap:16px;margin:24px 0;animation:fade .35s ease}
  .avatar{
    width:32px;height:32px;border-radius:9px;flex:none;display:grid;place-items:center;
    font-size:14px;font-family:var(--font-display);font-weight:700;margin-top:2px;
  }
  .msg.user .avatar{background:var(--user);color:var(--accent);border:1px solid var(--border)}
  .msg.bot .avatar{background:linear-gradient(140deg,var(--accent),var(--accent-2));color:#12100a}
  .bubble{flex:1;min-width:0}
  .who{font-size:12px;color:var(--faint);margin-bottom:6px;font-weight:600;letter-spacing:.3px}
  .content{font-size:15px;line-height:1.75;color:var(--text);word-wrap:break-word}
  .content p{margin:0 0 12px}
  .content p:last-child{margin-bottom:0}
  .content h1,.content h2,.content h3{margin:20px 0 10px;line-height:1.3;font-family:var(--font-display)}
  .content ul,.content ol{margin:0 0 12px;padding-left:22px}
  .content li{margin:4px 0}
  .content a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent-soft)}
  .content a:hover{border-color:var(--accent)}
  .content code{
    font-family:var(--mono);font-size:13px;background:rgba(255,255,255,.04);
    padding:2px 6px;border-radius:6px;border:1px solid var(--border-soft);
  }
  .content pre{
    background:#0b0a09;border:1px solid var(--border);border-radius:12px;
    padding:14px 16px;overflow-x:auto;margin:0 0 14px;
  }
  .content pre code{background:none;border:none;padding:0;font-size:13px;line-height:1.55}
  .content table{border-collapse:collapse;width:100%;margin:0 0 14px;font-size:13px}
  .content th,.content td{border:1px solid var(--border);padding:7px 10px;text-align:left}
  .content th{background:var(--panel)}
  .content blockquote{border-left:3px solid var(--accent);margin:0 0 12px;padding:2px 14px;color:var(--muted);background:rgba(240,168,66,.02)}

  /* Caret while streaming */
  .caret::after{
    content:'';display:inline-block;width:8px;height:16px;margin-left:2px;
    background:var(--accent);vertical-align:-3px;border-radius:1px;animation:blink 1s steps(2) infinite;
  }
  .think{display:inline-flex;gap:5px;padding:4px 0}
  .think i{width:7px;height:7px;border-radius:50%;background:var(--faint);animation:bounce 1.2s infinite}
  .think i:nth-child(2){animation-delay:.15s}
  .think i:nth-child(3){animation-delay:.3s}

  /* Sources details */
  .sources{margin-top:14px;border:1px solid var(--border);border-radius:12px;background:var(--panel);overflow:hidden}
  .sources summary{
    cursor:pointer;list-style:none;padding:10px 14px;font-size:12.5px;color:var(--muted);
    display:flex;align-items:center;gap:8px;user-select:none;
  }
  .sources summary::-webkit-details-marker{display:none}
  .sources summary b{color:var(--accent);font-weight:600}
  .src-list{padding:2px 8px 10px}
  .src{
    display:flex;gap:10px;align-items:baseline;padding:8px;border-radius:8px;
    text-decoration:none;color:var(--text);transition:.15s;
  }
  .src:hover{background:var(--panel-2)}
  .src .num{font-size:11px;color:#12100a;background:var(--accent);min-width:18px;height:18px;
    border-radius:5px;display:grid;place-items:center;font-weight:700;flex:none;transform:translateY(2px)}
  .src .meta{min-width:0}
  .src .t{font-size:13.5px;font-weight:550}
  .src .u{font-size:11.5px;color:var(--faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

  /* Composer */
  .composer-wrap{
    position:absolute;left:0;right:0;bottom:0;padding:16px 24px 24px;
    background:linear-gradient(to top,var(--bg) 60%,transparent);
  }
  .composer{
    max-width:760px;margin:0 auto;display:flex;gap:10px;align-items:flex-end;
    border:1px solid var(--border);background:var(--panel);border-radius:var(--radius);
    padding:10px 10px 10px 18px;box-shadow:var(--shadow);transition:all .2s;
  }
  .composer:focus-within{border-color:var(--accent);box-shadow:0 0 15px rgba(240,168,66,.08), var(--shadow)}
  textarea{
    flex:1;border:none;outline:none;background:none;color:var(--text);resize:none;
    font-family:inherit;font-size:15px;line-height:1.5;max-height:140px;padding:7px 0;
  }
  textarea::placeholder{color:var(--faint)}
  .send{
    width:38px;height:38px;border-radius:11px;border:none;cursor:pointer;flex:none;
    background:linear-gradient(140deg,var(--accent),var(--accent-2));color:#12100a;
    display:grid;place-items:center;transition:.18s;
  }
  .send:hover{filter:brightness(1.08)}
  .send:disabled{opacity:.4;cursor:not-allowed;filter:none}
  .send.stop{background:var(--panel-2);color:var(--text);border:1px solid var(--border)}
  .hint{max-width:760px;margin:8px auto 0;text-align:center;font-size:11px;color:var(--faint)}

  /* Modal styling */
  .modal-overlay{
    position:fixed;
    top:0;left:0;right:0;bottom:0;
    background:rgba(0,0,0,.7);
    backdrop-filter:blur(4px);
    display:none;
    place-items:center;
    z-index:100;
  }
  .modal{
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:var(--radius);
    width:480px;
    max-width:90%;
    padding:24px;
    box-shadow:var(--shadow);
    animation:fade .25s ease;
  }
  .modal-title{
    font-family:var(--font-display);
    font-size:18px;
    font-weight:600;
    margin:0 0 18px;
    color:var(--accent);
  }
  .form-group{
    display:flex;
    flex-direction:column;
    gap:6px;
    margin-bottom:14px;
  }
  .form-group label{
    font-size:11px;
    font-weight:600;
    color:var(--muted);
    text-transform:uppercase;
  }
  .form-input{
    background:var(--bg);
    border:1px solid var(--border);
    border-radius:var(--radius-sm);
    padding:10px 12px;
    color:var(--text);
    font-size:13px;
    outline:none;
  }
  .form-input:focus{
    border-color:var(--accent);
  }
  .form-checkbox{
    display:flex;
    align-items:center;
    gap:8px;
    cursor:pointer;
    font-size:13px;
    color:var(--text);
  }
  .modal-buttons{
    display:flex;
    justify-content:flex-end;
    gap:10px;
    margin-top:20px;
  }
  .btn{
    padding:8px 16px;
    border-radius:var(--radius-sm);
    font-size:13px;
    font-weight:600;
    cursor:pointer;
    border:none;
  }
  .btn-cancel{
    background:var(--border-soft);
    color:var(--muted);
  }
  .btn-submit{
    background:linear-gradient(140deg,var(--accent),var(--accent-2));
    color:#12100a;
  }

  @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  @keyframes blink{50%{opacity:0}}
  @keyframes bounce{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-5px);opacity:1}}
  ::-webkit-scrollbar{width:8px}
  ::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
  ::-webkit-scrollbar-track{background:transparent}

  /* Mascot Companion */
  .mascot-container {
    position: fixed;
    bottom: 95px;
    right: 340px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    z-index: 100;
    pointer-events: none;
  }
  .mascot-img {
    width: 90px;
    height: 90px;
    object-fit: cover;
    border-radius: 50%;
    border: 2px solid rgba(240,100,50,0.3);
    background: white;
    pointer-events: auto;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    filter: drop-shadow(0 0 12px rgba(240,100,50,0.4)) drop-shadow(0 6px 12px rgba(0,0,0,0.4));
  }
  .mascot-img:hover {
    transform: scale(1.08) translateY(-4px);
    border-color: rgba(240,100,50,0.7);
    filter: drop-shadow(0 0 20px rgba(240,100,50,0.7)) drop-shadow(0 8px 16px rgba(0,0,0,0.5));
  }
  .mascot-bubble {
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm) var(--radius-sm) 0 var(--radius-sm);
    padding: 10px 14px;
    font-size: 11.5px;
    color: var(--text);
    line-height: 1.45;
    max-width: 180px;
    box-shadow: var(--shadow);
    margin-bottom: 10px;
    opacity: 0;
    transform: translateY(12px);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    pointer-events: auto;
    position: relative;
  }
  .mascot-bubble::after {
    content: '';
    position: absolute;
    bottom: -6px;
    right: 15px;
    width: 10px;
    height: 10px;
    background: var(--panel-2);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    transform: rotate(45deg);
  }
  .mascot-bubble.show {
    opacity: 1;
    transform: translateY(0);
  }
</style>
</head>
<body>

<div class="app-layout">
  
  <!-- Left Sidebar: Project context -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <h3>Project Scope</h3>
    </div>
    
    <div class="sidebar-section">
      <div class="section-title">Active Project</div>
      <div class="input-group">
        <div class="input-label">Workspace path</div>
        <input type="text" class="sidebar-input" id="workspacePath" placeholder="C:\Users\you\your-project">
      </div>
      <button class="add-rule-trigger" onclick="saveActiveWorkspace()">Set active project</button>
      <div class="pill" id="workspaceStatusPill" style="margin-top:8px;">loading…</div>
    </div>
    
    <div class="sidebar-section">
      <div class="section-title">Detected Stack</div>
      <div class="stack-pills" id="stackPills">
        <div class="pill">loading stack…</div>
      </div>
    </div>
    
    <div class="sidebar-section" id="notebookSection" style="display:none;">
      <div class="section-title">Jupyter Notebooks</div>
      <div id="notebookList"></div>
    </div>
    
    <div class="sidebar-section">
      <div class="section-title">Cursor Rules</div>
      <div id="rulesList">
        <div class="pill">loading rules…</div>
      </div>
      <button class="add-rule-trigger" onclick="openAddRuleModal()">+ Create Project Rule</button>
    </div>
  </aside>
  
  <!-- Center Area: Grounded Chat -->
  <main class="chat-container">
    <header>
      <div class="mark">C</div>
      <div class="titles">
        <h1>Cursor Co-pilot</h1>
        <p>Grounded in the official docs + your active codebase</p>
      </div>
      <div class="status" id="status" title="Backend status">
        <span class="dot" id="dot"></span><span id="statusText">connecting…</span>
      </div>
    </header>
    
    <main id="main">
      <div class="wrap" id="wrap">
        <div class="hero" id="hero">
          <div class="big">C</div>
          <h2>Cursor Co-pilot</h2>
          <p id="heroSubtitle">Brainstorming for your active codebase…</p>
          <button class="add-rule-trigger" style="margin:12px auto 0;display:block;" onclick="loadBrainstorm()">Refresh ideas</button>
          <div class="chips" id="chips"></div>
        </div>
      </div>
    </main>
    
    <div class="composer-wrap">
      <div class="composer">
        <textarea id="input" rows="1" placeholder="Ask anything about Cursor or project setup… (Enter to send, Shift+Enter for newline)"></textarea>
        <button class="send" id="send" title="Send">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
        </button>
      </div>
      <div class="hint">Ask about your codebase strategy, Cursor setup, <b>generate a rule for …</b>, or <b>install postgres mcp</b>.</div>
    </div>
  </main>
  
  <!-- Right Sidebar: Personal vault & MCP catalog -->
  <aside class="sidebar right-sidebar">
    <div class="sidebar-header">
      <h3>Active Integrations</h3>
    </div>
    
    <div class="sidebar-section">
      <div class="section-title">Notes Vault</div>
      <div class="vault-config">
        <div class="input-group">
          <div class="input-label">Vault mode</div>
          <select class="sidebar-input" id="vaultMode" onchange="saveVaultConfig()">
            <option value="project">Project vault (docs/vault)</option>
            <option value="existing">Existing Obsidian vault</option>
          </select>
        </div>
        <div class="input-group">
          <div class="input-label">Vault path (existing mode)</div>
          <input type="text" class="sidebar-input" id="vaultPath" placeholder="C:\Users\you\Obsidian\MyProject" onchange="saveVaultConfig()">
        </div>
        <button class="add-rule-trigger" onclick="scaffoldVault()">Create project vault</button>
        <div class="input-group">
          <div class="input-label">Search Vault</div>
          <input type="text" class="sidebar-input" id="vaultSearchQuery" placeholder="Search notes..." onkeydown="handleVaultSearch(event)">
        </div>
      </div>
      <div class="search-results" id="vaultSearchResults"></div>
    </div>
    
    <div class="sidebar-section">
      <div class="section-title">MCP Marketplace & Recommendations</div>
      <div class="input-group">
        <div class="input-label">Search Server Catalog</div>
        <input type="text" class="sidebar-input" id="mcpSearchQuery" placeholder="Search servers (e.g. postgres)..." oninput="filterMcpServers()">
      </div>
      <div id="mcpList">
        <div class="pill">loading catalog…</div>
      </div>
    </div>
  </aside>
  
</div>

<!-- Modal: Create project rule -->
<div class="modal-overlay" id="ruleModal">
  <div class="modal">
    <h3 class="modal-title">Create Project Rule</h3>
    <div class="form-group">
      <label>Rule Filename</label>
      <input type="text" class="form-input" id="ruleName" placeholder="e.g. fast-api-standards">
    </div>
    <div class="form-group">
      <label>Rule Intent / Behavior Description</label>
      <input type="text" class="form-input" id="ruleIntent" placeholder="e.g. Always use typing, write tests in tests/">
    </div>
    <div class="form-group">
      <label>File Scope (Globs, e.g. **/*.py)</label>
      <input type="text" class="form-input" id="ruleGlobs" placeholder="e.g. **/*.py">
    </div>
    <div class="form-group">
      <label class="form-checkbox">
        <input type="checkbox" id="ruleAlwaysApply">
        Always apply this rule in context
      </label>
    </div>
    <div class="modal-buttons">
      <button class="btn btn-cancel" onclick="closeAddRuleModal()">Cancel</button>
      <button class="btn btn-submit" id="submitRuleBtn" onclick="submitCreateRule()">Create Rule</button>
    </div>
  </div>
</div>

<!-- Mascot Companion -->
<div class="mascot-container" id="mascotContainer">
  <div class="mascot-bubble" id="mascotBubble">Hi! I'm your Cursor Co-pilot. Ask me anything about Cursor docs or stack setups!</div>
  <img src="/static/mascot.png" class="mascot-img" id="mascotImg" alt="Mascot" onclick="speak('Need help? Ask me any question, search your vault, or configure MCP servers!')">
</div>

<script>
const $ = s => document.querySelector(s);
const main = $('#main'), wrap = $('#wrap'), hero = $('#hero');
const input = $('#input'), send = $('#send');
let history = [], streaming = false, controller = null;
let projectData = { profile: {}, mcp_config: {}, rules: [], workspace: {} };
let workspaceConfig = {};

const mascotBubble = $('#mascotBubble');
const mascotImg = $('#mascotImg');

function speak(text, duration = 4000) {
  mascotBubble.textContent = text;
  mascotBubble.classList.add('show');
  mascotImg.style.transform = 'scale(1.08) translateY(-4px) rotate(-3deg)';
  setTimeout(() => {
    mascotImg.style.transform = '';
  }, 350);
  
  if (window.mascotTimeout) clearTimeout(window.mascotTimeout);
  window.mascotTimeout = setTimeout(() => {
    mascotBubble.classList.remove('show');
  }, duration);
}

// Speak greeting on startup
setTimeout(() => {
  speak("Hi! I'm your Cursor Co-pilot. Ask me anything about Cursor docs, vault search, or project setups!", 6000);
}, 1200);

// Hover listeners for mascot interactivity
document.addEventListener('mouseover', e => {
  const target = e.target;
  
  if (target.classList.contains('pill')) {
    if (target.classList.contains('highlight')) {
      speak(`Languages detected: ${target.textContent}. Let's write some clean code!`, 3000);
    } else {
      speak(`Frameworks detected: ${target.textContent}. Excellent choice!`, 3000);
    }
  }
  else if (target.closest('.notebook-card')) {
    const name = target.closest('.notebook-card').querySelector('.notebook-name').textContent;
    speak(`Analyzing Jupyter notebook: ${name}. I will track imports, variables, and execution health!`, 3500);
  }
  else if (target.classList.contains('add-rule-trigger')) {
    speak("Let's create a custom project rule (.mdc) to automate coding standards!", 3000);
  }
  else if (target.classList.contains('install-btn')) {
    speak("Click to install this recommended MCP server to your mcp.json config!", 3000);
  }
  else if (target.id === 'vaultSearchQuery') {
    speak("Search your local Obsidian vault to ground my answers in your research!", 3500);
  }
  else if (target.id === 'mcpSearchQuery') {
    speak("Search the official catalog for any MCP server you need!", 3000);
  }
});


// Dynamic brainstorm chips
const chips = $('#chips');

function renderBrainstormChips(suggestions) {
  chips.innerHTML = '';
  if (!suggestions.length) {
    chips.innerHTML = '<div class="pill" style="grid-column:1/-1;">No ideas yet — set your active project first.</div>';
    return;
  }
  suggestions.forEach(s => {
    const b = document.createElement('button');
    b.className = 'chip';
    b.innerHTML = (s.title || 'Idea') + '<span>' + (s.tag || 'Brainstorm') + '</span>';
    b.onclick = () => { input.value = s.prompt || s.title; ask(); };
    chips.appendChild(b);
  });
}

async function pollBrainstormJob(jobId) {
  for (let i = 0; i < 90; i++) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const r = await fetch('/api/brainstorm/job/' + jobId);
      if (!r.ok) return;
      const data = await r.json();
      if (data.status === 'complete' && (data.suggestions || []).length) {
        renderBrainstormChips(data.suggestions);
        const subtitle = $('#heroSubtitle');
        if (subtitle) subtitle.textContent = (subtitle.textContent || '') + ' · AI-enhanced';
        return;
      }
      if (data.status === 'error') return;
    } catch (e) { return; }
  }
}

async function loadBrainstorm() {
  chips.innerHTML = '<div class="pill" style="grid-column:1/-1;text-align:center;">loading ideas…</div>';
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  try {
    const r = await fetch('/api/brainstorm?limit=6&async=1', { signal: controller.signal });
    const data = await r.json();
    const subtitle = $('#heroSubtitle');
    if (subtitle) {
      subtitle.textContent = data.context_summary
        ? `Brainstorming for ${data.context_summary}`
        : 'Brainstorming for your active codebase';
    }
    renderBrainstormChips(data.suggestions || []);
    if (data.enhancement_job_id) {
      pollBrainstormJob(data.enhancement_job_id);
    }
  } catch (e) {
    chips.innerHTML = '<div class="pill" style="grid-column:1/-1;">Could not load brainstorm ideas.</div>';
  } finally {
    clearTimeout(timeoutId);
  }
}

loadBrainstorm();

async function loadWorkspaceConfig() {
  try {
    const r = await fetch('/api/workspace/config');
    const data = await r.json();
    workspaceConfig = data.config || {};
    if (data.configured && data.workspace) $('#workspacePath').value = data.workspace;
    const vault = workspaceConfig.vault || {};
    if ($('#vaultMode')) $('#vaultMode').value = vault.mode || 'project';
    if (vault.path) $('#vaultPath').value = vault.path;
    else if (localStorage.getItem('obsidian_vault_path')) {
      $('#vaultPath').value = localStorage.getItem('obsidian_vault_path');
      await saveVaultConfig();
    }
  } catch (e) { console.error('workspace config load failed', e); }
}

async function saveActiveWorkspace() {
  const path = $('#workspacePath').value.trim();
  if (!path) return;
  await fetch('/api/workspace/active', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  await poll(true);
  await loadBrainstorm();
}

async function saveVaultConfig() {
  const mode = $('#vaultMode').value;
  const path = $('#vaultPath').value.trim();
  workspaceConfig.vault = workspaceConfig.vault || {};
  workspaceConfig.vault.mode = mode;
  workspaceConfig.vault.path = path;
  await fetch('/api/workspace/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config: workspaceConfig })
  });
  localStorage.setItem('obsidian_vault_path', path);
}

async function scaffoldVault() {
  await fetch('/api/vault/scaffold', { method: 'POST' });
  await poll(true);
  speak('Project vault scaffolded under docs/vault.', 3000);
}

loadWorkspaceConfig();

// Health + Project Status polling
async function poll(forceRefresh=false){
  const dot = $('#dot'), txt = $('#statusText');
  try{
    const r = await fetch('/api/health'); const h = await r.json();
    const llm = h.llm || {};
    const active = llm.active || 'unknown';
    const chunks = h.chunks != null ? h.chunks + ' docs chunks' : '';
    if (active === 'ollama') {
      if (!h.ollama) { dot.className='dot bad'; txt.textContent='Ollama offline'; }
      else if (!h.model_available) { dot.className='dot bad'; txt.textContent=(llm.ollama_model || h.model)+' not pulled'; }
      else {
        const chat = h.chat_model && h.chat_model !== (llm.ollama_model || h.model)
          ? ' · chat ' + h.chat_model : '';
        dot.className='dot ok';
        txt.textContent='ollama · '+(llm.ollama_model || h.model)+chat+(chunks ? ' · '+chunks : '');
      }
    } else if (active === 'gemini') {
      if (!llm.gemini_key) { dot.className='dot bad'; txt.textContent='gemini · no API key'; }
      else { dot.className='dot ok'; txt.textContent='gemini · '+llm.gemini_model+(chunks ? ' · '+chunks : ''); }
    } else if (active === 'anthropic') {
      if (!llm.anthropic_key) { dot.className='dot bad'; txt.textContent='anthropic · no API key'; }
      else { dot.className='dot ok'; txt.textContent='anthropic · '+llm.anthropic_model+(chunks ? ' · '+chunks : ''); }
    } else {
      dot.className='dot bad'; txt.textContent='No LLM backend available';
    }
  }catch(e){ dot.className='dot bad'; txt.textContent='server error'; }
  
  // Also poll project status
  try{
    const pr = await fetch('/api/project/status' + (forceRefresh ? '?refresh=1' : ''));
    const pData = await pr.json();
    projectData = pData;
    renderProjectDashboard();
  }catch(e){ console.error('Status loading failed', e); }
}

// Render Dashboard
function renderProjectDashboard() {
  const ws = projectData.workspace || {};
  const wsPill = $('#workspaceStatusPill');
  if (wsPill) {
    wsPill.textContent = ws.configured
      ? (ws.workspace || 'Active project set')
      : 'Using co-pilot install dir — set active project';
  }
  if (ws.configured && ws.workspace && !$('#workspacePath').value) {
    $('#workspacePath').value = ws.workspace;
  }

  // 1. Render stack profile
  const pills = $('#stackPills');
  pills.innerHTML = '';
  const prof = projectData.profile || {};
  const langs = prof.languages || [];
  const fws = prof.frameworks || [];
  const sdks = prof.notable_sdks || [];
  
  if(!langs.length && !fws.length && !sdks.length) {
    pills.innerHTML = '<div class="pill">no stack detected</div>';
  } else {
    langs.forEach(l => pills.innerHTML += `<div class="pill highlight">${l}</div>`);
    fws.forEach(f => pills.innerHTML += `<div class="pill">${f}</div>`);
    sdks.forEach(s => pills.innerHTML += `<div class="pill">${s}</div>`);
  }
  
  // 2. Render Notebooks
  const nbSection = $('#notebookSection');
  const nbList = $('#notebookList');
  const notebooks = prof.notebooks || [];
  if(notebooks.length > 0) {
    nbSection.style.display = 'block';
    nbList.innerHTML = '';
    notebooks.forEach(nb => {
      const health = (nb.execution_health === 'ordered' || nb.execution_health === 'out_of_order')
        ? nb.execution_health : 'unknown';
      const healthLabel = health.replace('_', ' ');
      let importsList = (nb.imports || []).map(i => `<li>${i}</li>`).join('');
      let varsList = (nb.variables || []).map(v => `<li>${v}</li>`).join('');
      let headersList = (nb.headers || []).map(h => `<li>${h}</li>`).join('');
      
      nbList.innerHTML += `
        <div class="notebook-card">
          <div class="notebook-name" title="${nb.filename}">${nb.filename}</div>
          <div class="notebook-meta">
            <span>Cells: ${nb.code_cells} code, ${nb.markdown_cells} md</span>
            <span style="display:flex;align-items:center;">
              <span class="health-dot ${health}"></span>
              ${healthLabel}
            </span>
          </div>
          <div class="notebook-details">
            <details>
              <summary>Imports & Variables</summary>
              <div style="font-size:10px; margin-top:4px;">
                ${importsList ? `<b>Imports:</b><ul>${importsList}</ul>` : ''}
                ${varsList ? `<b>Variables:</b><ul>${varsList}</ul>` : ''}
                ${headersList ? `<b>Structure:</b><ul>${headersList}</ul>` : ''}
              </div>
            </details>
          </div>
        </div>
      `;
    });
  } else {
    nbSection.style.display = 'none';
  }
  
  // 3. Render rules
  const rList = $('#rulesList');
  rList.innerHTML = '';
  const rules = projectData.rules || [];
  if(rules.length === 0) {
    rList.innerHTML = '<div class="pill" style="width:100%;text-align:center;">no rules active</div>';
  } else {
    rules.forEach(r => {
      rList.innerHTML += `
        <div class="rule-item">
          <div class="rule-info">
            <div class="rule-title" title="${r.filename}">${r.filename}</div>
            <div class="rule-desc">${r.description}</div>
          </div>
          <button class="action-btn" title="Delete rule" onclick="deleteRule('${r.filename}')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
          </button>
        </div>
      `;
    });
  }

  // 4. Render MCP Catalog Recommendations
  filterMcpServers();
}

// Filter and render MCP catalog
async function filterMcpServers() {
  const query = $('#mcpSearchQuery').value.trim().toLowerCase();
  const mList = $('#mcpList');
  mList.innerHTML = '';
  
  // Installed servers list from mcp.json
  const installed = Object.keys((projectData.mcp_config || {}).mcpServers || {});
  
  // Pull recommendations from search
  try {
    const goals = query || (projectData.profile.languages || []).join(" ") || "ml data analysis";
    const res = await fetch(`/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: `suggest mcp servers for ${goals}`, history: [] })
    });
    
  } catch(e) {}
  
  const prof = projectData.profile || {};
  const queryTerms = query || (prof.languages || []).join(" ") || "python ml data-analysis";
  
  mList.innerHTML = '';
  const candidates = [
    { name: "postgres", desc: "Allows querying and inspection of PostgreSQL databases.", tags: "postgres database sql" },
    { name: "sqlite", desc: "Query, schema analysis, and table inspection of local SQLite databases.", tags: "sqlite database local" },
    { name: "github", desc: "Interact with GitHub repositories, pull requests, issues, and files.", tags: "github devops code" },
    { name: "notion", desc: "Retrieve, edit, and search pages and databases in your Notion workspace.", tags: "notion productivity notes" },
    { name: "obsidian", desc: "Read and search notes from your Obsidian vault.", tags: "obsidian markdown documentation" },
    { name: "gdrive", desc: "Read, write, and search files in Google Drive.", tags: "gdrive files google" }
  ];
  
  const filtered = candidates.filter(c => {
    if(!query) return true;
    return c.name.toLowerCase().includes(query) || c.desc.toLowerCase().includes(query) || c.tags.toLowerCase().includes(query);
  });
  
  filtered.forEach(m => {
    const isInst = installed.includes(m.name);
    mList.innerHTML += `
      <div class="mcp-item">
        <div class="mcp-info">
          <div class="mcp-name">
            ${m.name}
            ${isInst ? '<span style="font-size:9px;background:rgba(92,204,132,.1);color:var(--ok);padding:1px 4px;border-radius:3px;">Installed</span>' : ''}
          </div>
          <div class="mcp-desc">${m.desc}</div>
          <div class="mcp-tag">${m.tags}</div>
        </div>
        ${isInst ? '' : `<button class="install-btn" onclick="installMcp('${m.name}')">Install</button>`}
      </div>
    `;
  });
}

// Vault search handler
async function handleVaultSearch(event) {
  if(event.key === 'Enter') {
    const q = $('#vaultSearchQuery').value.trim();
    const vPath = $('#vaultPath').value.trim();
    const resultsPanel = $('#vaultSearchResults');
    if(!q) return;
    resultsPanel.innerHTML = '<div class="pill">searching vault…</div>';
    
    try {
      const r = await fetch(`/api/vault/search?query=${encodeURIComponent(q)}&vault_path=${encodeURIComponent(vPath)}`);
      const results = await r.json();
      resultsPanel.innerHTML = '';
      if(results.length === 0) {
        resultsPanel.innerHTML = '<div class="pill" style="width:100%;text-align:center;">no matches in vault</div>';
      } else {
        results.forEach(res => {
          // Double backslashes and escape quotes to avoid syntax breaks in the inline JS onclick handler
          const escapedText = res.text.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/'/g, "\\'").replace(/\n/g, '\\n').replace(/\r/g, '\\r');
          const escapedTitle = res.title.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/'/g, "\\'");
          resultsPanel.innerHTML += `
            <div class="search-result-item" onclick="insertNoteContext('${escapedTitle}', '${escapedText}')">
              <div class="search-result-title" title="${res.url}">${res.title}</div>
              <div class="search-result-text">${res.text}</div>
            </div>
          `;
        });
      }
    } catch(e) {
      resultsPanel.innerHTML = `<div class="pill" style="color:var(--bad)">error searching: ${e.message}</div>`;
    }
  }
}

function insertNoteContext(title, text) {
  input.value = "Note Context from \"" + title + "\":\n---\n" + text + "\n---\n\n[My Question]: ";
  input.focus();
  input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,140)+'px';
}

// Rules operations
function openAddRuleModal() {
  $('#ruleModal').style.display = 'grid';
  $('#ruleName').focus();
}
function closeAddRuleModal() {
  $('#ruleModal').style.display = 'none';
}
async function submitCreateRule() {
  const name = $('#ruleName').value.trim();
  const intent = $('#ruleIntent').value.trim();
  const globs = $('#ruleGlobs').value.trim();
  const alwaysApply = $('#ruleAlwaysApply').checked;
  const btn = $('#submitRuleBtn');
  
  if(!name || !intent) return alert('Name and Intent are required');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  
  try {
    const r = await fetch('/api/rules/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, intent, globs, always_apply: alwaysApply })
    });
    const res = await r.json();
    if(res.success) {
      closeAddRuleModal();
      $('#ruleName').value = '';
      $('#ruleIntent').value = '';
      $('#ruleGlobs').value = '';
      $('#ruleAlwaysApply').checked = false;
      poll(true); // reload
    } else {
      alert('Error creating rule: ' + res.error);
    }
  } catch(e) { alert('Error: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = 'Create Rule'; }
}

async function deleteRule(filename) {
  if(!confirm(`Delete rule ${filename}?`)) return;
  try {
    const r = await fetch('/api/rules/delete', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    });
    const res = await r.json();
    if(res.success) poll(true);
    else alert('Failed to delete: ' + res.error);
  } catch(e) { alert('Error: ' + e.message); }
}

// MCP Install
async function installMcp(serverName) {
  try {
    const r = await fetch('/api/mcp/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: serverName, project_or_global: 'project' })
    });
    const res = await r.json();
    if(res.success) {
      alert(`Successfully installed ${serverName} to project mcp.json!`);
      poll(true);
    } else {
      alert('Error: ' + res.error);
    }
  } catch(e) { alert('Install failed: ' + e.message); }
}

poll(); setInterval(poll, 8000);

// Textarea autogrow
input.addEventListener('input', ()=>{ input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,140)+'px'; });
input.addEventListener('keydown', e=>{
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); ask(); }
});
send.onclick = ()=>{ if(streaming){ stop(); } else { ask(); } };

function addMsg(role){
  if(hero) hero.remove();
  const m = document.createElement('div');
  m.className = 'msg '+(role==='user'?'user':'bot');
  m.innerHTML = `<div class="avatar">${role==='user'?'You':'C'}</div>
    <div class="bubble"><div class="who">${role==='user'?'You':'Assistant'}</div>
    <div class="content"></div></div>`;
  wrap.appendChild(m);
  scroll();
  return m.querySelector('.content');
}
function scroll(){ main.scrollTop = main.scrollHeight; }
function md(t){ return DOMPurify.sanitize(marked.parse(t)); }

function setSending(on){
  streaming = on;
  send.classList.toggle('stop', on);
  send.innerHTML = on
    ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>'
    : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>';
}
function stop(){ if(controller) controller.abort(); }

function srcHTML(sources){
  if(!sources || !sources.length) return '';
  const items = sources.map(s=>{
    const head = s.heading ? (s.title+' — '+s.heading) : s.title;
    return `<a class="src" href="${s.url}" target="_blank" rel="noopener">
      <span class="num">${s.n}</span>
      <span class="meta"><div class="t">${head}</div><div class="u">${s.url}</div></span></a>`;
  }).join('');
  return `<details class="sources"><summary>📚 <b>${sources.length} sources</b> from Cursor docs</summary>
    <div class="src-list">${items}</div></details>`;
}

function advisorFooterHTML(){
  return `<details class="sources" open><summary>📁 <b>Project context</b> (README, scan, vault, rules)</summary>
    <div class="src-list"><div class="src"><span class="meta"><div class="t">Answer grounded in your active workspace</div></div></div></details>`;
}

async function ask(){
  const q = input.value.trim();
  if(!q || streaming) return;
  input.value=''; input.style.height='auto';
  addMsg('user').textContent = q;
  history.push({role:'user', content:q});

  const content = addMsg('bot');
  content.innerHTML = '<div class="think"><i></i><i></i><i></i></div>';
  setSending(true);
  speak("Working on that...", 8000);

  let answer = '', sources = [], started = false, actionDone = false, advisorMode = false;
  controller = new AbortController();
  try{
    const resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:q, history: history.slice(0,-1)}),
      signal: controller.signal,
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf='';
    while(true){
      const {value, done} = await reader.read();
      if(done) break;
      buf += dec.decode(value, {stream:true});
      const events = buf.split('\n\n'); buf = events.pop();
      for(const ev of events){
        const tMatch = ev.match(/^event: (.+)$/m);
        const dMatch = ev.match(/^data: ([\s\S]*)$/m);
        if(!tMatch || !dMatch) continue;
        const type = tMatch[1].trim();
        let payload; try{ payload = JSON.parse(dMatch[1]); }catch(e){ payload = dMatch[1]; }
        if(type==='sources'){ sources = payload; }
        else if(type==='mode'){
          if(payload && payload.mode === 'advisor') advisorMode = true;
        }
        else if(type==='action'){
          if(payload && payload.path) {
            actionDone = true;
            poll(true);
          }
        }
        else if(type==='token'){
          if(!started){ content.innerHTML=''; started=true; }
          answer += payload;
          content.innerHTML = md(answer);
          content.classList.add('caret');
          scroll();
        }
        else if(type==='error'){
          content.classList.remove('caret');
          content.innerHTML = md('⚠️ '+payload);
          speak("Oops! I hit an error during generation.", 5000);
        }
        else if(type==='done'){
          content.classList.remove('caret');
          if(answer) {
            const footer = actionDone ? '' : (advisorMode ? advisorFooterHTML() : srcHTML(sources));
            content.innerHTML = md(answer) + footer;
          }
          history.push({role:'assistant', content: answer});
          const msg = actionDone ? "Done — file written to your project."
            : advisorMode ? "Here's a plan based on your project context."
            : "Here is your answer! Check the citation links below.";
          speak(msg, 4000);
        }
      }
    }
  }catch(e){
    content.classList.remove('caret');
    if(e.name==='AbortError'){ 
      content.innerHTML = md(answer + (answer?'\n\n':'') + '_(stopped)_') + srcHTML(sources);
      speak("Chat request stopped.", 3000);
    }
    else { 
      content.innerHTML = md('⚠️ Connection error: '+e.message);
      speak("Connection failed. Check if server is running.", 4000);
    }
  }finally{
    content.classList.remove('caret');
    setSending(false); controller=null; scroll();
  }
}
input.focus();
</script>
</body>
</html>
'''
