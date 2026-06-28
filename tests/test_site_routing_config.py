import json
import unittest
from pathlib import Path


class SiteRoutingConfigTests(unittest.TestCase):
    @staticmethod
    def _status_markers() -> tuple[str, ...]:
        return (
            "PyPI <code>0.2.6</code>",
            "SSX360 SE050 hardware preview and verifier-compatible external Ed25519 signer guidance.",
            "IAM, sandboxing, prompt filtering, or an agent runtime.",
        )

    def test_launch_route_pages_exist(self):
        site_root = Path(__file__).resolve().parents[1]

        expected_pages = {
            "index.html": "wrote every commit.",
            "compare/index.html": "Keep your current controls. Add commit-time provenance.",
            "device/index.html": "Software first. Preview trust upgrade next.",
            "hardware/index.html": "NFC tap-to-approve. Same verifier contract as software.",
            "docs/index.html": "quickstart-mcp.md",
            "spec/index.html": "Pure Ed25519 over canonical JSON bytes.",
            "verify/index.html": "Tamper Sample",
        }

        for relative_path, marker in expected_pages.items():
            page = site_root / relative_path
            self.assertTrue(page.exists(), relative_path)
            self.assertIn(marker, page.read_text(encoding="utf-8"), relative_path)

    def test_public_pages_share_status_language(self):
        site_root = Path(__file__).resolve().parents[1]

        # The stripped-down homepage carries the same honest-limits content in a
        # dedicated section, not the shared one-line status markers. The deeper
        # routes still share the canonical status language.
        for relative_path in (
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
            "hardware/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            for marker in self._status_markers():
                self.assertIn(marker, text, relative_path)

    def test_homepage_carries_provenance_anchors(self):
        homepage = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        for marker in (
            "Know who",
            "wrote every commit.",
            "Install the MCP",
            "Verify a commit",
            "https://matrixscroll.com/verify/",
            "Book a provenance pilot",
            "Ready for rollout?",
            "https://ssx360.com/contact?intent=pilot",
            'matrixscroll[mcp]==0.2.6',
            "matrixscroll-mcp",
            '"mcpServers"',
            'id="answers"',
            'id="hardware"',
            "Hardware ready",
            "/hardware/",
            "Request hardware pilot",
            "What is Matrix Scroll and how does it secure Git?",
        ):
            self.assertIn(marker, homepage)
        self.assertNotIn('pip install <span class="st">"matrixscroll[mcp]"</span>', homepage)
        # Compliance language rule: never claim a regulation requires signing.
        for forbidden in ("required by", "mandated", "audit repo trust", "repo intelligence"):
            self.assertNotIn(forbidden, homepage)

    def test_homepage_and_docs_answer_exact_evaluator_questions(self):
        site_root = Path(__file__).resolve().parents[1]
        questions = (
            "What is Matrix Scroll and how does it secure Git?",
            "How do hardware and emulated modes differ in Matrix Scroll?",
            "How can I integrate Matrix Scroll into a CI/CD workflow?",
        )

        for relative_path in ("docs/index.html",):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            self.assertIn("MCP server", text, relative_path)
            for question in questions:
                self.assertIn(question, text, relative_path)

        homepage = (site_root / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="answers"', homepage)
        homepage_questions = (
            "What is Matrix Scroll and how does it secure Git?",
            "How do hardware and emulated modes differ",
            "How do I integrate Matrix Scroll into CI/CD",
        )
        for question in homepage_questions:
            self.assertIn(question, homepage)

    def test_public_pages_share_rollout_ctas(self):
        site_root = Path(__file__).resolve().parents[1]
        for relative_path in (
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
            "hardware/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            self.assertIn("Book a provenance pilot", text, relative_path)
            self.assertIn("https://ssx360.com/signup", text, relative_path)
            self.assertIn("/verify/", text, relative_path)

    def test_docs_hub_links_ap2_evaluation_path(self):
        docs_page = (Path(__file__).resolve().parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Evaluating payment approval?", docs_page)
        self.assertIn("https://ssx360.com/partner/ap2-vault-card", docs_page)
        self.assertIn("https://ssx360.com/contact?intent=ap2", docs_page)
        self.assertEqual(docs_page.count("Ready for rollout?"), 1)

    def test_docs_hub_does_not_promote_legacy_product_notes(self):
        docs_page = (Path(__file__).resolve().parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Documentation.html (legacy)", docs_page)

    def test_legacy_documentation_page_is_noindex(self):
        legacy = (Path(__file__).resolve().parents[1] / "docs" / "Documentation.html").read_text(encoding="utf-8")
        self.assertIn('content="noindex,nofollow"', legacy)

    def test_public_pages_do_not_ship_legacy_mcp_ids(self):
        site_root = Path(__file__).resolve().parents[1]
        for relative_path in (
            "index.html",
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
            "hardware/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("cursor-copilot", text, relative_path)

    def test_public_pages_do_not_ship_mojibake(self):
        site_root = Path(__file__).resolve().parents[1]

        for relative_path in (
            "index.html",
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
            "hardware/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            for marker in ("â€”", "â†’", "â—", "Ã"):
                self.assertNotIn(marker, text, relative_path)

    def test_vercel_redirects_device_to_hardware(self):
        config_path = Path(__file__).resolve().parents[1] / "vercel.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        redirects = {(item["source"], item["destination"]) for item in config.get("redirects", [])}

        self.assertIn(("/device", "/hardware/"), redirects)
        self.assertIn(("/device/", "/hardware/"), redirects)

    def test_docs_reference_pages_keep_explicit_html_destinations(self):
        config_path = Path(__file__).resolve().parents[1] / "vercel.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        rewrites = {(item["source"], item["destination"]) for item in config.get("rewrites", [])}

        self.assertIn(("/docs/Documentation.md", "/docs/Documentation.html"), rewrites)
        self.assertIn(("/docs/Whitepaper.md", "/docs/Whitepaper.html"), rewrites)

    def test_public_schema_files_match_published_urls(self):
        schema_dir = Path(__file__).resolve().parents[1] / "schemas"

        for filename in (
            "commit-envelope.v1.json",
            "evidence-pack.v1.json",
            "release-manifest.v1.json",
        ):
            schema_path = schema_dir / filename
            self.assertTrue(schema_path.exists(), filename)
            text = schema_path.read_text(encoding="utf-8")
            self.assertIn(f'"$id": "https://matrixscroll.com/schemas/{filename}"', text)

    def test_verify_surface_mentions_browser_and_ci_contract(self):
        verify_page = (Path(__file__).resolve().parents[1] / "verify" / "index.html").read_text(encoding="utf-8")
        verify_script = (Path(__file__).resolve().parents[1] / "static" / "verify.js").read_text(encoding="utf-8")

        for marker in (
            "Load Sample",
            "Tamper Sample",
            "Private by default",
            "matrixscroll==0.2.6",
            "SSX360/matrixscroll-verify-action@v1",
        ):
            self.assertIn(marker, verify_page)

        for marker in (
            "MS-TAMP-ERED",
            "Signature valid",
            "Device ID mismatch",
            "canonical_bytes",
        ):
            self.assertIn(marker, verify_script)


if __name__ == "__main__":
    unittest.main()
