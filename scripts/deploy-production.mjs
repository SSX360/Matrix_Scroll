#!/usr/bin/env node
/**
 * Deploy matrixscroll.com to Vercel production.
 *
 * CI: set VERCEL_TOKEN (required). ORG/PROJECT ids default from scripts/vercel-project.json.
 * Local: run `npx vercel link --scope ssx-360` once, or export the same env vars.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const vercelDir = join(root, ".vercel")
const defaultsPath = join(root, "scripts", "vercel-project.json")

function loadProjectConfig() {
  const linked = join(vercelDir, "project.json")
  if (existsSync(linked)) {
    return JSON.parse(readFileSync(linked, "utf8"))
  }
  if (existsSync(defaultsPath)) {
    return JSON.parse(readFileSync(defaultsPath, "utf8"))
  }
  return {}
}

function ensureLinkedProject() {
  const defaults = loadProjectConfig()
  const orgId = process.env.VERCEL_ORG_ID || defaults.orgId
  const projectId = process.env.VERCEL_PROJECT_ID || defaults.projectId
  const projectName = defaults.projectName || "matrixscroll-site"

  if (!orgId || !projectId) {
    console.error(
      "Missing Vercel project linkage. Set VERCEL_ORG_ID and VERCEL_PROJECT_ID, or add .vercel/project.json via `npx vercel link --scope ssx-360`.",
    )
    process.exit(1)
  }

  if (!process.env.VERCEL_TOKEN) {
    console.error(
      "Missing VERCEL_TOKEN. Add it as a GitHub Actions secret (SSX360/Matrix_Scroll → Settings → Secrets → VERCEL_TOKEN).",
    )
    process.exit(1)
  }

  mkdirSync(vercelDir, { recursive: true })
  writeFileSync(
    join(vercelDir, "project.json"),
    JSON.stringify({ orgId, projectId, projectName }, null, 2) + "\n",
  )

  process.env.VERCEL_ORG_ID = orgId
  process.env.VERCEL_PROJECT_ID = projectId
}

function deploy() {
  const scope = process.env.VERCEL_SCOPE || "ssx-360"
  const args = ["vercel", "deploy", "--prod", "--yes", "--scope", scope, "--token", process.env.VERCEL_TOKEN]

  console.log(`Deploying matrixscroll-site to production (scope: ${scope})…`)

  const result = spawnSync(process.platform === "win32" ? "npx.cmd" : "npx", args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: process.env,
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }

  console.log("\nProduction deploy finished: https://matrixscroll.com")
}

ensureLinkedProject()

const configEnv = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  NEXT_PUBLIC_PORTAL_URL: process.env.NEXT_PUBLIC_PORTAL_URL,
}

console.log("Generating runtime config…")
spawnSync(process.execPath, [join(root, "scripts", "generate-runtime-config.mjs")], {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, ...configEnv },
})

deploy()
