import unittest
from unittest.mock import patch

import brainstorm as bs


class BrainstormTests(unittest.TestCase):
    def test_suggest_offline_notebook_health(self):
        context = {
            "workspace": "/proj",
            "configured": True,
            "profile": {
                "languages": ["python"],
                "frameworks": ["flask"],
                "notebooks": [
                    {"filename": "train.ipynb", "execution_health": "out_of_order"},
                ],
            },
            "rules": [{"filename": "x.mdc"}],
            "mcp_hits": [],
            "config": {"vault": {"mode": "project", "project_subdir": "docs/vault"}},
        }
        with patch.object(bs.wc, "resolve_vault_path", return_value=None):
            items = bs.suggest_offline(context, limit=6)
        titles = " ".join(i.title for i in items)
        self.assertIn("train.ipynb", titles)

    def test_suggest_offline_unconfigured_workspace(self):
        context = {
            "workspace": "/install",
            "configured": False,
            "profile": {},
            "rules": [],
            "mcp_hits": [],
            "config": {"vault": {"mode": "project"}},
        }
        with patch.object(bs.wc, "resolve_vault_path", return_value=None):
            items = bs.suggest_offline(context, limit=3)
        self.assertTrue(any(i.category == "workspace" for i in items))

    def test_suggest_offline_missing_rules(self):
        context = {
            "workspace": "/proj",
            "configured": True,
            "profile": {"languages": ["python"], "frameworks": ["flask"]},
            "rules": [],
            "mcp_hits": [],
            "config": {"vault": {"mode": "existing", "path": "/vault"}},
        }
        with patch.object(bs.wc, "resolve_vault_path", return_value=__import__("pathlib").Path("/vault")):
            items = bs.suggest_offline(context, limit=6)
        self.assertTrue(any("rule" in i.title.lower() for i in items))

    @patch.object(bs, "_llm_enhancement_allowed", return_value=False)
    def test_brainstorm_skips_llm_when_ollama_active(self, _allowed):
        generate = unittest.mock.Mock(return_value="Title | Prompt | Tag")
        with patch.object(bs, "gather_context", return_value={
            "workspace": "/proj",
            "configured": True,
            "profile": {"languages": ["python"], "frameworks": ["flask"]},
            "rules": [],
            "mcp_hits": [],
            "config": {"brainstorm": {"enabled": True, "max_suggestions": 6, "prefer_llm_enhancement": True}},
        }):
            result = bs.brainstorm(limit=3, llm_generate=generate)
        generate.assert_not_called()
        self.assertFalse(result["llm_enhanced"])
        self.assertTrue(len(result["suggestions"]) > 0)

    def test_brainstorm_disabled_returns_empty(self):
        with patch.object(bs, "gather_context", return_value={
            "workspace": "/proj",
            "configured": True,
            "profile": {},
            "rules": [],
            "mcp_hits": [],
            "config": {"brainstorm": {"enabled": False}},
        }):
            result = bs.brainstorm(limit=3)
        self.assertEqual(result["suggestions"], [])
        self.assertTrue(result.get("disabled"))


if __name__ == "__main__":
    unittest.main()
