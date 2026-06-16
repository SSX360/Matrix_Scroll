import unittest
from unittest.mock import patch

import llm


class LLMTests(unittest.TestCase):
    def test_backend_chain_puts_preferred_first(self):
        with patch.object(llm, "_PREFERRED", "gemini"):
            chain = llm._backend_chain()
            self.assertEqual(chain[0], "gemini")

    def test_active_backend_prefers_usable_gemini(self):
        with patch.object(llm, "_backend_chain", return_value=["gemini", "ollama"]), patch.object(
            llm, "_usable", side_effect=lambda b: b == "gemini"
        ):
            self.assertEqual(llm.active_backend(), "gemini")

    def test_ollama_options_includes_num_predict(self):
        opts = llm._ollama_options(0.7)
        self.assertIn("num_predict", opts)
        self.assertEqual(opts["num_predict"], llm.OLLAMA_NUM_PREDICT)
        self.assertEqual(opts["temperature"], 0.7)

    @patch("llm.requests.post")
    def test_ollama_generate_sends_num_predict(self, mock_post):
        mock_resp = unittest.mock.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "hi"}}
        mock_post.return_value = mock_resp

        result = llm._ollama_generate("sys", [{"role": "user", "content": "hi"}], 0.2)
        self.assertEqual(result, "hi")
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("num_predict", payload["options"])


if __name__ == "__main__":
    unittest.main()
