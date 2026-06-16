import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import workspace_config as wc


class WorkspaceConfigTests(unittest.TestCase):
    def test_resolve_workspace_prefers_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"COPILOT_WORKSPACE": tmp}):
                ws, configured = wc.resolve_workspace()
            self.assertEqual(ws, Path(tmp).resolve())
            self.assertTrue(configured)

    def test_set_active_workspace_writes_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            pointer = Path(tmp) / "active.json"
            with patch.object(wc, "ACTIVE_POINTER", pointer):
                resolved = wc.set_active_workspace(tmp)
            self.assertEqual(resolved, Path(tmp).resolve())
            data = json.loads(pointer.read_text(encoding="utf-8"))
            self.assertEqual(data["workspace"], str(Path(tmp).resolve()))

    def test_load_config_merges_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            cfg_path = ws / ".cursor" / "co-pilot.json"
            cfg_path.parent.mkdir(parents=True)
            cfg_path.write_text(json.dumps({"vault": {"mode": "existing"}}), encoding="utf-8")
            cfg = wc.load_config(ws)
            self.assertEqual(cfg["vault"]["mode"], "existing")
            self.assertTrue(cfg["notebooks"]["enabled"])

    def test_scaffold_project_vault_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault_dir = wc.scaffold_project_vault(ws, "docs/vault")
            self.assertTrue((vault_dir / "README.md").exists())
            self.assertTrue((vault_dir / "project-context.md").exists())
            cfg = wc.load_config(ws)
            self.assertEqual(cfg["vault"]["mode"], "project")

    def test_resolve_vault_path_existing_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = wc.load_config(Path(tmp))
            cfg["vault"]["mode"] = "existing"
            cfg["vault"]["path"] = tmp
            path = wc.resolve_vault_path(Path(tmp), cfg)
            self.assertEqual(path, Path(tmp).resolve())


if __name__ == "__main__":
    unittest.main()
