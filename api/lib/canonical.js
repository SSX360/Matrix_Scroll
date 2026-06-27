const crypto = require("crypto");

function deepSort(v) {
  if (Array.isArray(v)) return v.map(deepSort);
  if (v && typeof v === "object") {
    const out = {};
    for (const k of Object.keys(v).sort()) out[k] = deepSort(v[k]);
    return out;
  }
  if (typeof v === "number" && !Number.isFinite(v)) throw new Error("NaN/Infinity not allowed (§4.5)");
  return v;
}

function asciiEscape(s) {
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    out += c >= 0x80 ? "\\u" + c.toString(16).padStart(4, "0") : s[i];
  }
  return out;
}

function canonicalBytes(manifest) {
  const { signature, ...body } = manifest;
  const escaped = asciiEscape(JSON.stringify(deepSort(body)));
  return Buffer.from(escaped, "utf8");
}

function verifyManifest(manifest) {
  const block = manifest && manifest.signature;
  if (!block || typeof block !== "object" || block.algorithm !== "ed25519") return false;
  let pub, sig;
  try {
    pub = Buffer.from(block.public_key, "base64");
    sig = Buffer.from(block.value, "base64");
  } catch (err) {
    return false;
  }
  if (pub.length !== 32 || sig.length !== 64) return false;
  
  // Verify device_id (SPEC §3)
  const dg = crypto.createHash("sha256").update(pub).digest("hex").toUpperCase();
  if (block.device_id !== `MS-${dg.slice(0, 4)}-${dg.slice(4, 8)}`) return false;
  
  try {
    // Construct standard SPKI DER encoding for Ed25519 public key
    const der = Buffer.concat([
      Buffer.from("302a300506032b6570032100", "hex"),
      pub
    ]);
    const publicKeyObj = crypto.createPublicKey({
      key: der,
      format: "der",
      type: "spki"
    });
    return crypto.verify(
      null,
      canonicalBytes(manifest),
      publicKeyObj,
      sig
    );
  } catch (e) {
    console.error("[CANONICAL] Cryptographic verification failed:", e.message);
    return false;
  }
}

function deviceIdFromPub(pubB64) {
  const pub = Buffer.from(pubB64, "base64");
  const dg = crypto.createHash("sha256").update(pub).digest("hex").toUpperCase();
  return `MS-${dg.slice(0, 4)}-${dg.slice(4, 8)}`;
}

module.exports = { canonicalBytes, verifyManifest, deviceIdFromPub, deepSort, asciiEscape };
