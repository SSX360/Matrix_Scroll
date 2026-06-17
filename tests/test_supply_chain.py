import json
import tempfile
import unittest
from pathlib import Path

from qa import supply_chain


class SupplyChainEvidenceTests(unittest.TestCase):
    def test_parse_requirements_extracts_names_scopes_and_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "requirements.txt"
            requirements.write_text(
                "\n".join(
                    [
                        "# comment",
                        "Flask==3.0.1",
                        "requests>=2.31",
                        "local-lib @ file:///tmp/local-lib",
                        "--index-url https://example.invalid/simple",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = supply_chain.parse_requirements(requirements)

        by_name = {item["name"]: item for item in parsed}
        self.assertEqual(by_name["flask"]["version"], "3.0.1")
        self.assertEqual(by_name["requests"]["specifier"], ">=2.31")
        self.assertEqual(by_name["local-lib"]["specifier"], "@ file:///tmp/local-lib")
        self.assertNotIn("--index-url", by_name)

    def test_build_bom_uses_brand_new_project_manifests_without_environment_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("flask==3.0.1\nrequests>=2.31\n", encoding="utf-8")
            (root / "requirements-dev.txt").write_text("pytest>=8\n", encoding="utf-8")

            bom = supply_chain.build_bom(root, include_environment=False)
            assessment = supply_chain.assess_supply_chain(root, bom)

        component_names = {item["name"] for item in bom["components"]}
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        self.assertEqual(component_names, {"flask", "requests", "pytest"})
        self.assertTrue(assessment["inventory_ready"])
        self.assertIn("No dependency lockfile", " ".join(assessment["warnings"]))

    def test_generate_supply_chain_evidence_writes_sbom_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            out = Path(tmp) / "evidence"
            root.mkdir()
            (root / "requirements.txt").write_text("flask>=3.0\n", encoding="utf-8")

            summary = supply_chain.generate_supply_chain_evidence(root, out)

            sbom_path = Path(summary["artifacts"]["supply_chain_sbom"])
            summary_path = Path(summary["artifacts"]["supply_chain_summary"])
            sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
            saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertTrue(summary["inventory_ready"])
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(saved_summary["status"], "inventory_ready")
        self.assertIn("Dependency vulnerability review", saved_summary["field_evidence_needed"])


if __name__ == "__main__":
    unittest.main()
