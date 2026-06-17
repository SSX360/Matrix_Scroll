# Matrix Scroll — A Hardware Root of Trust for AI-Written Code

*Whitepaper · v1 · June 2026 · SSX 360 Corp. (Delaware)*

---

## The short version

AI now writes a large share of the code that lands in production. That is great for
velocity and terrible for provenance. When an agent edits forty files at 2 a.m., who
actually authored that change? Which machine produced it? Can you prove, six months
later in an audit, that the diff came from a trusted operator and not from a hijacked
token or a poisoned dependency?

Most teams cannot answer those questions today. Their git history says "Jane committed
this," but git trusts whatever name and email it is handed. Signing keys, when they
exist at all, sit in plaintext in `~/.ssh` or a CI secret store — copyable, exfiltratable,
and only as safe as the laptop they live on.

Matrix Scroll is our attempt to fix the weakest link: **where the signing key lives, and
who is allowed to use it.** It is two pieces that work together:

- **Digital Rain** — the software. A local context engine and MCP server that grounds
  your AI agents in your actual codebase and produces signed release evidence.
- **Matrix Scroll** — the hardware. A USB-C secure element that holds an Ed25519 key
  the operating system can never read, so signatures can be produced but never forged.

This paper explains what problem we are solving, what we defend against (and what we
do not), how the cryptography works, and — importantly — what ships today versus what
is still on the bench.

---

## 1. Why we built this

We started Digital Rain as a developer-productivity tool: a small MCP server that scans
your project, ranks local context with BM25, answers questions grounded in real docs,
and falls back gracefully from a cloud model to a local one when you are offline. It was
useful. People liked it.

But the more we used agents to write code, the more one question nagged at us. The agent
is fast and mostly right, but it is also a process running with our credentials. If that
process — or anything wearing its identity — pushes a change, the audit trail looks
identical to a human doing careful work. The trust we place in a commit is, in practice,
trust in an unencrypted key file.

So the real product stopped being "better AI context" and became "make every AI-assisted
change cryptographically attributable to a physical device you control." Context is still
the foundation; attestation is the point.

---

## 2. Threat model

We think a security product should say plainly what it does and does not stop. Here is
ours.

**What Matrix Scroll is designed to defend against**

- **Key theft from a compromised host.** Malware on a developer laptop can read files,
  scrape environment variables, and copy `~/.ssh`. It cannot extract a private key that
  was generated inside the secure element and never leaves it. The worst an attacker can
  do is *ask the device to sign while they are present on the machine* — a much smaller,
  time-bounded window than "copy the key and sign forever."
- **Identity spoofing in the commit trail.** Anyone can set `git config user.email` to
  your address. They cannot produce a valid Ed25519 signature for your device key.
- **Silent tampering with release artifacts.** Our manifests are signed over a canonical
  serialization, so a single byte changed after signing fails verification.
- **Repudiation.** A signed manifest ties a specific build to a specific device id at a
  specific time. "That wasn't from one of our machines" becomes checkable, not arguable.

**What it does not (and cannot) defend against**

- **A fully present, fully privileged attacker.** In traditional hardware keys, malware on your laptop can request signatures in the background while the key is plugged in. Matrix Scroll mitigates this via the UX of Consent: every signature request must be visually confirmed on the device's 1-bit Sharp Memory LCD and authorized by a physical capacitive touch. The mascot looks up, prompts confirmation, and will display an alarmed face if an unexpected request is made. The key remains secure inside the NXP SE050 secure element, and the user must physically tap the device to authorize any signature.
- **Bad code that is correctly signed.** We prove *who and where*, not *whether the code
  is good*. A signed change can still be a bug or a deliberate backdoor by an authorized
  operator. Attestation complements review; it does not replace it.
- **Supply-chain compromise upstream of you.** We sign what your machine produced. If a
  malicious dependency was already in your tree, the signature faithfully attests that you
  shipped it.

Being honest about that second list is, we think, the difference between a security
product and a marketing slide.

---

## 3. Architecture at a glance

Two layers, one trust boundary.

```
        ┌─────────────────────────────────────────────┐
        │  Your IDE (Cursor / VS Code / JetBrains)      │
        │  ── speaks MCP ──┐                            │
        └──────────────────┼────────────────────────────┘
                           │
                  ┌────────▼─────────┐     grounds agents in
                  │   Digital Rain   │     real, ranked context
                  │  (MCP + scanner) │
                  └────────┬─────────┘
                           │ asks for a signature over a manifest
                  ┌────────▼─────────┐
                  │  Identity layer  │  EmulatedProvider  (disk key, today)
                  │   (Ed25519)      │  HardwareProvider  (SE050, roadmap)
                  └────────┬─────────┘
                           │ sign() — host OS cannot read key
                  ┌────────▼─────────┐
                  │  Matrix Scroll   │  RP2040 MCU + LCD Screen (Consent UI)
                  │  (Dual-Chip)     ├──[I2C]── NXP SE050 (EAL6+ Secure Element)
                  └──────────────────┘
```

The crucial line is the last one. In the emulated build the "secure element" is a key
file on disk with owner-only permissions — good enough to develop and integrate against.
In the hardware build, that line is a physical chip boundary the host CPU cannot reach
across.

---

## 4. The software: Digital Rain

Digital Rain is a local-first MCP server (internal id `cursor-copilot`, kept for backward
compatibility) exposing thirteen tools to any MCP-capable editor. The parts that matter
for this paper:

- **Project scanner.** Detects languages, frameworks, package managers, SDKs, and Jupyter
  notebook health. This is what "grounding" actually means in practice — the agent sees
  your real stack, not a guess.
- **BM25 retrieval.** A local lexical index over documentation and an MCP catalog. No
  embeddings to leak, no vectors leaving the machine. It is boring and it works.
- **Fallback LLM chain.** Anthropic → Gemini → local Ollama, in that order, with the
  preferred backend moved to the front. If every cloud path fails, you can still work
  fully offline against a local model. For sensitive code, that is a feature, not a
  consolation prize.
- **Release evidence.** `qa/release_evidence.py` collects what a build produced and asks
  the identity layer to sign it, emitting a `manifest.json` with a signature block and a
  human-readable `summary.md`.

None of this requires the hardware. That is deliberate — the software is useful on its
own, and the emulator lets you integrate the full signing flow before a device exists on
your desk.

---

## 5. The hardware: Matrix Scroll

The device is a keychain-sized, matte black anodized desktop object with a lime accent, built around a dual-chip architecture: an RP2040-class MCU to drive the USB communication, capacitive touch sensor, and a high-contrast 1.3" Sharp Memory LCD, coupled with an NXP SE050 secure element for key custody. The private signing keys are generated inside the SE050 and never cross the silicon boundary to the RP2040 or the host OS. The screen displays our character avatar (a desk companion living in software and silicon) which acts as a trust and consent surface: the avatar prompts touch confirmation for every signature, showing a signing state or an alarmed face on unexpected activity, neutralizing background malware signature requests.

A stable, human-readable **device id** (for example `MS-4319-20D5`) is derived from the
public key so humans can talk about "which device signed this" without pasting 32 bytes of
base64 at each other.

We are pre-launch on the physical unit (see §8). Everything above the chip boundary —
the API, the manifest format, the verification flow — is identical between emulated and
hardware modes, so code written against the emulator today keeps working when the device
arrives.

---

## 6. Cryptographic design

We kept this intentionally small. Small is auditable.

- **Algorithm: Ed25519.** Deterministic signatures, 32-byte public keys, fast verify, no
  parameter choices to get wrong. We use the `cryptography` library's implementation.
- **Canonical serialization.** Before signing, a manifest is reduced to a canonical byte
  string: keys sorted recursively, ASCII-only escaping, compact separators, and an
  explicit rejection of `NaN`/`Infinity` (which have no portable JSON form). This is the
  detail that makes a signature produced on Windows verify byte-for-byte on Linux. Without
  it, signatures "drift" across platforms and you spend a weekend learning why.
- **The signature block.** A signed manifest carries a `signature` object holding the
  signing `device_id`, the algorithm, and the base64 signature `value`. Verification
  recomputes the canonical bytes *excluding the signature block* and checks them against
  the device's public key. Change anything else in the document and verification fails.
- **What is signed, exactly.** Today we sign release manifests — the evidence of a build.
  On-device signing of individual git commits is on the roadmap (§8); we would rather ship
  one honest signing path than three half-wired ones.

If you want to verify a manifest yourself, you do not need our software. The public key is
published via `GET /api/identity` and the `device_identity` MCP tool, and the canonical
rules above are enough to reimplement verification in any language.

---

## 7. Why local-first matters here

A signing product that phones home is a contradiction. The whole point is that trust lives
on your device, not in our cloud. So Digital Rain runs entirely on `localhost`, the index
is built from local sources, and the offline LLM path exists precisely so that
ultra-sensitive code never has to leave the building to get useful AI assistance. We do not
see your source, your prompts, or your keys, because there is no "we" in the data path.

---

## 8. What ships today vs. what is on the bench

We would rather under-promise here.

| Capability | Status |
|---|---|
| Digital Rain MCP server, 13 tools, project scan, BM25 retrieval | **Shipping** |
| Anthropic → Gemini → Ollama fallback (incl. fully offline) | **Shipping** |
| Emulated Ed25519 identity, signed release manifests, verification | **Shipping** |
| `/api/identity` + `device_identity` tool | **Shipping** |
| Cross-IDE setup (Cursor, VS Code native, Cline/Roo, Claude Desktop) | **Shipping** |
| Matrix Scroll (Founders Edition) with LCD Avatar & RP2040 MCU | **Pre-order, target Q3 2026** |
| Touch-to-sign presence check & avatar consent UI | **Planned with hardware** |
| On-device signing of individual git commits | **Roadmap** |
| Org-level attestation dashboard / fleet key registry | **Roadmap** |

The honest summary: **the software and the full signing/verification flow are real and
usable now in emulated mode.** The hardware that moves the key behind silicon is what you
are reserving when you pre-order.

---

## 9. A note on compliance

Security pages love to say a product "satisfies SOC 2 and ISO 27001." That is not quite how
those work — they are organizational certifications, not something a dongle confers. What we
can say accurately: Matrix Scroll produces **hardware-attested, tamper-evident evidence**
that maps cleanly onto the change-management, access-control, and supply-chain-integrity
controls those frameworks ask about (e.g., SOC 2 CC8, SLSA provenance). It gives your
auditor artifacts to point at. It does not make you certified on its own, and we will never
claim it does.

---

## 10. Open questions and future work

- **Revocation and rotation.** Keys outlive their usefulness. A fleet registry with clean
  rotation and revocation is the next hard problem.
- **Multi-signer workflows.** Pair-programming and CI both touch a change; representing
  "two devices attest this" is more honest than collapsing it to one.
- **Commit-level granularity.** Signing the build is useful; signing each change is the
  long-term goal, and it raises real UX questions about how often a human should be asked
  to confirm.

We will write these up as we solve them, in the same plain language. If you are deploying
this in anger and hit something we did not anticipate, tell us:
**operations@matrixscroll.com**.

---

*Digital Rain (software) · Matrix Scroll (hardware) · © 2026 SSX 360 Corp.*

