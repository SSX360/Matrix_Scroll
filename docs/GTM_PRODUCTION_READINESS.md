# GTM Production Readiness

This repo should be launchable as the Software Node before any hardware device
commitment. Hardware can become the premium wedge after the software install,
security story, and buyer activation loop are proven.

## Production QA Gates

Run the full fresh-project release gate:

```powershell
.\.venv\Scripts\python.exe -m qa.run_gates --workspace empty --report out\qa-report.json
```

Required pass conditions:

- The backend starts without opening a browser.
- `COPILOT_WORKSPACE` points at a brand-new synthetic project.
- `/api/health`, `/api/workspace/status`, `/api/project/status`,
  `/api/diagnostics`, `/api/brainstorm`, and `/api/chat` all respond.
- `/api/diagnostics` is versioned, bound to the synthetic workspace, and redacts
  secret-like environment fields.
- TypeScript and monorepo fixtures expose per-service components and likely
  install, dev, build, or API launch commands from a brand-new project scan.
- Suggested launch commands pass static readiness checks for workspace-contained
  `cwd`, non-empty commands, known command prefixes, and destructive-script
  patterns. These checks do not execute installs or servers.
- Chat can answer a project-scan question without cloud keys or a live model.
- No stale demo workspace markers appear in user-facing responses.
- The stale-marker gate uses neutral configurable markers and does not depend on
  any prior customer, demo, or archived project path.

Optional fixture passes:

```powershell
.\.venv\Scripts\python.exe -m qa.run_gates --workspace python --report out\qa-python-report.json
.\.venv\Scripts\python.exe -m qa.run_gates --workspace typescript --report out\qa-typescript-report.json
.\.venv\Scripts\python.exe -m qa.run_gates --workspace monorepo --report out\qa-monorepo-report.json
.\.venv\Scripts\python.exe -m qa.run_gates --workspace notebook --report out\qa-notebook-report.json
.\.venv\Scripts\python.exe -m qa.run_gates --workspace security --report out\qa-security-report.json
```

## Release Evidence

Before a GTM build is published, build the release evidence pack:

```powershell
.\.venv\Scripts\python.exe -m qa.release_evidence --output-dir out\release-evidence
```

The command writes a timestamped folder containing:

- `manifest.json`: machine-readable command results, fixture reports, KPI status,
  local experiment matrix, git metadata, and release decisions. It is signed by
  the active Matrix Scroll root of trust (`identity.py`): a `signature` block
  records the device id, Ed25519 public key, mode, and signature value. Verify
  it with `identity.verify_manifest(...)`.
- `summary.md`: Sales/support-friendly release readout (includes the signer
  device id when the manifest is signed).
- `qa-empty-report.json`, `qa-python-report.json`, `qa-typescript-report.json`,
  `qa-monorepo-report.json`, `qa-notebook-report.json`, and
  `qa-security-report.json`: full synthetic workspace gate reports.
- `supply-chain-sbom.cdx.json`: CycloneDX-shaped dependency inventory for the
  release candidate.
- `supply-chain-summary.json`: manifest inventory, SBOM status, warnings, and
  field evidence still needed for paid GTM.

The evidence pack separates two decisions:

- `software_release_candidate`: all local software QA gates pass.
- `device_gtm_ready`: software QA passes and field evidence is available for
  install success and retained usage.

It also compares local build styles so optimization work is grounded in evidence:

- Empty project: first-run/offline-first readiness.
- Minimal Python web app: conventional application repo readiness.
- TypeScript frontend app: modern web app readiness plus inferred pnpm commands.
- Mixed frontend/API monorepo: multi-service repo readiness plus service launch
  commands.
- Notebook project: Data Analytics workflow readiness.
- Security-sensitive app: local-trust readiness, sensitive-file detection, and
  redaction of secret-like values surfaced from README or package script
  metadata.

## Brand-New Project QA Plan

The QA plan intentionally starts from generated projects, not from any existing
customer or demo repo. A passing release must prove the tool works when a buyer
opens a completely new folder.

1. Fresh-project foundation: run `qa.run_gates` against empty, Python,
   TypeScript, monorepo, notebook, and security-sensitive fixtures. Every report
   must bind `COPILOT_WORKSPACE` to the temporary fixture, return redacted
   diagnostics, answer a project-aware chat question in degraded mode, and avoid
   stale workspace markers.
2. Product quality hardening: keep unit tests and compile checks in the release
   evidence pack, add a focused regression test before each bug fix, and expand
   fixture coverage when a customer workflow reveals a new repo shape.
3. Security verification: map secure-development work to NIST SSDF, use OWASP
   ASVS 5.0 and OWASP SAMM as the application-security and maturity checklists,
   and keep local diagnostics privacy-first by default.
4. Supply-chain readiness: generate the SBOM artifacts in every release pack,
   then add dependency vulnerability review, OpenSSF Scorecard-style dependency
   health checks, signed installer provenance, and release artifact attestations.
5. GTM field proof: after local gates are green, measure install success, time
   to first useful scan, first-week retained usage, support handoff quality, and
   DORA delivery metrics during alpha and founder-customer pilots.
6. Device gate: treat hardware as blocked until the software install, support,
   security, supply-chain, and retention evidence are proven in the field.

Minimum manual evidence to capture alongside the pack:

- Unit tests: `.\.venv\Scripts\python.exe -m unittest discover -v tests`
- Compile check: `.\.venv\Scripts\python.exe -m py_compile app.py brainstorm.py chat_actions.py chat_advisor.py companion.py cursor_artifacts.py desktop_launcher.py identity.py ingest.py llm.py mcp_server.py scanner.py search.py vault.py workspace_config.py qa\run_gates.py qa\release_evidence.py qa\supply_chain.py`
- Fresh-project QA report from `qa.run_gates`
- Supply-chain SBOM and summary from `qa.supply_chain`
- Browser verification of the local dashboard first screen
- Installer or launch script smoke test on a clean Windows profile
- Redacted diagnostic output from `/api/diagnostics` for support handoff
- Security-sensitive project gate proving sentinel secrets do not appear in
  project scan, diagnostics, brainstorm, chat, or release evidence payloads

## GTM Readiness Metrics

Track these for alpha and founder customers:

- Install success rate: target 90%+
- Time to first useful project scan: target under 3 minutes
- Fresh-project QA pass rate: target 95%+
- Chat degraded-mode success: target 95%+
- Diagnostics redaction coverage: target 100%
- Launch command static validation: target 100%
- Project secret redaction: target 100%
- SBOM/dependency inventory: generated for every release
- First-week retained usage: target 40%+
- Stale workspace leaks: target zero

## Security And Supply-Chain Track

Treat the current product as a Software Node until these gates are true. This
keeps the hardware/security story aligned with what the repo can prove.

- Secure development baseline: map release work to
  [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final).
- App-security verification: use
  [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/)
  as the checklist for authentication, access control, cryptography, logging,
  and data protection.
- Security maturity: use
  [OWASP SAMM](https://owasp.org/www-project-samm/) to turn ad hoc security work
  into a staged assurance program.
- Supply-chain integrity: add build provenance aligned with
  [SLSA](https://slsa.dev/) and signed artifact attestations before publishing
  installers.
- SBOM: generate a CycloneDX-compatible bill of materials using the
  [CycloneDX standard](https://cyclonedx.org/) for every release candidate.
- Dependency security: run dependency vulnerability review and OpenSSF-style
  health checks, including
  [OpenSSF Scorecard](https://scorecard.dev/), before paid pilots.
- Delivery quality: track software delivery speed and safety using
  [DORA metrics](https://dora.dev/guides/dora-metrics/) once pilots begin.

## Production Device Track

Do not open paid hardware preorders until the Software Node proves:

- Repeatable signed desktop install
- Redacted diagnostics and support workflow
- SBOM and dependency vulnerability review
- Build provenance and artifact attestation for installer outputs
- Clear privacy posture for local scans and cloud fallback
- 20-user alpha feedback with activation and retention evidence
- Hardware BOM, secure element choice, firmware update path, and manufacturing
  estimate reviewed by a qualified partner
