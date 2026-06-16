import unittest

import scanner


class ScannerTests(unittest.TestCase):
    def test_skip_dirs_includes_scratch(self):
        self.assertIn("scratch", scanner._SKIP_DIRS)

    def test_skip_dirs_includes_venv(self):
        self.assertIn(".venv", scanner._SKIP_DIRS)


if __name__ == "__main__":
    unittest.main()
