import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import chat_advisor as advisor


class ChatAdvisorDetectionTests(unittest.TestCase):
    def test_detects_weather_profit_prompt(self):
        q = (
            "Continue with all the next best steps to maximize profit from "
            "weather predictions for this codebase"
        )
        self.assertTrue(advisor.wants_project_advice(q))

    def test_excludes_pure_cursor_rules_faq(self):
        q = "How do I configure Cursor rules?"
        self.assertFalse(advisor.wants_project_advice(q))

    def test_detects_project_signal_alone(self):
        self.assertTrue(advisor.wants_project_advice("What should we do next for this project?"))

    def test_stack_plus_advice_verb(self):
        profile = {"frameworks": ["fastapi"], "languages": ["python"]}
        self.assertTrue(
            advisor.wants_project_advice("How should we structure fastapi routes?", profile)
        )


class ChatAdvisorContextTests(unittest.TestCase):
    def test_includes_readme_excerpt(self):
        profile = {
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "readme_excerpt": "PROPHET v1.3 Kalshi weather max-aggression",
            "notable_sdks": [],
            "package_managers": [],
        }
        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            ctx = advisor.build_advisor_context(
                "maximize profit from weather",
                ws,
                profile,
                {"brainstorm": {"include_vault_context": False}},
            )
        self.assertIn("README excerpt", ctx)
        self.assertIn("Kalshi weather", ctx)

    @patch("chat_advisor.vault.search_vault")
    def test_vault_search_uses_user_question(self, mock_search):
        mock_search.return_value = [{"doc_title": "Strategy", "text": "Kelly sizing notes"}]
        profile = {"languages": ["python"], "frameworks": [], "notable_sdks": [], "package_managers": []}
        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault_dir = ws / "docs" / "vault"
            vault_dir.mkdir(parents=True)
            config = {
                "vault": {"mode": "project", "project_subdir": "docs/vault"},
                "brainstorm": {"include_vault_context": True},
            }
            with patch("chat_advisor.wc.resolve_vault_path", return_value=vault_dir):
                advisor.build_advisor_context(
                    "maximize profit from weather predictions",
                    ws,
                    profile,
                    config,
                )
        mock_search.assert_called_once()
        self.assertIn("weather", mock_search.call_args[0][0].lower())


class ChatAdvisorPromptTests(unittest.TestCase):
    def test_build_advisor_prompt_includes_question(self):
        prompt = advisor.build_advisor_prompt(
            "next steps?",
            "=== Stack scan ===\npython",
            [],
        )
        self.assertIn("next steps?", prompt)
        self.assertIn("actionable steps", prompt.lower())


if __name__ == "__main__":
    unittest.main()
