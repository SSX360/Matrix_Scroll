import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import chat_actions as actions


class ChatActionDetectionTests(unittest.TestCase):
    def test_detects_generate_cursor_rules_request(self):
        q = (
            "Generate a `.cursor/rules` file for fastapi conventions in this "
            "codebase based on what you detect in the project scan."
        )
        action = actions.detect_chat_action(q)
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], "create_rule")

    def test_detects_install_mcp_request(self):
        action = actions.detect_chat_action("install the postgres mcp server")
        self.assertIsNotNone(action)
        self.assertEqual(action["type"], "install_mcp")
        self.assertEqual(action["name"], "postgres")

    def test_docs_question_is_not_an_action(self):
        action = actions.detect_chat_action("How do I configure Cursor rules?")
        self.assertIsNone(action)


class ChatActionInferenceTests(unittest.TestCase):
    def test_infers_fastapi_rule_name(self):
        profile = {"frameworks": ["fastapi"], "languages": ["python"]}
        name = actions.infer_rule_name(
            "Generate a .cursor/rules file for fastapi conventions", profile
        )
        self.assertEqual(name, "fastapi-conventions")

    def test_infers_python_globs(self):
        profile = {"languages": ["python"], "frameworks": ["fastapi"]}
        globs = actions.infer_rule_globs("fastapi rules", profile)
        self.assertEqual(globs, "**/*.py")


class ChatActionExecutionTests(unittest.TestCase):
    def test_writes_rule_file_to_workspace(self):
        profile = {
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "notable_sdks": ["pandas"],
            "package_managers": ["uv"],
            "path": "/tmp/proj",
        }
        question = "Generate a .cursor/rules file for fastapi conventions"

        with TemporaryDirectory() as tmp:
            ws = Path(tmp)
            with patch.object(actions, "generate_rule_body", return_value="- Use APIRouter\n- Type hints required"):
                message, meta = actions.write_project_rule(
                    ws,
                    question,
                    profile,
                    search_docs=lambda q, k: [],
                )

            rule_path = ws / ".cursor" / "rules" / "fastapi-conventions.mdc"
            self.assertTrue(rule_path.exists())
            self.assertIn("fastapi-conventions", meta["relative_path"])
            self.assertIn("Created", message)
            self.assertIn("APIRouter", rule_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
