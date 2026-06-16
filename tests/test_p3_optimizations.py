import unittest
from unittest.mock import patch

import app as app_module
import brainstorm as bs


class StatusCacheTests(unittest.TestCase):
    def setUp(self):
        app_module._clear_status_cache()
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module._clear_status_cache()

    @patch.object(app_module, "scan_active_profile")
    @patch.object(app_module.wc, "workspace_status")
    @patch.object(app_module, "list_project_rules")
    @patch.object(app_module, "get_workspace")
    def test_project_status_uses_cache(self, mock_ws, mock_rules, mock_status, mock_scan):
        from pathlib import Path
        mock_ws.return_value = (Path("/proj"), {})
        mock_scan.return_value = {"languages": ["python"]}
        mock_status.return_value = {"configured": True}
        mock_rules.return_value = []

        r1 = self.client.get("/api/project/status")
        r2 = self.client.get("/api/project/status")
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.get_json().get("cached"))
        self.assertTrue(r2.get_json().get("cached"))
        mock_scan.assert_called_once()

    @patch.object(app_module, "scan_active_profile")
    @patch.object(app_module.wc, "workspace_status")
    @patch.object(app_module, "list_project_rules")
    @patch.object(app_module, "get_workspace")
    def test_project_status_refresh_bypasses_cache(self, mock_ws, mock_rules, mock_status, mock_scan):
        from pathlib import Path
        mock_ws.return_value = (Path("/proj"), {})
        mock_scan.return_value = {"languages": ["python"]}
        mock_status.return_value = {"configured": True}
        mock_rules.return_value = []

        self.client.get("/api/project/status")
        r = self.client.get("/api/project/status?refresh=1")
        self.assertFalse(r.get_json().get("cached"))
        self.assertEqual(mock_scan.call_count, 2)


class BrainstormAsyncTests(unittest.TestCase):
    @patch.object(bs, "start_enhancement_job", return_value="job123")
    @patch.object(bs, "gather_context")
    def test_brainstorm_async_returns_job_id(self, mock_gather, mock_start):
        mock_gather.return_value = {
            "workspace": "/proj",
            "configured": True,
            "profile": {"languages": ["python"]},
            "rules": [],
            "mcp_hits": [],
            "config": {"brainstorm": {"enabled": True, "prefer_llm_enhancement": True, "max_suggestions": 6}},
        }
        with patch.object(bs.llm, "active_backend", return_value="ollama"):
            result = bs.brainstorm(limit=3, llm_generate=lambda *a, **k: "x", async_enhance=True)
        self.assertEqual(result["enhancement_job_id"], "job123")
        self.assertFalse(result["llm_enhanced"])
        mock_start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
