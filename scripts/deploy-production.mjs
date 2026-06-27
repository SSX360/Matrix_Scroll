#!/usr/bin/env node
/**
 * Deploy matrixscroll.com without Vercel BLOCKED on dirty git.
 * Copies only public site assets to a temp folder, then runs vercel deploy --prod.
 *
 * Usage: node scripts/deploy-production.mjs
 * Requires: linked .vercel/project.json and `npx vercel` auth for ssx-360 scope.
 */
import { cpSync, existsSync, mkdtempSync } from "node:fs"
import { tmpdir } from "node:os"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const vercelDir = join(root, ".vercel")

if (!existsSync(join(vercelDir, "project.json"))) {
  console.error("Missing .vercel/project.json — run `npx vercel link` in Matrix_Scroll first.")
  process.exit(1)
}

const staging = mkdtempSync(join(tmpdir(), "matrixscroll-deploy-"))
const copyPaths = ["index.html", "vercel.json", "static", "docs", "compare", "verify", "spec", "device", "og-image.png"]

for (const rel of copyPaths) {
  const src = join(root, rel)
  if (!existsSync(src)) continue
  cpSync(src, join(staging, rel), { recursive: true })
}

cpSync(vercelDir, join(staging, ".vercel"), { recursive: true })

const vercelScope = process.env.VERCEL_SCOPE || "ssx-360"
const result = spawnSync(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["vercel", "deploy", "--prod", "--yes", "--scope", vercelScope],
  { cwd: staging, stdio: "inherit", shell: process.platform === "win32" },
)

if (result.status !== 0) {
  process.exit(result.status ?? 1)
}

console.log(`\nDeployed from clean staging dir: ${staging}`)
