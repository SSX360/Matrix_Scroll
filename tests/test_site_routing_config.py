import json
import unittest
from pathlib import Path


class SiteRoutingConfigTests(unittest.TestCase):
    @staticmethod
    def _status_markers() -> tuple[str, ...]:
        return (
            "PyPI <code>0.2.6</code>, Git hooks, Scroll Gate PR verification, browser verifier, and emulated-mode evaluation.",
            "SSX360 SE050 hardware preview and verifier-compatible external Ed25519 signer guidance.",
            "IAM, sandboxing, prompt filtering, or an agent runtime.",
        )

    def test_launch_route_pages_exist(self):
        site_root = Path(__file__).resolve().parents[1]

        expected_pages = {
            "index.html": "Signed provenance for agent-assisted Git commits.",
            "compare/index.html": "Keep your current controls. Add commit-time provenance.",
            "device/index.html": "Software first. Preview trust upgrade next.",
            "docs/index.html": 'matrixscroll==0.2.6',
            "spec/index.html": "Pure Ed25519 over canonical JSON bytes.",
            "verify/index.html": "Tamper Sample",
        }

        for relative_path, marker in expected_pages.items():
            page = site_root / relative_path
            self.assertTrue(page.exists(), relative_path)
            self.assertIn(marker, page.read_text(encoding="utf-8"), relative_path)

    def test_public_pages_share_status_language(self):
        site_root = Path(__file__).resolve().parents[1]

        for relative_path in (
            "index.html",
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            for marker in self._status_markers():
                self.assertIn(marker, text, relative_path)

    def test_homepage_and_docs_answer_exact_evaluator_questions(self):
        site_root = Path(__file__).resolve().parents[1]
        questions = (
            "What is Matrix Scroll and how does it secure Git?",
            "How do hardware and emulated modes differ in Matrix Scroll?",
            "How can I integrate Matrix Scroll into a CI/CD workflow?",
        )

        for relative_path in ("index.html", "docs/index.html"):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            for question in questions:
                self.assertIn(question, text, relative_path)

    def test_public_pages_do_not_ship_mojibake(self):
        site_root = Path(__file__).resolve().parents[1]

        for relative_path in (
            "index.html",
            "docs/index.html",
            "compare/index.html",
            "verify/index.html",
            "spec/index.html",
            "device/index.html",
        ):
            text = (site_root / relative_path).read_text(encoding="utf-8")
            for marker in ("â€”", "â†’", "â—", "Ã"):
                self.assertNotIn(marker, text, relative_path)

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
