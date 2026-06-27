#!/usr/bin/env python3
"""
verify_live.py — the single most important check before calling the Authority "live".

It catches the FATAL, silent failure mode: a certificate that is internally
self-consistent (verify_manifest == True) but is NOT signed by the published
Authority root. If your verifier only calls verify_manifest(cert), then ANY key
can mint a cert that shows a green "Verified identity: Mallory" badge. The badge
must mean "signed by the Authority root" — which means comparing the cert's
signing key to the PUBLISHED trust root, not just that the cert verifies.

This script proves three things at once:
  1. The published trust root is reachable and well-formed.
  2. A real, issued cert from the public directory verifies cryptographically.
  3. The cert's signing key == the published Authority root key (the chain).
     <-- this is the step a naive verifier skips.

Usage:
  pip install "matrixscroll>=0.3.0"
  python verify_live.py MS-XXXX-XXXX            # a device_id you actually claimed
  # or point at staging:
  BASE=https://your-preview.vercel.app python verify_live.py MS-XXXX-XXXX
"""
import os, sys, json, base64, hashlib, urllib.request
import matrixscroll

BASE = os.environ.get("BASE", "https://id.matrixscroll.com")
TRUST_URL = f"{BASE}/.well-known/matrixscroll-trust.json"


def fetch(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def device_id_of(pub_b64):
    d = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest().upper()
    return f"MS-{d[0:4]}-{d[4:8]}"


def main(device_id):
    ok = True

    # 1. trust root
    root = fetch(TRUST_URL)
    root_keys = {k["public_key"] for k in root.get("keys", [])}
    if not root_keys:
        print("FAIL: trust root has no keys"); return 1
    print(f"[1] trust root OK — {len(root_keys)} authority key(s)")

    # 2. fetch the issued cert
    cert = fetch(f"{BASE}/id/{device_id}.json")

    # 3a. cryptographic self-consistency (what a naive verifier checks)
    if not matrixscroll.verify_manifest(cert):
        print("FAIL: cert signature invalid"); return 1
    print("[2] cert signature verifies cryptographically")

    # 3b. THE CHAIN CHECK — is it signed by the PUBLISHED Authority root?
    signer = cert["signature"]["public_key"]
    if signer not in root_keys:
        print("FAIL: cert is signed by a key NOT in the published trust root.")
        print("      -> signer:", signer)
        print("      -> roots :", root_keys)
        print("      This is the fatal mismatch: real certs won't chain, OR a")
        print("      forged cert would still pass a naive verifier. The signing")
        print("      key (complete.js / issuer) MUST equal the key whose public")
        print("      half is in matrixscroll-trust.json.")
        ok = False
    else:
        print("[3] cert chains to the published Authority root ✓")

    # 4. issuer.public_key must agree with the signature key and the root
    issuer_pub = cert.get("issuer", {}).get("public_key")
    if issuer_pub != signer:
        print("WARN: issuer.public_key != signature.public_key"); ok = False

    # 5. subject device_id must derive from subject public_key (SPEC §3)
    sub = cert["subject"]
    if device_id_of(sub["public_key"]) != sub["device_id"]:
        print("FAIL: subject device_id does not derive from subject public_key"); ok = False
    else:
        print("[4] subject device_id derives correctly from its public key ✓")

    print("\nRESULT:", "LIVE-READY ✓" if ok else "NOT READY — fix the chain above ✗")
    print(f"  subject : {sub['display_name']}  ({sub['plan']}, expires {sub['expires_at']})")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python verify_live.py MS-XXXX-XXXX"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
