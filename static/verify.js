(function () {
  const sampleManifest = {
    commit: {
      author: {
        date: "1740000000",
        email: "dev@example.com",
        name: "Example Developer"
      },
      committer: {
        date: "1740000000",
        email: "dev@example.com",
        name: "Example Developer"
      },
      expected_id: "0000000000000000000000000000000000000000",
      message: "feat: add commit envelope example\n\nSigned-by: matrixscroll",
      parents: [],
      tree: "0000000000000000000000000000000000000000"
    },
    provenance: {
      actor_type: "human",
      tool: "git-cli",
      tool_version: "2.43.0"
    },
    repository: {
      branch: "main",
      name: "matrixscroll",
      remote_url: "https://github.com/SSX360/matrixscroll"
    },
    schema: "matrixscroll.commit_envelope.v1",
    signature: {
      algorithm: "ed25519",
      device_id: "MS-4319-20D5",
      mode: "emulated",
      public_key: "bsVoWgUYK+NZNcSNIoWjO3IiTK/xT6U6mXFzBJgPUKc=",
      schema: "matrixscroll.signature.v1",
      signed_at: "2026-06-20T00:04:31Z",
      value: "P/YGQsCEyFfWizauGvxFpJ71pk0JFvzgoMTRzEnLumtKIwac/H83eKNc5t4w9RJCudMZR6v24KCtsclB+uyTBQ=="
    }
  };

  const tamperedManifest = JSON.parse(JSON.stringify(sampleManifest));
  tamperedManifest.signature.device_id = "MS-TAMP-ERED";

  function asciiJsonString(value) {
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, function (char) {
      return "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0");
    });
  }

  function stableStringify(value) {
    if (value === null) {
      return "null";
    }
    if (Array.isArray(value)) {
      return "[" + value.map(stableStringify).join(",") + "]";
    }
    if (typeof value === "object") {
      return "{" + Object.keys(value).sort().map(function (key) {
        return asciiJsonString(key) + ":" + stableStringify(value[key]);
      }).join(",") + "}";
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new Error("Manifest contains NaN or Infinity, which Matrix Scroll rejects.");
      }
      return JSON.stringify(value);
    }
    return asciiJsonString(value);
  }

  function canonicalBytes(manifest) {
    const body = {};
    Object.keys(manifest).forEach(function (key) {
      if (key !== "signature") {
        body[key] = manifest[key];
      }
    });
    return new TextEncoder().encode(stableStringify(body));
  }

  function b64ToBytes(value) {
    const raw = atob(value);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      out[i] = raw.charCodeAt(i);
    }
    return out;
  }

  function bytesToHexUpper(bytes) {
    return Array.from(bytes).map(function (byte) {
      return byte.toString(16).padStart(2, "0");
    }).join("").toUpperCase();
  }

  async function deriveDeviceId(publicKeyBytes) {
    const digest = await crypto.subtle.digest("SHA-256", publicKeyBytes);
    const hex = bytesToHexUpper(new Uint8Array(digest));
    return "MS-" + hex.slice(0, 4) + "-" + hex.slice(4, 8);
  }

  async function importEd25519Key(publicKeyBytes) {
    try {
      return await crypto.subtle.importKey("raw", publicKeyBytes, "Ed25519", false, ["verify"]);
    } catch (error) {
      return crypto.subtle.importKey("raw", publicKeyBytes, { name: "Ed25519" }, false, ["verify"]);
    }
  }

  async function verifySignature(publicKeyBytes, signatureBytes, messageBytes) {
    const key = await importEd25519Key(publicKeyBytes);
    try {
      return await crypto.subtle.verify("Ed25519", key, signatureBytes, messageBytes);
    } catch (error) {
      return crypto.subtle.verify({ name: "Ed25519" }, key, signatureBytes, messageBytes);
    }
  }

  async function verifyManifest(manifest) {
    if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
      throw new Error("The envelope must be a JSON object.");
    }

    const signature = manifest.signature;
    if (!signature || typeof signature !== "object") {
      throw new Error("Missing signature block.");
    }

    if (signature.schema !== "matrixscroll.signature.v1") {
      throw new Error("Unsupported signature schema: " + String(signature.schema || "(missing)") + ".");
    }

    if (signature.algorithm !== "ed25519") {
      throw new Error("Unsupported signature algorithm: " + String(signature.algorithm || "(missing)") + ".");
    }

    if (!window.crypto || !window.crypto.subtle) {
      throw new Error("This browser does not expose Web Crypto.");
    }

    const publicKeyBytes = b64ToBytes(signature.public_key);
    const signatureBytes = b64ToBytes(signature.value);
    const expectedDeviceId = await deriveDeviceId(publicKeyBytes);
    const messageBytes = canonicalBytes(manifest);

    if (signature.device_id !== expectedDeviceId) {
      return {
        ok: false,
        message: "Device ID mismatch: expected " + expectedDeviceId + ", manifest says " + signature.device_id + ".",
        details: {
          algorithm: signature.algorithm,
          device_id: signature.device_id,
          expected_device_id: expectedDeviceId,
          mode: signature.mode || "(missing)",
          signed_at: signature.signed_at || "(missing)",
          canonical_bytes: String(messageBytes.length)
        }
      };
    }

    let supported = true;
    let verified = false;
    try {
      verified = await verifySignature(publicKeyBytes, signatureBytes, messageBytes);
    } catch (error) {
      supported = false;
    }

    if (!supported) {
      throw new Error("This browser cannot verify Ed25519 with Web Crypto yet. Try a current Chrome, Edge, or Safari build.");
    }

    return {
      ok: verified,
      message: verified ? "Signature valid for canonical commit envelope." : "Ed25519 signature verification failed.",
      details: {
        algorithm: signature.algorithm,
        device_id: signature.device_id,
        mode: signature.mode || "(missing)",
        signed_at: signature.signed_at || "(missing)",
        canonical_bytes: String(messageBytes.length)
      }
    };
  }

  function setJson(editor, payload) {
    editor.value = JSON.stringify(payload, null, 2);
  }

  function renderDetails(target, details) {
    target.innerHTML = "";
    Object.entries(details).forEach(function (entry) {
      const row = document.createElement("div");
      row.className = "detail-item";

      const key = document.createElement("span");
      key.className = "detail-key";
      key.textContent = entry[0].replace(/_/g, " ");

      const value = document.createElement("span");
      value.className = "detail-value";
      value.textContent = entry[1];

      row.appendChild(key);
      row.appendChild(value);
      target.appendChild(row);
    });
  }

  function setBanner(banner, kind, label, headline, body) {
    banner.className = "result-banner " + kind;
    banner.querySelector(".label").textContent = label;
    banner.querySelector(".headline").textContent = headline;
    banner.querySelector(".body").textContent = body;
  }

  async function runVerification() {
    const editor = document.getElementById("manifestInput");
    const banner = document.getElementById("verifyResult");
    const details = document.getElementById("verifyDetails");

    try {
      const manifest = JSON.parse(editor.value);
      const result = await verifyManifest(manifest);
      renderDetails(details, result.details);

      if (result.ok) {
        setBanner(
          banner,
          "ok",
          "PASS",
          "Signature valid",
          result.message
        );
      } else {
        setBanner(
          banner,
          "error",
          "FAIL",
          "INVALID",
          result.message
        );
      }
    } catch (error) {
      details.innerHTML = "";
      setBanner(
        banner,
        "error",
        "ERROR",
        "Could not verify",
        error instanceof Error ? error.message : String(error)
      );
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const editor = document.getElementById("manifestInput");
    const loadSample = document.getElementById("loadSample");
    const loadTampered = document.getElementById("loadTampered");
    const clearEditor = document.getElementById("clearManifest");
    const verifyButton = document.getElementById("runVerify");

    setJson(editor, sampleManifest);
    runVerification();

    loadSample.addEventListener("click", function () {
      setJson(editor, sampleManifest);
      runVerification();
    });

    loadTampered.addEventListener("click", function () {
      setJson(editor, tamperedManifest);
      runVerification();
    });

    clearEditor.addEventListener("click", function () {
      editor.value = "";
    });

    verifyButton.addEventListener("click", runVerification);
  });
}());
