import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import Mock, patch

import desktop_launcher


class DesktopLauncherTests(unittest.TestCase):
    def test_load_mcp_env_returns_cursor_copilot_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "mcp.json"
            config_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "cursor-copilot": {
                            "env": {
                                "GEMINI_API_KEY": "secret",
                                "LLM_BACKEND": "gemini",
                                "GEMINI_MODEL": "gemini-2.5-flash",
                            }
                        }
                    }
                }),
                encoding="utf-8",
            )

            env = desktop_launcher.load_mcp_env(config_path)

        self.assertEqual(env["GEMINI_API_KEY"], "secret")
        self.assertEqual(env["LLM_BACKEND"], "gemini")
        self.assertEqual(env["GEMINI_MODEL"], "gemini-2.5-flash")

    def test_load_mcp_env_resolves_env_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "mcp.json"
            config_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "cursor-copilot": {
                            "env": {
                                "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
                                "LLM_BACKEND": "ollama",
                                "COPILOT_WORKSPACE": "${workspaceFolder}",
                            }
                        }
                    }
                }),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "real-secret"}, clear=False):
                env = desktop_launcher.load_mcp_env(config_path)
            self.assertEqual(env["GEMINI_API_KEY"], "real-secret")
            self.assertEqual(env["LLM_BACKEND"], "ollama")
            self.assertNotIn("COPILOT_WORKSPACE", env)

    def test_load_mcp_env_skips_unset_env_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "mcp.json"
            config_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "cursor-copilot": {
                            "env": {"GEMINI_API_KEY": "${env:MISSING_VAR}"}
                        }
                    }
                }),
                encoding="utf-8",
            )
            env = desktop_launcher.load_mcp_env(config_path)
            self.assertNotIn("GEMINI_API_KEY", env)

    def test_load_mcp_env_returns_empty_dict_for_missing_file(self):
        env = desktop_launcher.load_mcp_env(Path("missing-mcp.json"))
        self.assertEqual(env, {})

    def test_is_backend_healthy_true_on_200(self):
        response = Mock()
        response.status = 200
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("desktop_launcher.request.urlopen", return_value=response):
            self.assertTrue(desktop_launcher.is_backend_healthy("http://127.0.0.1:59712/api/health"))

    def test_is_backend_healthy_false_on_exception(self):
        with patch("desktop_launcher.request.urlopen", side_effect=OSError("offline")):
            self.assertFalse(desktop_launcher.is_backend_healthy("http://127.0.0.1:59712/api/health"))

    def test_build_backend_env_forces_port_and_browser_flag(self):
        env = desktop_launcher.build_backend_env({"LLM_BACKEND": "gemini"}, port=59712)
        self.assertEqual(env["PORT"], "59712")
        self.assertEqual(env["OPEN_BROWSER"], "0")
        self.assertEqual(env["LLM_BACKEND"], "gemini")

    def test_build_backend_env_injects_active_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            with mock.patch("workspace_config.get_active_workspace_raw", return_value=ws):
                env = desktop_launcher.build_backend_env({}, port=59712)
            self.assertEqual(env["COPILOT_WORKSPACE"], str(ws))

    def test_is_companion_running_true_when_lock_taken(self):
        with patch("desktop_launcher.socket.socket") as socket_cls:
            sock = Mock()
            sock.bind.side_effect = OSError("address already in use")
            socket_cls.return_value = sock
            self.assertTrue(desktop_launcher.is_companion_running())

    def test_is_companion_running_false_when_lock_free(self):
        with patch("desktop_launcher.socket.socket") as socket_cls:
            sock = Mock()
            socket_cls.return_value = sock
            self.assertFalse(desktop_launcher.is_companion_running())
            sock.bind.assert_called_once_with(("127.0.0.1", desktop_launcher.COMPANION_LOCK_PORT))

    def test_wait_for_backend_returns_actionable_message_when_port_busy(self):
        with patch("desktop_launcher.is_backend_healthy", return_value=False), patch(
            "desktop_launcher.is_port_in_use", return_value=True
        ):
            healthy, detail = desktop_launcher.wait_for_backend(
                "http://127.0.0.1:59712/api/health",
                timeout_seconds=0,
            )
        self.assertFalse(healthy)
        self.assertIn("Port 59712 is in use", detail)

    @patch("desktop_launcher.start_companion")
    @patch("desktop_launcher.is_companion_running", return_value=True)
    @patch("desktop_launcher.is_backend_healthy", return_value=True)
    def test_main_skips_companion_when_already_running(self, _healthy, _companion, start_companion):
        code = desktop_launcher.main()
        self.assertEqual(code, 0)
        start_companion.assert_not_called()

    @patch("desktop_launcher.start_backend")
    @patch("desktop_launcher.is_port_in_use", return_value=True)
    @patch("desktop_launcher.is_backend_healthy", return_value=False)
    def test_main_refuses_duplicate_backend_when_port_busy(self, _healthy, _port, start_backend):
        code = desktop_launcher.main()
        self.assertEqual(code, 1)
        start_backend.assert_not_called()


if __name__ == "__main__":
    unittest.main()
