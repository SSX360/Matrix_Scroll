#!/usr/bin/env node
/**
 * Syncs shared SEO head tags across static HTML pages on matrixscroll.com
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, "..")

const SITE = "https://matrixscroll.com"
const OG_IMAGE = `${SITE}/og-image.png`
const LOCALE = "en_US"

const pages = {
  "index.html": {
    path: "/",
    title: "Matrix Scroll — Prove who or what made the commit",
    description:
      "Signed commit provenance for humans, agents, and CI. Verify offline, in the browser, or in CI — then extend to AP2 Vault Card hardware approval.",
    ogTitle: "Matrix Scroll — Signed commit provenance for agents and CI",
  },
  "hardware/index.html": {
    path: "/hardware/",
    title: "AP2 Vault Card — Hardware | Matrix Scroll",
    description:
      "On-card Ed25519 signing for AI agent payments. The private key lives on NXP SE050 silicon — not in software, not in the cloud.",
    ogTitle: "AP2 Vault Card — The key never leaves the card",
  },
  "ap2/index.html": {
    path: "/ap2/",
    title: "AP2 Agent Payments — Matrix Scroll",
    description:
      "Signed agent payment envelopes with offline verification. Pair with the AP2 Vault Card for possession-factor approval on every mandate.",
    ogTitle: "AP2 Agent Payments — Signed mandates with hardware approval",
  },
  "docs/index.html": {
    path: "/docs/",
    title: "Documentation — Matrix Scroll",
    description: "Install the Matrix Scroll SDK, configure git hooks, and verify signed commit envelopes locally or in CI.",
    ogTitle: "Matrix Scroll Documentation",
  },
  "mcp/index.html": {
    path: "/mcp/",
    title: "MCP Server — Matrix Scroll",
    description: "Attest and verify agent commits inside Cursor, Claude Code, or VS Code with the public Matrix Scroll MCP server.",
    ogTitle: "Matrix Scroll MCP Server",
  },
  "verify/index.html": {
    path: "/verify/",
    title: "Browser Verifier — Matrix Scroll",
    description: "Paste a commit envelope or upload a manifest to verify Ed25519 signatures offline in your browser.",
    ogTitle: "Matrix Scroll Browser Verifier",
  },
  "spec/index.html": {
    path: "/spec/",
    title: "Specification — Matrix Scroll",
    description: "Canonical manifest schema, signature rules, and verification contract for matrixscroll.identity.v1 commit envelopes.",
    ogTitle: "Matrix Scroll Specification",
  },
  "compare/index.html": {
    path: "/compare/",
    title: "Compare — Matrix Scroll",
    description: "How signed commit provenance compares to GPG signatures, SLSA attestations, and in-toto layouts for agent-assisted Git.",
    ogTitle: "Compare Matrix Scroll",
  },
  "ecosystem/index.html": {
    path: "/ecosystem/",
    title: "Ecosystem — Matrix Scroll · AP2 · SSX360",
    description: "Three-layer stack: Matrix Scroll protocol, AP2 Vault Card hardware, and SSX360 hosted control plane for policy and audit.",
    ogTitle: "Matrix Scroll Ecosystem",
  },
  "roadmap/index.html": {
    path: "/roadmap/",
    title: "Roadmap — Matrix Scroll",
    description: "Foundation shipped. Transparency log, issuer registry, and AP2 hardware integrations on the roadmap.",
    ogTitle: "Matrix Scroll Roadmap",
  },
  "authority/index.html": {
    path: "/authority/",
    title: "Authority — Matrix Scroll",
    description: "Issuer keys, certificate status, and trust anchors for Matrix Scroll identity verification.",
    ogTitle: "Matrix Scroll Authority",
  },
  "404.html": {
    path: "/404",
    title: "Page not found — Matrix Scroll",
    description: "The page you requested was not found on matrixscroll.com.",
    ogTitle: "Page not found — Matrix Scroll",
    noindex: true,
  },
  "id/index.html": {
    path: "/id/",
    title: "Identity lookup — Matrix Scroll",
    description: "Look up a Matrix Scroll identity certificate by ID.",
    ogTitle: "Matrix Scroll Identity Lookup",
    noindex: true,
  },
  "docs/Whitepaper.html": {
    path: "/docs/Whitepaper.html",
    title: "Whitepaper — Matrix Scroll",
    description: "Technical whitepaper for signed commit provenance, verification, and the Matrix Scroll trust model.",
    ogTitle: "Matrix Scroll Whitepaper",
  },
  "docs/why.html": {
    path: "/docs/why.html",
    title: "Why Matrix Scroll exists — Documentation",
    description: "Why signed commit provenance matters for AI-assisted development — and how Matrix Scroll closes the gap.",
    ogTitle: "Why Matrix Scroll exists",
  },
  "docs/protocol-flow.html": {
    path: "/docs/protocol-flow.html",
    title: "Protocol flow — Matrix Scroll Documentation",
    description: "From agent output to durable proof: the four-step Matrix Scroll signing and verification flow.",
    ogTitle: "Matrix Scroll protocol flow",
  },
  "docs/threat-model.html": {
    path: "/docs/threat-model.html",
    title: "Threat model — Matrix Scroll Documentation",
    description: "Matrix Scroll attestation limits, L1 software-key assumptions, and trust anchor distribution.",
    ogTitle: "Matrix Scroll threat model",
  },
  "hardware/lab/index.html": {
    path: "/hardware/lab/",
    title: "AP2 PoC Lab — Hardware configurator | Matrix Scroll",
    description: "Interactive AP2 Vault Card configurator and device simulator for design partners.",
    ogTitle: "AP2 PoC Lab — Hardware configurator",
  },
}

function buildHead(page) {
  const url = `${SITE}${page.path}`
  const robots = page.noindex ? "noindex, nofollow" : "index, follow"
  return `  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${page.title}</title>
    <meta name="description" content="${page.description}">
    <meta name="keywords" content="Matrix Scroll, commit provenance, Ed25519, agent signing, AP2 Vault Card, offline verification, git hooks">
    <meta name="author" content="Matrix Scroll">
    <meta name="robots" content="${robots}">
    <meta name="content-language" content="en-US">
    <meta name="geo.region" content="US">
    <meta name="geo.placename" content="United States">
    <link rel="canonical" href="${url}">
    <link rel="alternate" hreflang="en-US" href="${url}">
    <link rel="alternate" hreflang="x-default" href="${url}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Matrix Scroll">
    <meta property="og:locale" content="${LOCALE}">
    <meta property="og:url" content="${url}">
    <meta property="og:title" content="${page.ogTitle}">
    <meta property="og:description" content="${page.description}">
    <meta property="og:image" content="${OG_IMAGE}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:alt" content="AP2 Vault Card — possession-factor approval for AI agent payments">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@MatrixScroll">
    <meta name="twitter:title" content="${page.ogTitle}">
    <meta name="twitter:description" content="${page.description}">
    <meta name="twitter:image" content="${OG_IMAGE}">
    <meta name="twitter:image:alt" content="AP2 Vault Card — possession-factor approval for AI agent payments">
    <meta name="theme-color" content="#050505">
    <link rel="icon" href="/favicon.ico" sizes="48x48">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <link rel="manifest" href="/site.webmanifest">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>`
}

for (const [relPath, page] of Object.entries(pages)) {
  const filePath = path.join(root, relPath)
  if (!fs.existsSync(filePath)) {
    console.warn("skip missing", relPath)
    continue
  }
  let html = fs.readFileSync(filePath, "utf8")
  const headEnd =
    html.match(/<link rel="preconnect" href="https:\/\/fonts\.gstatic\.com" crossorigin>/)?.[0] ??
    html.match(/<link rel="stylesheet" href="\/assets\/site\.css">/)?.[0]
  if (!headEnd) {
    console.warn("skip no anchor", relPath)
    continue
  }
  html = html.replace(/<head>[\s\S]*?(?=<link rel="stylesheet" href="\/assets\/site\.css">)/, `${buildHead(page)}\n    `)
  fs.writeFileSync(filePath, html)
  console.log("patched", relPath)
}
