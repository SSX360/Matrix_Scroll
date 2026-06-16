import unittest
import unittest.mock

import companion


class CompanionTests(unittest.TestCase):
    def test_chat_timeout_allows_long_ollama_reads(self):
        self.assertEqual(companion.CHAT_CONNECT_TIMEOUT, 5)
        self.assertEqual(companion.CHAT_READ_TIMEOUT, 300)
        self.assertEqual(companion.CHAT_TIMEOUT, (5, 300))

    def test_get_server_port_fallback(self):
        comp = companion.DesktopCompanion.__new__(companion.DesktopCompanion)
        with unittest.mock.patch.object(
            companion.Path, "exists", return_value=False
        ):
            port = comp.get_server_port()
        self.assertEqual(port, 59712)


if __name__ == "__main__":
    unittest.main()
