/** Homepage protocol interactions — CLI sandbox, anatomy explorer, install copy */
(function () {
  var anatomyKeyValues = {
    origin: {
      title: "Origin Context Mapping",
      desc: "Specifies which AI application, autonomous development agent, or LLM generated the underlying adjustments. This allows pre-commit filters to match changes precisely.",
    },
    target: {
      title: "Affected Targets Matrix",
      desc: "Defines the exact list of targets, files, modules, or directories that were modified by the AI generation cycle.",
    },
    hash: {
      title: "Cryptographic Delta Hash",
      desc: "A secure SHA-256 calculation tracking precisely which changes were generated. Any manual edit to the block post-generation will break the signature match instantly.",
    },
    key: {
      title: "Local Signing Key Credentials",
      desc: "The public key representing either your secure local Ed25519 identity, or a designated hardware secure element module (SE050 profile).",
    },
    sig: {
      title: "Ed25519 Cryptographic Envelope",
      desc: "The final tamper-proof mathematical assertion confirming origin legitimacy. Fast, zero-overhead execution perfect for pre-commit git checks.",
    },
  }

  var cliOutputTemplates = {
    init:
      '<div class="cli-muted">// Initialize open Matrix Scroll environment</div>' +
      '<div class="cli-cmd">$ matrixscroll init</div>' +
      '<div class="cli-out">Initializing workspace config template...</div>' +
      '<div class="cli-out">Generating local Ed25519 keypair for AI provenance...</div>' +
      '<div class="cli-ok">✓ Created public key: ed25519_pub_7c8d9e2f...</div>' +
      '<div class="cli-out">Injecting git pre-commit hooks...</div>' +
      '<div class="cli-ok">✓ Matrix Scroll successfully activated on repository.</div>',
    sign:
      '<div class="cli-muted">// Sign AI authored block manually</div>' +
      '<div class="cli-cmd">$ matrixscroll sign main.py --agent copilot_v1</div>' +
      '<div class="cli-out">Parsing main.py delta modifications...</div>' +
      '<div class="cli-out">Signature metadata prepared: lines 12-18</div>' +
      '<div class="cli-out">Signing with ed25519_pub_7c8d9e2f...</div>' +
      '<div class="cli-ok">✓ Appended manifest signature envelope to main.py</div>' +
      '<div class="cli-muted">Signature: h8S9d1Ka...9sLk17MvQp02aW</div>',
    "verify-pass":
      '<div class="cli-muted">// Verify clean, unmodified file signatures</div>' +
      '<div class="cli-cmd">$ matrixscroll verify main.py</div>' +
      '<div class="cli-out">Checking manifest records... [1 signature block found]</div>' +
      '<div class="cli-out">Matching SHA256 delta hashes against signature...</div>' +
      '<div class="cli-ok">✓ VERIFICATION APPROVED: Signature matches original code structure.</div>',
    "verify-fail":
      '<div class="cli-muted">// Verify altered signature records</div>' +
      '<div class="cli-cmd">$ matrixscroll verify main.py</div>' +
      '<div class="cli-out">Checking manifest records... [1 signature block found]</div>' +
      '<div class="cli-warn">WARNING: Hash mismatch detected on main.py line 14</div>' +
      '<div class="cli-warn">Line was modified after signature generation!</div>' +
      '<div class="cli-fail">✗ VERIFICATION REJECTED: Code is untrusted or modified.</div>',
  }

  function copyInstallCmd() {
    var cmd = "pip install matrixscroll"
    navigator.clipboard.writeText(cmd).catch(function () {
      var temp = document.createElement("textarea")
      temp.value = cmd
      document.body.appendChild(temp)
      temp.select()
      document.execCommand("copy")
      document.body.removeChild(temp)
    })

    var icon = document.getElementById("copy-icon")
    if (icon) {
      icon.textContent = "✓"
      icon.classList.add("is-copied")
      setTimeout(function () {
        icon.textContent = "⎘"
        icon.classList.remove("is-copied")
      }, 2500)
    }

    var existing = document.getElementById("copy-toast")
    if (existing) existing.remove()
    var notify = document.createElement("div")
    notify.id = "copy-toast"
    notify.className = "copy-toast"
    notify.textContent = "✓ Install command copied to clipboard"
    document.body.appendChild(notify)
    setTimeout(function () {
      notify.remove()
    }, 2500)
  }

  function selectAnatomyKey(keyId) {
    var keys = ["origin", "target", "hash", "key", "sig"]
    keys.forEach(function (k) {
      var el = document.getElementById("ana-" + k)
      if (!el) return
      el.classList.remove("is-active")
    })
    var active = document.getElementById("ana-" + keyId)
    if (active) active.classList.add("is-active")

    var map = anatomyKeyValues[keyId]
    if (!map) return
    var title = document.getElementById("anatomy-title")
    var desc = document.getElementById("anatomy-desc")
    if (title) title.textContent = map.title
    if (desc) desc.textContent = map.desc
  }

  function runCliCommand(cmdKey) {
    var btnMap = { init: "init", sign: "sign", "verify-pass": "ver-pass", "verify-fail": "ver-fail" }
    Object.keys(btnMap).forEach(function (k) {
      var btn = document.getElementById("cli-btn-" + btnMap[k])
      if (btn) btn.classList.remove("is-active")
    })
    var activeBtn = document.getElementById("cli-btn-" + btnMap[cmdKey])
    if (activeBtn) activeBtn.classList.add("is-active")

    var screen = document.getElementById("terminal-screen")
    if (!screen) return
    screen.innerHTML = '<div class="cli-muted">Processing command...</div>'

    setTimeout(function () {
      screen.innerHTML =
        (cliOutputTemplates[cmdKey] || "") +
        '<div class="cli-cmd">$ <span class="terminal-cursor" aria-hidden="true">|</span></div>'
    }, 400)
  }

  function init() {
    var copyBtn = document.getElementById("copy-install-btn")
    if (copyBtn) copyBtn.addEventListener("click", copyInstallCmd)

    document.querySelectorAll("[data-anatomy-key]").forEach(function (el) {
      el.addEventListener("click", function () {
        selectAnatomyKey(el.getAttribute("data-anatomy-key"))
      })
    })

    document.querySelectorAll("[data-cli-cmd]").forEach(function (el) {
      el.addEventListener("click", function () {
        runCliCommand(el.getAttribute("data-cli-cmd"))
      })
    })

    selectAnatomyKey("origin")
  }

  window.copyInstallCmd = copyInstallCmd
  window.selectAnatomyKey = selectAnatomyKey
  window.runCliCommand = runCliCommand

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init)
  } else {
    init()
  }
})()
