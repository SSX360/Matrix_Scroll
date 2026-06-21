import json
import unittest
from pathlib import Path


class SiteRoutingConfigTests(unittest.TestCase):
    def test_launch_routes_rewrite_to_site_shell(self):
        config_path = Path(__file__).resolve().parents[1] / "vercel.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        rewrites = {(item["source"], item["destination"]) for item in config.get("rewrites", [])}

        for source in (
            "/docs",
            "/docs/",
            "/compare",
            "/compare/",
            "/verify",
            "/verify/",
            "/spec",
            "/spec/",
            "/device",
            "/device/",
        ):
            self.assertIn((source, "/index.html"), rewrites)

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


if __name__ == "__main__":
    unittest.main()
