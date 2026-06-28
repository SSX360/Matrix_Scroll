const SAMPLE_COMMIT_ENVELOPE = `{
  "commit": {
    "author": {
      "date": "1740000000",
      "email": "contributor@matrixscroll.dev",
      "name": "Sample Contributor"
    },
    "committer": {
      "date": "1740000000",
      "email": "contributor@matrixscroll.dev",
      "name": "Sample Contributor"
    },
    "expected_id": "0000000000000000000000000000000000000000",
    "message": "feat: add commit envelope example\\n\\nSigned-by: matrixscroll",
    "parents": [],
    "tree": "0000000000000000000000000000000000000000"
  },
  "provenance": {
    "actor_type": "human",
    "tool": "git-cli",
    "tool_version": "2.43.0"
  },
  "repository": {
    "branch": "main",
    "name": "matrixscroll",
    "remote_url": "https://github.com/SSX360/matrixscroll"
  },
  "schema": "matrixscroll.commit_envelope.v1",
  "signature": {
    "algorithm": "ed25519",
    "device_id": "MS-4319-20D5",
    "mode": "emulated",
    "public_key": "bsVoWgUYK+NZNcSNIoWjO3IiTK/xT6U6mXFzBJgPUKc=",
    "schema": "matrixscroll.signature.v1",
    "signed_at": "2026-06-20T00:04:31Z",
    "value": "P/YGQsCEyFfWizauGvxFpJ71pk0JFvzgoMTRzEnLumtKIwac/H83eKNc5t4w9RJCudMZR6v24KCtsclB+uyTBQ=="
  }
}`;

const SAMPLE_RELEASE_MANIFEST = `{
  "artifact": "release-manifest.json",
  "commit": "demo-8f2a1b94",
  "evidence": {
    "agent": "codex",
    "policy": "ai-assisted-code",
    "verified_commands": [
      "matrixscroll verify release-manifest.json"
    ]
  },
  "files": [
    {
      "path": "index.html",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    },
    {
      "path": "spec/index.html",
      "sha256": "1111111111111111111111111111111111111111111111111111111111111111"
    }
  ],
  "generated_by": "matrixscroll fixture",
  "project": "matrixscroll-site",
  "schema": "matrixscroll.release_manifest.v1",
  "signature": {
    "algorithm": "ed25519",
    "device_id": "MS-EAB9-1217",
    "mode": "emulated",
    "public_key": "Vxee+i1db9bLRAY5cPJw7gFBCk2lHlpIFhaZUdY2n/8=",
    "schema": "matrixscroll.signature.v1",
    "signed_at": "2026-06-19T09:43:35Z",
    "value": "SQPMBxv3MvjlB0lN9SURLoqrQJ4IWzNd62fCOqwSu/fg2S3KCrZ2dsFcUNIkw4iiTwxFSryL7v+fdBpVW0ICCA=="
  }
}`;const SAMPLE_AGENT_PAYMENT = `{
  "agent_device_id": "MS-4319-20D5",
  "amount": 250.0,
  "currency": "USD",
  "merchant": "OpenAI",
  "payment_method": {
    "identifier_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "type": "virtual_card"
  },
  "schema": "matrixscroll.agent_payment.v1",
  "signature": {
    "algorithm": "ed25519",
    "device_id": "MS-4319-20D5",
    "mode": "emulated",
    "public_key": "bsVoWgUYK+NZNcSNIoWjO3IiTK/xT6U6mXFzBJgPUKc=",
    "schema": "matrixscroll.signature.v1",
    "signed_at": "2026-06-27T04:29:41Z",
    "value": "+dRjYqhW+Bf/1L7Ka0jZzOeS37Wj7iFqCdCnQvE6fK+9W50t9q5E1ZKQWZ5+tPnTarZtaxo/KYPBMCciLxLDDA=="
  },
  "timestamp": "2026-06-27T04:29:41Z",
  "transaction_id": "tx_ok12345"
}`;

class JsonParser {
  constructor(source) {
    this.source = source;
    this.index = 0;
  }

  parse() {
    const value = this.parseValue();
    this.skipWhitespace();
    if (this.index !== this.source.length) {
      this.fail("Unexpected trailing input");
    }
    return value;
  }

  skipWhitespace() {
    while (/[\t\n\r ]/.test(this.source[this.index] || "")) {
      this.index += 1;
    }
  }

  parseValue() {
    this.skipWhitespace();
    const char = this.source[this.index];
    if (char === "{") return this.parseObject();
    if (char === "[") return this.parseArray();
    if (char === "\"") return { type: "string", value: this.parseString() };
    if (char === "t" && this.take("true")) return { type: "literal", value: true };
    if (char === "f" && this.take("false")) return { type: "literal", value: false };
    if (char === "n" && this.take("null")) return { type: "literal", value: null };
    if (char === "-" || (char >= "0" && char <= "9")) return this.parseNumber();
    this.fail("Unexpected token");
  }

  take(text) {
    if (this.source.slice(this.index, this.index + text.length) === text) {
      this.index += text.length;
      return true;
    }
    return false;
  }

  parseObject() {
    this.expect("{");
    this.skipWhitespace();
    const map = new Map();
    if (this.source[this.index] === "}") {
      this.index += 1;
      return { type: "object", map };
    }
    while (true) {
      this.skipWhitespace();
      if (this.source[this.index] !== "\"") this.fail("Expected object key");
      const key = this.parseString();
      this.skipWhitespace();
      this.expect(":");
      const value = this.parseValue();
      map.set(key, value);
      this.skipWhitespace();
      const char = this.source[this.index];
      if (char === "}") {
        this.index += 1;
        return { type: "object", map };
      }
      this.expect(",");
    }
  }

  parseArray() {
    this.expect("[");
    this.skipWhitespace();
    const values = [];
    if (this.source[this.index] === "]") {
      this.index += 1;
      return { type: "array", values };
    }
    while (true) {
      values.push(this.parseValue());
      this.skipWhitespace();
      const char = this.source[this.index];
      if (char === "]") {
        this.index += 1;
        return { type: "array", values };
      }
      this.expect(",");
    }
  }

  parseString() {
    this.expect("\"");
    let value = "";
    while (this.index < this.source.length) {
      const char = this.source[this.index++];
      if (char === "\"") return value;
      if (char === "\\") {
        const escaped = this.source[this.index++];
        if (escaped === "\"" || escaped === "\\" || escaped === "/") value += escaped;
        else if (escaped === "b") value += "\b";
        else if (escaped === "f") value += "\f";
        else if (escaped === "n") value += "\n";
        else if (escaped === "r") value += "\r";
        else if (escaped === "t") value += "\t";
        else if (escaped === "u") {
          const hex = this.source.slice(this.index, this.index + 4);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) this.fail("Invalid unicode escape");
          value += String.fromCharCode(parseInt(hex, 16));
          this.index += 4;
        } else {
          this.fail("Invalid escape sequence");
        }
      } else {
        if (char < " ") this.fail("Unescaped control character");
        value += char;
      }
    }
    this.fail("Unterminated string");
  }

  parseNumber() {
    const rest = this.source.slice(this.index);
    const match = rest.match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (!match) this.fail("Invalid number");
    this.index += match[0].length;
    return { type: "number", raw: match[0] };
  }

  expect(char) {
    if (this.source[this.index] !== char) this.fail(`Expected ${char}`);
    this.index += 1;
  }

  fail(message) {
    throw new Error(`${message} at byte ${this.index}`);
  }
}

function compareStrings(a, b) {
  const ac = Array.from(a);
  const bc = Array.from(b);
  const len = Math.min(ac.length, bc.length);
  for (let i = 0; i < len; i += 1) {
    const av = ac[i].codePointAt(0);
    const bv = bc[i].codePointAt(0);
    if (av !== bv) return av - bv;
  }
  return ac.length - bc.length;
}

function hex4(value) {
  return value.toString(16).padStart(4, "0");
}

function stringifyPythonAscii(value) {
  let output = "\"";
  for (let i = 0; i < value.length; i += 1) {
    let code = value.codePointAt(i);
    if (code > 0xffff) i += 1;
    if (code === 0x22) output += "\\\"";
    else if (code === 0x5c) output += "\\\\";
    else if (code === 0x08) output += "\\b";
    else if (code === 0x0c) output += "\\f";
    else if (code === 0x0a) output += "\\n";
    else if (code === 0x0d) output += "\\r";
    else if (code === 0x09) output += "\\t";
    else if (code < 0x20) output += `\\u${hex4(code)}`;
    else if (code < 0x80) output += String.fromCodePoint(code);
    else if (code <= 0xffff) output += `\\u${hex4(code)}`;
    else {
      code -= 0x10000;
      output += `\\u${hex4(0xd800 + (code >> 10))}\\u${hex4(0xdc00 + (code & 0x3ff))}`;
    }
  }
  return `${output}"`;
}

function canonicalize(node, options = {}) {
  if (node.type === "string") return stringifyPythonAscii(node.value);
  if (node.type === "number") return node.raw;
  if (node.type === "literal") return node.value === null ? "null" : String(node.value);
  if (node.type === "array") return `[${node.values.map((value) => canonicalize(value)).join(",")}]`;
  if (node.type === "object") {
    const keys = Array.from(node.map.keys())
      .filter((key) => !(options.omitTopLevelSignature && key === "signature"))
      .sort(compareStrings);
    return `{${keys.map((key) => `${stringifyPythonAscii(key)}:${canonicalize(node.map.get(key))}`).join(",")}}`;
  }
  throw new Error("Unsupported JSON node");
}

function requireObject(node, name) {
  if (!node || node.type !== "object") throw new Error(`${name} must be a JSON object`);
  return node;
}

function getField(objectNode, key) {
  return objectNode.map.get(key);
}

function getStringField(objectNode, key) {
  const node = getField(objectNode, key);
  if (!node || node.type !== "string" || !node.value) {
    throw new Error(`signature.${key} is required`);
  }
  return node.value;
}

function base64ToBytes(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/").replace(/\s+/g, "");
  const binary = atob(normalized);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("").toUpperCase();
}

async function deriveDeviceId(publicKeyBytes) {
  const digest = await crypto.subtle.digest("SHA-256", publicKeyBytes);
  const hex = bytesToHex(new Uint8Array(digest));
  return `MS-${hex.slice(0, 4)}-${hex.slice(4, 8)}`;
}

async function verifyEd25519(publicKeyBytes, signatureBytes, canonicalBytes) {
  if (!window.crypto || !crypto.subtle) {
    throw new Error("Web Crypto is not available in this browser context");
  }
  const key = await crypto.subtle.importKey("raw", publicKeyBytes, "Ed25519", false, ["verify"]);
  return crypto.subtle.verify("Ed25519", key, signatureBytes, canonicalBytes);
}

function setResult(root, status, title, message, details = []) {
  const statusEl = root.querySelector("[data-result-status]");
  const titleEl = root.querySelector("[data-result-title]");
  const messageEl = root.querySelector("[data-result-message]");
  const listEl = root.querySelector("[data-result-list]");
  if (!statusEl || !titleEl || !messageEl || !listEl) return;
  statusEl.className = `result-status ${status}`;
  const container = statusEl.closest(".result-box");
  if (container) {
    container.className = `result-box ${status}`;
  }
  statusEl.textContent = status === "valid" ? "Valid" : status === "invalid" ? "Invalid" : "Waiting";
  titleEl.textContent = title;
  messageEl.textContent = message;
  listEl.innerHTML = "";
  for (const detail of details) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    const value = document.createElement("span");
    label.textContent = detail.label;
    value.innerHTML = detail.value || "-";
    item.append(label, value);
    listEl.appendChild(item);
  }
}

function getManifestValue(root) {
  const input = root.querySelector("[data-manifest-input]");
  if (input) return input.value.trim();
  const display = root.querySelector("[data-manifest-display]");
  return display ? display.textContent.trim() : "";
}

function setManifestValue(root, value) {
  const input = root.querySelector("[data-manifest-input]");
  const display = root.querySelector("[data-manifest-display]");
  if (input) input.value = value;
  if (display) display.textContent = value;
}

function resetResult(root) {
  setResult(
    root,
    "waiting",
    root.dataset.emptyTitle || "No document checked yet.",
    root.dataset.emptyMessage || "Load a sample or paste signed JSON to verify it locally."
  );
}

function describeManifest(rootNode) {
  const schemaNode = getField(rootNode, "schema");
  const schema = schemaNode && schemaNode.type === "string" ? schemaNode.value : "";
  if (schema === "matrixscroll.commit_envelope.v1") {
    return {
      successTitle: "Commit envelope verified.",
      successMessage: "The commit body, actor, and tool match the embedded Ed25519 signature.",
      details: [{ label: "Schema", value: "commit envelope" }]
    };
  }
  if (schema === "matrixscroll.release_manifest.v1") {
    return {
      successTitle: "Release manifest verified.",
      successMessage: "The release payload and signature still match after transport.",
      details: [{ label: "Schema", value: "release manifest" }]
    };
  }
  if (schema === "matrixscroll.evidence_pack.v1") {
    return {
      successTitle: "Evidence pack verified.",
      successMessage: "The evidence payload matches the embedded signature contract.",
      details: [{ label: "Schema", value: "evidence pack" }]
    };
  }
  if (schema === "matrixscroll.agent_payment.v1") {
    return {
      successTitle: "Agent payment attestation verified.",
      successMessage: "The transaction amount, merchant, and method match the agent signature.",
      details: [{ label: "Schema", value: "agent payment attestation" }]
    };
  }
  return {
    successTitle: "Signature valid.",
    successMessage: "The manifest body matches the embedded Ed25519 signature.",
    details: schema ? [{ label: "Schema", value: schema }] : []
  };
}

function pushStringDetail(details, label, node) {
  if (node && node.type === "string" && node.value) {
    details.push({ label, value: node.value });
  }
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

let cachedTrustKeys = null;

async function getTrustKeys() {
  if (cachedTrustKeys) return cachedTrustKeys;
  try {
    const response = await fetch("/.well-known/matrixscroll-trust.json");
    if (response.ok) {
      const data = await response.json();
      cachedTrustKeys = (data.keys || []).map(k => k.public_key);
    }
  } catch (e) {
    console.error("Failed to fetch trust root", e);
  }
  return cachedTrustKeys || [];
}

async function verifyManifest(root) {
  try {
    const input = getManifestValue(root);
    if (!input) throw new Error("Paste a signed manifest first");
    const manifest = requireObject(new JsonParser(input).parse(), "Manifest");
    const signature = requireObject(getField(manifest, "signature"), "signature");

    const schema = getStringField(signature, "schema");
    const algorithm = getStringField(signature, "algorithm").toLowerCase();
    const deviceId = getStringField(signature, "device_id");
    const publicKey = getStringField(signature, "public_key");
    const mode = getStringField(signature, "mode");
    const signedAt = getStringField(signature, "signed_at");
    const value = getStringField(signature, "value");

    if (schema !== "matrixscroll.signature.v1") {
      throw new Error(`Unsupported signature schema: ${schema}`);
    }
    if (algorithm !== "ed25519") {
      throw new Error(`Unsupported signature algorithm: ${algorithm}`);
    }

    const publicKeyBytes = base64ToBytes(publicKey);
    const signatureBytes = base64ToBytes(value);
    if (publicKeyBytes.length !== 32) throw new Error(`Expected 32-byte Ed25519 public key, got ${publicKeyBytes.length}`);
    if (signatureBytes.length !== 64) throw new Error(`Expected 64-byte Ed25519 signature, got ${signatureBytes.length}`);

    const derivedDeviceId = await deriveDeviceId(publicKeyBytes);
    if (derivedDeviceId !== deviceId) {
      throw new Error(`Device ID mismatch: expected ${derivedDeviceId}, manifest says ${deviceId}`);
    }

    const canonical = canonicalize(manifest, { omitTopLevelSignature: true });
    const canonicalBytes = new TextEncoder().encode(canonical);
    const ok = await verifyEd25519(publicKeyBytes, signatureBytes, canonicalBytes);
    const manifestSummary = describeManifest(manifest);
    const details = [...manifestSummary.details];
    const provenance = getField(manifest, "provenance");
    if (provenance && provenance.type === "object") {
      pushStringDetail(details, "Actor", getField(provenance, "actor_type"));
      pushStringDetail(details, "Tool", getField(provenance, "tool"));
    }
    pushStringDetail(details, "Project", getField(manifest, "project"));
    
    const manifestSchemaNode = getField(manifest, "schema");
    const manifestSchema = manifestSchemaNode && manifestSchemaNode.type === "string" ? manifestSchemaNode.value : "";
    if (manifestSchema === "matrixscroll.agent_payment.v1") {
      pushStringDetail(details, "Transaction ID", getField(manifest, "transaction_id"));
      const amountNode = getField(manifest, "amount");
      const currencyNode = getField(manifest, "currency");
      if (amountNode && amountNode.type === "number" && currencyNode && currencyNode.type === "string") {
        details.push({ label: "Amount", value: `${amountNode.value} ${currencyNode.value}` });
      }
      pushStringDetail(details, "Merchant", getField(manifest, "merchant"));
      const methodNode = getField(manifest, "payment_method");
      if (methodNode && methodNode.type === "object") {
        pushStringDetail(details, "Payment Method", getField(methodNode, "type"));
      }
    }
    details.push(
      { label: "Device", value: deviceId },
      { label: "Mode", value: mode },
      { label: "Signed", value: signedAt },
      { label: "Canonical", value: `${canonicalBytes.length} bytes` }
    );

    if (ok) {
      try {
        const response = await fetch(`/id/${deviceId}.json`);
        if (response.ok) {
          const cert = await response.json();
          if (cert && cert.subject && cert.subject.device_id === deviceId) {
            let certValid = false;
            try {
              const certSigPub = base64ToBytes(cert.signature.public_key);
              const certSigVal = base64ToBytes(cert.signature.value);
              const certCanon = new TextEncoder().encode(canonicalize(cert, { omitTopLevelSignature: true }));
              certValid = await verifyEd25519(certSigPub, certSigVal, certCanon);
            } catch (err) {
              console.error("Certificate crypto verification failed", err);
            }

            const trustKeys = await getTrustKeys();
            const isChained = trustKeys.includes(cert.signature.public_key);

            if (certValid && isChained) {
              const escapedName = escapeHtml(cert.subject.display_name);
              const escapedAccts = (cert.subject.verified_accounts || [])
                .map(a => `${escapeHtml(a.type)}:${escapeHtml(a.value)}`)
                .join(", ");
              details.unshift({
                label: "Identity",
                value: `<span style="color: #10B981; font-weight: 600;">✅ Verified Identity: ${escapedName} (${escapedAccts})</span>`
              });
            } else {
              details.unshift({
                label: "Identity",
                value: `<span style="color: #EF4444; font-weight: 600;">❌ Forged Certificate: Signature invalid or not chained to trust root</span>`
              });
            }
          } else {
            details.unshift({
              label: "Identity",
              value: `<span style="color: #F59E0B; font-weight: 500;">⚠️ Self-signed (unverified) — <a href="/authority/" style="color: var(--accent); text-decoration: underline;">Claim Yours</a></span>`
            });
          }
        } else {
          details.unshift({
            label: "Identity",
            value: `<span style="color: #F59E0B; font-weight: 500;">⚠️ Self-signed (unverified) — <a href="/authority/" style="color: var(--accent); text-decoration: underline;">Claim Yours</a></span>`
          });
        }
      } catch (e) {
        details.unshift({
          label: "Identity",
          value: `<span style="color: #F59E0B; font-weight: 500;">⚠️ Self-signed (unverified) — <a href="/authority/" style="color: var(--accent); text-decoration: underline;">Claim Yours</a></span>`
        });
      }
    }

    setResult(
      root,
      ok ? "valid" : "invalid",
      ok ? manifestSummary.successTitle : "Signature did not verify.",
      ok ? (details.some(d => d.label === "Identity" && d.value.includes("✅")) ? "The cryptographic signature and identity binding are fully verified." : manifestSummary.successMessage) : "The manifest was parsed, but the signed bytes do not match the signature.",
      details
    );
  } catch (error) {
    setResult(root, "invalid", "Verification failed.", error.message);
  }
}

function getSampleValue(sampleName) {
  if (sampleName === "release") return SAMPLE_RELEASE_MANIFEST;
  if (sampleName === "payment") return SAMPLE_AGENT_PAYMENT;
  return SAMPLE_COMMIT_ENVELOPE;
}

function tamperValue(source) {
  if (source.includes("\"amount\": 250.0")) {
    return source.replace("\"amount\": 250.0", "\"amount\": 999.99");
  }
  if (source.includes("\"tool\": \"git-cli\"")) {
    return source.replace("\"tool\": \"git-cli\"", "\"tool\": \"tampered-cli\"");
  }
  if (source.includes("\"policy\": \"ai-assisted-code\"")) {
    return source.replace("\"policy\": \"ai-assisted-code\"", "\"policy\": \"tampered-policy\"");
  }
  return source.replace("\"mode\": \"emulated\"", "\"mode\": \"tampered\"");
}

function wireVerifier(root) {
  const input = root.querySelector("[data-manifest-input]");
  const dropZone = root.querySelector("[data-drop-zone]");
  const verifyButton = root.querySelector("[data-verify-button]");
  const tamperButton = root.querySelector("[data-tamper-button]");
  const clearButton = root.querySelector("[data-clear-button]");
  const sampleButtons = root.querySelectorAll("[data-load-sample]");

  resetResult(root);

  if (verifyButton) {
    verifyButton.addEventListener("click", () => verifyManifest(root));
  }

  sampleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setManifestValue(root, getSampleValue(button.dataset.loadSample));
      verifyManifest(root);
    });
  });

  if (tamperButton) {
    tamperButton.addEventListener("click", () => {
      const value = getManifestValue(root) || SAMPLE_COMMIT_ENVELOPE;
      setManifestValue(root, tamperValue(value));
      verifyManifest(root);
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      setManifestValue(root, "");
      resetResult(root);
    });
  }

  if (dropZone && input) {
    dropZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("is-dragging"));
    dropZone.addEventListener("drop", async (event) => {
      event.preventDefault();
      dropZone.classList.remove("is-dragging");
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      input.value = await file.text();
      verifyManifest(root);
    });
  }

  if (root.dataset.autoload) {
    setManifestValue(root, getSampleValue(root.dataset.autoload));
    verifyManifest(root);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-verifier-root]").forEach(wireVerifier);
});
