"""
Authority cert issuer + conformance-vector generator. Signs with the AUTHORITY key,
reusing the matrixscroll reference impl so certs are byte-conformant to SPEC §4-6.
Run as a small HTTP service OR call from the Node enroll endpoint. Keep the
Authority PRIVATE seed in a KMS/HSM — NEVER in code, env files, or the repo.
"""
from __future__ import annotations
import json, os, sys, base64, hashlib
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add matrixscroll-repo to python path so it resolves the local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../matrixscroll-repo")))
import matrixscroll

PLAN_DAYS = {"basic": 30, "team": 30, "enterprise": 365}


def _device_id(pub_b64: str) -> str:
    d = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest().upper()
    return f"MS-{d[0:4]}-{d[4:8]}"


def issue_certificate(*, subject_public_key: str, display_name: str,
                      verified_accounts: list[dict], plan: str) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    exp = now + timedelta(days=PLAN_DAYS.get(plan, 30))
    auth = matrixscroll.status()
    cert = {
        "schema": "matrixscroll.identity_certificate.v1",
        "subject": {
            "public_key": subject_public_key,
            "device_id": _device_id(subject_public_key),
            "display_name": display_name,
            "verified_accounts": verified_accounts,
            "plan": plan,
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "issuer": {
            "authority": "matrixscroll-authority-v1",
            "public_key": auth["public_key"],
            "device_id": auth["device_id"],
        },
    }
    signed = matrixscroll.sign_manifest(cert)
    assert matrixscroll.verify_manifest(signed), "self-check failed"
    return signed


def publish(cert: dict, out_dir: str = "id") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{cert['subject']['device_id']}.json")
    with open(path, "w") as f:
        json.dump(cert, f, indent=2)
    return path


def write_trust_root(out_dir: str = ".well-known") -> str:
    os.makedirs(out_dir, exist_ok=True)
    auth = matrixscroll.status()
    root = {
        "schema": "matrixscroll.trust_root.v1",
        "authority": "matrixscroll-authority-v1",
        "keys": [{"public_key": auth["public_key"], "device_id": auth["device_id"],
                  "valid_from": "2026-07-01T00:00:00Z", "valid_to": "2027-07-01T00:00:00Z"}],
    }
    path = os.path.join(out_dir, "matrixscroll-trust.json")
    with open(path, "w") as f:
        json.dump(root, f, indent=2)
    return path


class IssuerHTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/issue":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                req = json.loads(post_data.decode('utf-8'))
                cert = issue_certificate(
                    subject_public_key=req["subject_public_key"],
                    display_name=req["display_name"],
                    verified_accounts=req["verified_accounts"],
                    plan=req["plan"]
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"certificate": cert}).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Run HTTP issuer service")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    if args.server:
        server = HTTPServer(('localhost', args.port), IssuerHTTPHandler)
        print(f"Issuer HTTP server running on port {args.port}...")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    else:
        # Default behavior: generate vectors and trust root
        # Check if nacl is available
        try:
            import nacl.signing
            sk = nacl.signing.SigningKey.generate()
            subj_pub = base64.b64encode(bytes(sk.verify_key)).decode()
        except ImportError:
            # Fallback to dummy Ed25519 pubkey if pynacl is not installed
            print("pynacl not installed, generating vectors with fixed mock public key")
            subj_pub = "1111111111111111111111111111111111111111110="

        valid = issue_certificate(
            subject_public_key=subj_pub, display_name="Ryan James York",
            verified_accounts=[{"type": "github", "value": "ssx360", "method": "oauth"},
                               {"type": "email", "value": "ryan@matrixscroll.com", "method": "oauth"}],
            plan="basic")
        
        os.makedirs("vectors", exist_ok=True)
        with open("vectors/valid_identity_certificate.json", "w") as f:
            json.dump(valid, f, indent=2)
            
        tampered = json.loads(json.dumps(valid))
        tampered["subject"]["display_name"] = "Mallory"
        with open("vectors/tampered_identity_certificate.json", "w") as f:
            json.dump(tampered, f, indent=2)
            
        print("valid  ->", matrixscroll.verify_manifest(valid))     # True
        print("tamper ->", matrixscroll.verify_manifest(tampered))  # False
        
        write_trust_root()
        print("Conformance vectors and trust root successfully generated in vectors/ and public/")
