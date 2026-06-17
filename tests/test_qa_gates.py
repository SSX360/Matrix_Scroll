import unittest
from pathlib import Path

from qa import run_gates


class QAGateHelperTests(unittest.TestCase):
    def test_fresh_workspace_name_is_isolated_from_neutral_stale_markers(self):
        workspace = run_gates.create_workspace("empty")
        try:
            low = str(workspace).lower()
            for marker in run_gates.FORBIDDEN_WORKSPACE_MARKERS:
                self.assertNotIn(marker, low)
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_python_fixture_contains_minimal_flask_project(self):
        workspace = run_gates.create_workspace("python")
        try:
            self.assertTrue((workspace / "requirements.txt").exists())
            self.assertTrue((workspace / "app.py").exists())
            self.assertIn("flask", (workspace / "requirements.txt").read_text(encoding="utf-8"))
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_typescript_fixture_contains_next_project(self):
        workspace = run_gates.create_workspace("typescript")
        try:
            self.assertTrue((workspace / "package.json").exists())
            self.assertTrue((workspace / "pnpm-lock.yaml").exists())
            self.assertTrue((workspace / "app" / "page.tsx").exists())
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_monorepo_fixture_contains_nested_manifests(self):
        workspace = run_gates.create_workspace("monorepo")
        try:
            self.assertTrue((workspace / "package.json").exists())
            self.assertTrue((workspace / "pnpm-workspace.yaml").exists())
            self.assertTrue((workspace / "apps" / "web" / "package.json").exists())
            self.assertTrue((workspace / "services" / "api" / "pyproject.toml").exists())
            self.assertTrue((workspace / ".cursor" / "rules" / "gtm.mdc").exists())
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_security_fixture_contains_secret_redaction_surface(self):
        workspace = run_gates.create_workspace("security")
        try:
            self.assertTrue((workspace / "package.json").exists())
            self.assertTrue((workspace / ".env.local").exists())
            self.assertIn(
                "readme-secret-123",
                (workspace / "README.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "script-secret-456",
                (workspace / "package.json").read_text(encoding="utf-8"),
            )
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_forbidden_workspace_reference_detector_is_case_insensitive(self):
        payload = {
            "workspace": (
                r"C:\Users\ryanj\Desktop"
                + "\\"
                + run_gates.FORBIDDEN_WORKSPACE_MARKERS[0].upper()
                + "\\"
                + run_gates.FORBIDDEN_WORKSPACE_MARKERS[1].upper()
            )
        }
        self.assertTrue(run_gates.contains_forbidden_workspace_reference(payload))
        self.assertFalse(run_gates.contains_forbidden_workspace_reference({"workspace": "fresh-project"}))

    def test_find_free_port_returns_available_integer(self):
        port = run_gates.find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)


if __name__ == "__main__":
    unittest.main()
