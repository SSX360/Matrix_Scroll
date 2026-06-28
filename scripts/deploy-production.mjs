#!/usr/bin/env node
/**
 * Deploy matrixscroll.com without Vercel BLOCKED on dirty git.
 * Copies only public site assets to a temp folder, then runs vercel deploy --prod.
 *
 * Usage: node scripts/deploy-production.mjs
 * CI: requires VERCEL_TOKEN; optional VERCEL_ORG_ID + VERCEL_PROJECT_ID from secrets.
 */
import { cpSync, existsSync, mkdtempSync, mkdirSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const vercelDir = join(root, ".vercel")
const vercelToken = process.env.VERCEL_TOKEN?.trim()

if (!existsSync(join(vercelDir, "project.json")) && !(process.env.VERCEL_ORG_ID && process.env.VERCEL_PROJECT_ID)) {
  console.error("Missing .vercel/project.json — run `npx vercel link` or set VERCEL_ORG_ID + VERCEL_PROJECT_ID.")
  process.exit(1)
}

if (!vercelToken && !process.env.VERCEL_OIDC_TOKEN) {
  console.warn("Warning: VERCEL_TOKEN not set — relying on local Vercel CLI auth.")
}

const staging = mkdtempSync(join(tmpdir(), "matrixscroll-deploy-"))
const copyPaths = ["index.html", "vercel.json", "static", "docs", "compare", "verify", "spec", "device", "og-image.png"]

for (const rel of copyPaths) {
  const src = join(root, rel)
  if (!existsSync(src)) continue
  cpSync(src, join(staging, rel), { recursive: true })
}

if (existsSync(vercelDir)) {
  cpSync(vercelDir, join(staging, ".vercel"), { recursive: true })
} else if (process.env.VERCEL_ORG_ID && process.env.VERCEL_PROJECT_ID) {
  const linked = join(staging, ".vercel")
  mkdirSync(linked, { recursive: true })
  writeFileSync(
    join(linked, "project.json"),
    JSON.stringify({
      orgId: process.env.VERCEL_ORG_ID,
      projectId: process.env.VERCEL_PROJECT_ID,
      projectName: "matrixscroll-site",
    }),
  )
}

const vercelScope = process.env.VERCEL_SCOPE || "ssx-360"
const deployArgs = ["vercel", "deploy", "--prod", "--yes", "--scope", vercelScope]
if (vercelToken) {
  deployArgs.push("--token", vercelToken)
}

const result = spawnSync(process.platform === "win32" ? "npx.cmd" : "npx", deployArgs, {
  cwd: staging,
  stdio: "inherit",
  shell: process.platform === "win32",
  env: {
    ...process.env,
    VERCEL_ORG_ID: process.env.VERCEL_ORG_ID || "",
    VERCEL_PROJECT_ID: process.env.VERCEL_PROJECT_ID || "",
  },
})

if (result.status !== 0) {
  process.exit(result.status ?? 1)
}

console.log(`\nDeployed from clean staging dir: ${staging}`)
