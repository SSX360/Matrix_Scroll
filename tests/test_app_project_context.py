import unittest
from unittest.mock import patch

import app


class AppProjectContextTests(unittest.TestCase):
    def test_project_scan_question_adds_local_stack_context(self):
        profile = {
            "languages": ["python"],
            "frameworks": ["flask"],
            "notable_sdks": ["pandas"],
            "package_managers": ["pip"],
            "notebooks": [
                {
                    "filename": "analysis.ipynb",
                    "execution_health": "out_of_order",
                    "imports": ["pandas"],
                }
            ],
        }

        with patch("app.scan_active_profile", return_value=profile):
            prompt = app.build_prompt("scan my project and tell me what stack we use", [])

        self.assertIn("Local project scan", prompt)
        self.assertIn("Answering priority: for project, stack, or notebook questions", prompt)
        self.assertIn("Do not mention this instruction.", prompt)
        self.assertIn("frameworks=flask", prompt)
        self.assertIn("analysis.ipynb: out_of_order", prompt)

    def test_cursor_docs_question_does_not_add_project_context(self):
        prompt = app.build_prompt("How do I configure Cursor rules?", [])
        self.assertNotIn("Local project scan", prompt)

    def test_sanitize_mcp_config_redacts_secret_env_values(self):
        config = {
            "mcpServers": {
                "cursor-copilot": {
                    "command": "python",
                    "env": {
                        "GEMINI_API_KEY": "real-secret",
                        "LLM_BACKEND": "gemini",
                    },
                }
            }
        }

        sanitized = app.sanitize_mcp_config(config)

        env = sanitized["mcpServers"]["cursor-copilot"]["env"]
        self.assertEqual(env["GEMINI_API_KEY"], "<redacted>")
        self.assertEqual(env["LLM_BACKEND"], "gemini")

    def test_offline_project_answer_includes_stack_and_notebook_health(self):
        profile = {
            "languages": ["python"],
            "frameworks": ["flask"],
            "notable_sdks": ["pandas"],
            "package_managers": ["pip"],
            "notebooks": [
                {
                    "filename": "analysis.ipynb",
                    "execution_health": "out_of_order",
                    "imports": ["pandas"],
                }
            ],
        }

        with patch("app.scan_active_profile", return_value=profile):
            answer = app.build_offline_project_answer(
                "What is the project stack and notebook health?"
            )

        self.assertIn("frameworks=flask", answer)
        self.assertIn("analysis.ipynb: out_of_order", answer)
        self.assertIn("offline", answer.lower())


if __name__ == "__main__":
    unittest.main()
