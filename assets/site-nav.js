/**
 * Unified cross-site navigation for matrixscroll.com
 * - Ecosystem bar: Matrix Scroll ↔ AP2 Hardware ↔ SSX360 control plane
 * - Consistent primary nav on every page (fixes drift between HTML files)
 * - Mobile menu for crowded nav
 */
(function () {
  var PRIMARY = [
    { href: "/docs/", label: "Docs", match: ["/docs"] },
    { href: "/mcp/", label: "MCP", match: ["/mcp"] },
    { href: "/verify/", label: "Verifier", match: ["/verify"] },
    { href: "/hardware/", label: "Hardware", match: ["/hardware"] },
    { href: "/ap2/", label: "AP2", match: ["/ap2"] },
    { href: "/ecosystem/", label: "Ecosystem", match: ["/ecosystem"] },
  ]

  var MORE = [
    { href: "/spec/", label: "Spec", match: ["/spec"] },
    { href: "/compare/", label: "Compare", match: ["/compare"] },
    { href: "/docs/Whitepaper.html", label: "Whitepaper", match: ["/docs/Whitepaper"] },
    { href: "/roadmap/", label: "Roadmap", match: ["/roadmap"] },
    { href: "/authority/", label: "Authority", match: ["/authority"] },
  ]

  var ECOSYSTEM = [
    {
      href: "https://matrixscroll.com/",
      label: "Matrix Scroll",
      detail: "Open protocol",
      external: false,
      active: function (path) {
        return !path.startsWith("/hardware") && !path.startsWith("/ap2")
      },
    },
    {
      href: "https://matrixscroll.com/hardware/",
      label: "AP2 Vault Card",
      detail: "Hardware wedge",
      external: false,
      active: function (path) {
        return path.startsWith("/hardware") || path.startsWith("/ap2")
      },
    },
    {
      href: "https://ssx360.com/",
      label: "SSX360",
      detail: "Control plane",
      external: true,
      active: function () {
        return false
      },
    },
  ]

  function normalizePath() {
    var path = window.location.pathname || "/"
    if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1)
    return path
  }

  function itemActive(item, path) {
    return item.match.some(function (prefix) {
      return path === prefix || path.indexOf(prefix + "/") === 0
    })
  }

  function linkHtml(item, path) {
    var active = itemActive(item, path) ? ' aria-current="page"' : ""
    return '<a href="' + item.href + '"' + active + ">" + item.label + "</a>"
  }

  function buildEcosystemBar(path) {
    var parts = ECOSYSTEM.map(function (site) {
      var active = site.active(path)
      var cls = "ecosystem-pill" + (active ? " is-active" : "") + (site.external ? " is-external" : "")
      var ext = site.external ? ' target="_blank" rel="noopener noreferrer"' : ""
      var arrow = site.external ? '<span class="ecosystem-arrow" aria-hidden="true">↗</span>' : ""
      return (
        '<a class="' +
        cls +
        '" href="' +
        site.href +
        '"' +
        ext +
        '><span class="ecosystem-pill-label">' +
        site.label +
        '</span><span class="ecosystem-pill-detail">' +
        site.detail +
        "</span>" +
        arrow +
        "</a>"
      )
    })
    return (
      '<div class="ecosystem-bar" role="navigation" aria-label="SSX360 product ecosystem">' +
      '<div class="ecosystem-bar-inner">' +
      parts.join('<span class="ecosystem-sep" aria-hidden="true">→</span>') +
      "</div></div>"
    )
  }

  function buildNav(path) {
    var primary = PRIMARY.map(function (item) {
      return linkHtml(item, path)
    }).join("")

    var moreItems = MORE.map(function (item) {
      return linkHtml(item, path)
    }).join("")

    var moreActive = MORE.some(function (item) {
      return itemActive(item, path)
    })

    return (
      '<div class="nav-links" id="site-nav-links">' +
      primary +
      '<details class="nav-more"' +
      (moreActive ? " open" : "") +
      ">" +
      '<summary>More</summary>' +
      '<div class="nav-more-panel">' +
      moreItems +
      '<a class="nav-external" href="https://ssx360.com/" target="_blank" rel="noopener noreferrer">SSX360 Control Plane <span aria-hidden="true">↗</span></a>' +
      "</div></details>" +
      '<a class="nav-external nav-external-desktop" href="https://ssx360.com/" target="_blank" rel="noopener noreferrer">SSX360 <span aria-hidden="true">↗</span></a>' +
      "</div>"
    )
  }

  function injectMobileToggle(nav) {
    if (nav.querySelector(".nav-toggle")) return
    var btn = document.createElement("button")
    btn.type = "button"
    btn.className = "nav-toggle"
    btn.setAttribute("aria-expanded", "false")
    btn.setAttribute("aria-controls", "site-nav-links")
    btn.setAttribute("aria-label", "Open menu")
    btn.innerHTML = '<span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span>'
    btn.addEventListener("click", function () {
      var links = nav.querySelector(".nav-links")
      var open = links.classList.toggle("is-open")
      btn.setAttribute("aria-expanded", open ? "true" : "false")
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu")
    })
    nav.appendChild(btn)
  }

  function init() {
    var path = normalizePath()
    var header = document.querySelector(".site-header")

    if (header && !document.querySelector(".ecosystem-bar")) {
      header.insertAdjacentHTML("beforebegin", buildEcosystemBar(path))
    }

    var nav = document.querySelector(".site-header .nav")
    if (nav) {
      var existing = nav.querySelector(".nav-links")
      if (existing) {
        existing.outerHTML = buildNav(path)
      }
      injectMobileToggle(nav)
    }

    document.querySelectorAll(".ecosystem-bar a.is-external").forEach(function (anchor) {
      anchor.addEventListener("click", function () {
        /* allow default — user leaves protocol site for control plane */
      })
    })
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init)
  } else {
    init()
  }
})()
