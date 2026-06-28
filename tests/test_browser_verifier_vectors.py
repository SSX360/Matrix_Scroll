import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIXSCROLL_ROOT = ROOT / "matrixscroll"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browser_canonical.mjs"


def _node_available() -> bool:
    return shutil.which("node") is not None


@unittest.skipUnless(MATRIXSCROLL_ROOT.exists(), "matrixscroll package not present")
class BrowserVerifierVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(MATRIXSCROLL_ROOT))
        from matrixscroll.canonical import canonical_bytes

        cls.canonical_bytes = staticmethod(canonical_bytes)

    @unittest.skipUnless(_node_available(), "node is not available")
    def test_browser_canonical_matches_python_vectors(self):
        vectors_dir = MATRIXSCROLL_ROOT / "vectors"
        for vector_path in sorted(vectors_dir.glob("*.json")):
            if vector_path.name.startswith("_"):
                continue
            manifest = json.loads(vector_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or "schema" not in manifest:
                continue
            python_bytes = self.canonical_bytes(manifest)
            completed = subprocess.run(
                ["node", str(SCRIPT), str(vector_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            browser_bytes = bytes.fromhex(completed.stdout.strip())
            self.assertEqual(
                browser_bytes,
                python_bytes,
                msg=f"canonical mismatch for {vector_path.name}",
            )


if __name__ == "__main__":
    unittest.main()
