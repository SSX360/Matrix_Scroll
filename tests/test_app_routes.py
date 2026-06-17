import json
import os
import unittest
from unittest.mock import patch

import app as app_module


class AppRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_health_returns_llm_status(self):
        with patch.object(app_module, "get_index") as mock_index:
            mock_index.return_value = type("Idx", (), {"N": 42})()
            resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("llm", data)
        self.assertIn("active", data["llm"])
        self.assertEqual(data["chunks"], 42)

    def test_workspace_status(self):
        resp = self.client.get("/api/workspace/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("workspace", data)
        self.assertIn("configured", data)

    def test_diagnostics_returns_redacted_support_bundle(self):
        with (
            patch.object(app_module, "get_index") as mock_index,
            patch.dict(
                os.environ,
                {
                    "ANTHROPIC_API_KEY": "anthropic-real-secret",
                    "GEMINI_API_KEY": "gemini-real-secret",
                    "LLM_BACKEND": "ollama",
                },
            ),
        ):
            mock_index.return_value = type("Idx", (), {"N": 42})()
            resp = self.client.get("/api/diagnostics")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        encoded = json.dumps(data)
        self.assertEqual(data["product"], "Digital Rain")
        self.assertEqual(data["diagnostics_version"], 1)
        self.assertEqual(data["app"]["chunks"], 42)
        self.assertIn("workspace", data)
        self.assertIn("llm", data)
        self.assertIs(data["redaction"]["secrets_redacted"], True)
        self.assertEqual(data["environment"]["ANTHROPIC_API_KEY"], "<redacted:set>")
        self.assertEqual(data["environment"]["GEMINI_API_KEY"], "<redacted:set>")
        self.assertNotIn("anthropic-real-secret", encoded)
        self.assertNotIn("gemini-real-secret", encoded)

    def test_redact_diagnostics_recurses(self):
        payload = {
            "safe": "keep",
            "nested": {
                "api_key": "secret",
                "items": [{"password": "pw", "label": "visible"}],
            },
            "token": "",
            "secret_status": "<unset>",
            "redaction": {"secrets_redacted": True},
        }

        redacted = app_module.redact_diagnostics(payload)

        self.assertEqual(redacted["safe"], "keep")
        self.assertEqual(redacted["nested"]["api_key"], "<redacted:set>")
        self.assertEqual(redacted["nested"]["items"][0]["password"], "<redacted:set>")
        self.assertEqual(redacted["nested"]["items"][0]["label"], "visible")
        self.assertEqual(redacted["token"], "<unset>")
        self.assertEqual(redacted["secret_status"], "<unset>")
        self.assertIs(redacted["redaction"]["secrets_redacted"], True)

    def test_workspace_config_includes_configured_flag(self):
        resp = self.client.get("/api/workspace/config")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("configured", data)
        self.assertIn("config", data)

    @patch("brainstorm.brainstorm")
    def test_brainstorm_route(self, mock_brainstorm):
        mock_brainstorm.return_value = {
            "workspace": "/proj",
            "configured": True,
            "context_summary": "python",
            "suggestions": [{"title": "A", "prompt": "p", "tag": "t", "category": "x", "source": "offline"}],
            "llm_enhanced": False,
        }
        resp = self.client.get("/api/brainstorm?limit=3")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["llm_enhanced"])
        self.assertEqual(len(data["suggestions"]), 1)

    def test_vault_status(self):
        resp = self.client.get("/api/vault/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("mode", data)
        self.assertIn("path", data)


if __name__ == "__main__":
    unittest.main()
