# Matrix Scroll Site

This repository is the source for the public Matrix Scroll product site and
proof surfaces at [matrixscroll.com](https://matrixscroll.com/).

**Matrix Scroll is signed commit-time provenance for agent-assisted Git,
verified offline, with hardware as an optional trust upgrade.**

Pinned public release: `matrixscroll==0.2.6`

## What belongs in this repo

- Homepage, docs, compare, verify, and device-preview copy for
  `matrixscroll.com`
- Static assets, HTML, and Vercel configuration for the public product surface
- Product-language changes that must stay aligned with
  `matrixscroll==0.2.6`, the GitHub README, and launch materials

## Public positioning rules

- Lead with the software product first. `MATRIXSCROLL_MODE=emulated` is the
  valid evaluation path.
- Keep hardware labeled preview or design-partner only until the SE050
  acceptance package is complete.
- Position Matrix Scroll as complementary to scanners, branch protection, and
  artifact attestations.
- Avoid assistant-brand-led hero framing. Public examples should be generic and
  Matrix Scroll-led.
- Keep `ssx360.com` as the redirect and company shell, not a second product
  explainer.

## Canonical proof links

- Product site: [matrixscroll.com](https://matrixscroll.com/)
- Browser verifier: [matrixscroll.com/verify](https://matrixscroll.com/verify/)
- Compare page: [matrixscroll.com/compare](https://matrixscroll.com/compare/)
- Device preview: [matrixscroll.com/device](https://matrixscroll.com/device/)
- PyPI release provenance: [matrixscroll 0.2.6](https://pypi.org/project/matrixscroll/0.2.6/)
- SDK repo: [SSX360/matrixscroll](https://github.com/SSX360/matrixscroll)
- Public CI proof: [SSX360/matrixscroll-verify-action](https://github.com/SSX360/matrixscroll-verify-action)

## Local workflow

This site is currently a static HTML surface rooted at
[`index.html`](./index.html) with lightweight Vercel rewrites in
[`vercel.json`](./vercel.json).

- Edit public copy here first when changing `matrixscroll.com`
- Keep version pins and quickstart steps aligned with the SDK README
- Validate preview deploys before promotion

## Historical note

This repository still contains earlier experiments and supporting artifacts from
older Digital Rain and companion-style work. Treat those materials as
historical or secondary. Public messaging, deployment decisions, and README copy
should all follow the Matrix Scroll product story above.

Archived examples to treat as historical notes, not current launch surfaces:

- `INTEGRATIONS.md`
- `docs/DAILY_USE.md`
- `docs/Documentation.md`
- `docs/Documentation.html`
