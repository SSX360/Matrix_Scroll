import os
import tempfile
import unittest
from pathlib import Path

import mcp_server


class MCPServerTests(unittest.TestCase):
    def test_mcp_tool_count(self):
        source = (Path(__file__).resolve().parent.parent / "mcp_server.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("@mcp.tool()"), 13)

    def test_default_project_path_uses_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.dict(os.environ, {"COPILOT_WORKSPACE": tmp}, clear=False):
                path = mcp_server._default_project_path()
                self.assertEqual(Path(path), Path(tmp).resolve())


if __name__ == "__main__":
    unittest.main()
