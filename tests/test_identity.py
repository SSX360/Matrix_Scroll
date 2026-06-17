import os
import stat
import tempfile
import unittest
from pathlib import Path

import identity
from identity import EmulatedProvider, IdentityError


def _provider(directory: Path) -> EmulatedProvider:
    return EmulatedProvider.load_or_create(directory)


class IdentityPersistenceTests(unittest.TestCase):
    def test_same_device_id_recovered_across_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            first = identity.identity_info(_provider(d))
            second = identity.identity_info(_provider(d))
            self.assertEqual(first["device_id"], second["device_id"])
            self.assertEqual(first["public_key"], second["public_key"])

    def test_device_id_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = identity.identity_info(_provider(Path(tmp)))
            self.assertRegex(info["device_id"], r"^MS-[0-9A-F]{4}-[0-9A-F]{4}$")

    def test_identity_info_excludes_private_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = identity.identity_info(_provider(Path(tmp)))
            self.assertNotIn("private_key", info)


class CryptoIntegrityTests(unittest.TestCase):
    def test_sign_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _provider(Path(tmp))
            pub = identity.public_key_b64(p)
            sig = identity.sign(b"release-42", p)
            self.assertTrue(identity.verify(pub, b"release-42", sig))

    def test_verify_rejects_tampered_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _provider(Path(tmp))
            pub = identity.public_key_b64(p)
            sig = identity.sign(b"release-42", p)
            self.assertFalse(identity.verify(pub, b"release-43", sig))

    def test_verify_rejects_tampered_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _provider(Path(tmp))
            pub = identity.public_key_b64(p)
            sig = bytearray(identity.sign(b"data", p))
            sig[0] ^= 0x01
            self.assertFalse(identity.verify(pub, b"data", bytes(sig)))

    def test_verify_rejects_mismatched_public_key(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            signer = _provider(Path(a))
            other = identity.public_key_b64(_provider(Path(b)))
            sig = identity.sign(b"data", signer)
            self.assertFalse(identity.verify(other, b"data", sig))


class ManifestSigningTests(unittest.TestCase):
    def _nested_manifest(self) -> dict:
        return {
            "run_id": "r1",
            "meta": {"z": 1, "a": {"deep": [3, 2, 1]}},
            "kpis": [{"label": "rate", "actual": 66.7}],
        }

    def test_sign_and_verify_nested_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _provider(Path(tmp))
            signed = identity.sign_manifest(self._nested_manifest(), p)
            self.assertTrue(identity.verify_manifest(signed))

    def test_verify_detects_nested_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _provider(Path(tmp))
            signed = identity.sign_manifest(self._nested_manifest(), p)
            signed["meta"]["a"]["deep"][0] = 99
            self.assertFalse(identity.verify_manifest(signed))

    def test_verify_manifest_without_signature_block(self):
        self.assertFalse(identity.verify_manifest({"run_id": "r1"}))


class CanonicalTests(unittest.TestCase):
    def test_key_order_independent(self):
        a = identity._canonical({"b": 1, "a": {"y": 2, "x": 1}})
        b = identity._canonical({"a": {"x": 1, "y": 2}, "b": 1})
        self.assertEqual(a, b)

    def test_signature_block_excluded(self):
        base = {"run_id": "r1"}
        withsig = {"run_id": "r1", "signature": {"value": "abc"}}
        self.assertEqual(identity._canonical(base), identity._canonical(withsig))

    def test_unicode_is_ascii_escaped(self):
        out = identity._canonical({"name": "café"})
        self.assertEqual(out, b'{"name":"caf\\u00e9"}')

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            identity._canonical({"x": float("nan")})


class EdgeCaseTests(unittest.TestCase):
    def test_corrupted_key_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / identity.DEVICE_FILE
            path.write_text("{ not valid json", encoding="utf-8")
            with self.assertRaises(IdentityError):
                EmulatedProvider.load_or_create(Path(tmp))

    def test_invalid_seed_length_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / identity.DEVICE_FILE
            path.write_text('{"private_key": "QUJD"}', encoding="utf-8")
            with self.assertRaises(IdentityError):
                EmulatedProvider.load_or_create(Path(tmp))

    def test_unwritable_home_raises_oserror(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "blocker"
            blocker.write_text("x", encoding="utf-8")
            with self.assertRaises(OSError):
                EmulatedProvider.load_or_create(blocker / "sub")

    @unittest.skipIf(os.name == "nt", "POSIX file modes not enforced on Windows")
    def test_private_key_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            _provider(Path(tmp))
            path = Path(tmp) / identity.DEVICE_FILE
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
