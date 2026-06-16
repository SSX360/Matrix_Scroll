import unittest
from unittest.mock import patch

import llm


class LLMErrorReportingTests(unittest.TestCase):
    def test_generate_error_includes_all_failed_backends(self):
        def fail_backend(backend, *_args, **_kwargs):
            if backend == "gemini":
                raise RuntimeError("429 RESOURCE_EXHAUSTED credits depleted")
            raise RuntimeError("ollama connection refused")

        with patch("llm._backend_chain", return_value=["gemini", "ollama"]):
            with patch("llm._usable", return_value=True):
                with patch("llm._generate_one", side_effect=fail_backend):
                    with self.assertRaises(llm.LLMError) as ctx:
                        llm.generate("system", [{"role": "user", "content": "hello"}])

        message = str(ctx.exception)
        self.assertIn("gemini: 429 RESOURCE_EXHAUSTED credits depleted", message)
        self.assertIn("ollama: ollama connection refused", message)

    def test_stream_error_includes_all_failed_backends(self):
        def fail_backend(backend, *_args, **_kwargs):
            if backend == "gemini":
                raise RuntimeError("429 RESOURCE_EXHAUSTED credits depleted")
            raise RuntimeError("ollama connection refused")

        with patch("llm._backend_chain", return_value=["gemini", "ollama"]):
            with patch("llm._usable", return_value=True):
                with patch("llm._stream_one", side_effect=fail_backend):
                    with self.assertRaises(llm.LLMError) as ctx:
                        list(llm.stream("system", [{"role": "user", "content": "hello"}]))

        message = str(ctx.exception)
        self.assertIn("gemini: 429 RESOURCE_EXHAUSTED credits depleted", message)
        self.assertIn("ollama: ollama connection refused", message)


if __name__ == "__main__":
    unittest.main()
