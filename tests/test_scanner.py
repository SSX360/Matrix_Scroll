import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path

import scanner
from qa import run_gates


class ScannerTests(unittest.TestCase):
    def test_skip_dirs_includes_scratch(self):
        self.assertIn("scratch", scanner._SKIP_DIRS)

    def test_skip_dirs_includes_venv(self):
        self.assertIn(".venv", scanner._SKIP_DIRS)

    def test_scan_project_detects_nested_monorepo_manifests(self):
        with TemporaryDirectory() as tmp:
            workspace = run_gates.create_workspace("monorepo", base_dir=Path(tmp))
            profile = scanner.scan_project(str(workspace))

        self.assertIn("typescript", profile["languages"])
        self.assertIn("python", profile["languages"])
        self.assertIn("react", profile["frameworks"])
        self.assertIn("vite", profile["frameworks"])
        self.assertIn("fastapi", profile["frameworks"])
        self.assertIn("pnpm", profile["package_managers"])
        self.assertIn("apps/web/package.json", profile["manifests"])
        self.assertIn("services/api/pyproject.toml", profile["manifests"])
        self.assertIn("cursor-config", profile["signals"])

        components = profile["components"]
        web = next(item for item in components if item["path"] == "apps/web")
        api = next(item for item in components if item["path"] == "services/api")
        self.assertEqual(web["kind"], "node")
        self.assertIn("react", web["frameworks"])
        self.assertIn("vite", web["frameworks"])
        self.assertEqual(web["package_manager"], "pnpm")
        self.assertEqual(api["kind"], "python")
        self.assertIn("fastapi", api["frameworks"])

        commands = {(item["cwd"], item["command"]) for item in profile["suggested_commands"]}
        self.assertIn((".", "pnpm install"), commands)
        self.assertIn(("apps/web", "pnpm dev"), commands)
        self.assertIn(("apps/web", "pnpm build"), commands)
        self.assertIn(("services/api", "python -m uvicorn main:app --reload"), commands)

        readiness = profile["launch_readiness"]
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["blocking_issue_count"], 0)
        launch_order = [(item["cwd"], item["command"]) for item in readiness["launch_order"]]
        self.assertLess(
            launch_order.index(("services/api", "python -m uvicorn main:app --reload")),
            launch_order.index(("apps/web", "pnpm dev")),
        )

    def test_scan_project_suggests_commands_for_typescript_fixture(self):
        with TemporaryDirectory() as tmp:
            workspace = run_gates.create_workspace("typescript", base_dir=Path(tmp))
            profile = scanner.scan_project(str(workspace))

        self.assertEqual(len(profile["components"]), 1)
        component = profile["components"][0]
        self.assertEqual(component["path"], ".")
        self.assertEqual(component["kind"], "node")
        self.assertEqual(component["package_manager"], "pnpm")
        self.assertIn("next", component["frameworks"])
        commands = {(item["cwd"], item["command"]) for item in profile["suggested_commands"]}
        self.assertIn((".", "pnpm install"), commands)
        self.assertIn((".", "pnpm dev"), commands)
        self.assertIn((".", "pnpm build"), commands)
        self.assertEqual(profile["launch_readiness"]["status"], "ready")

    def test_launch_readiness_blocks_destructive_package_script(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "package.json").write_text(
                json.dumps(
                    {
                        "scripts": {"dev": "rm -rf ."},
                        "dependencies": {"vite": "^7.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            profile = scanner.scan_project(str(workspace))

        readiness = profile["launch_readiness"]
        self.assertEqual(readiness["status"], "blocked")
        self.assertGreater(readiness["blocking_issue_count"], 0)
        self.assertTrue(any("destructive pattern" in issue["message"] for issue in readiness["issues"]))

    def test_scan_project_redacts_surfaced_secret_values(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text(
                "Set INTERNAL_API_KEY=readme-secret-123 before running locally.\n",
                encoding="utf-8",
            )
            (workspace / "package.json").write_text(
                json.dumps(
                    {
                        "scripts": {"dev": "SERVICE_TOKEN=script-secret-456 vite"},
                        "dependencies": {"vite": "^7.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (workspace / ".env.local").write_text("DATABASE_PASSWORD=env-secret-789\n", encoding="utf-8")
            profile = scanner.scan_project(str(workspace))

        encoded = json.dumps(profile, sort_keys=True)
        self.assertNotIn("readme-secret-123", encoded)
        self.assertNotIn("script-secret-456", encoded)
        self.assertNotIn("env-secret-789", encoded)
        self.assertIn("INTERNAL_API_KEY=<redacted>", profile["readme_excerpt"])
        self.assertEqual(profile["security_posture"]["status"], "review")
        self.assertGreaterEqual(profile["security_posture"]["secret_file_count"], 1)
        self.assertGreaterEqual(profile["security_posture"]["redacted_value_count"], 2)


if __name__ == "__main__":
    unittest.main()
