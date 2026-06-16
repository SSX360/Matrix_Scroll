import importlib
import os
import unittest
from unittest.mock import patch


class AppLaunchConfigTests(unittest.TestCase):
    def reload_app(self):
        import app

        return importlib.reload(app)

    def test_should_open_browser_defaults_true(self):
        with patch.dict(os.environ, {}, clear=True):
            app = self.reload_app()
            self.assertTrue(app.should_open_browser())

    def test_should_open_browser_respects_zero_false_no_off(self):
        for value in ("0", "false", "False", "no", "off"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPEN_BROWSER": value}, clear=True):
                    app = self.reload_app()
                    self.assertFalse(app.should_open_browser())

    def test_should_open_browser_accepts_one_true_yes_on(self):
        for value in ("1", "true", "yes", "on"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"OPEN_BROWSER": value}, clear=True):
                    app = self.reload_app()
                    self.assertTrue(app.should_open_browser())


if __name__ == "__main__":
    unittest.main()
