const crypto = require("crypto");
const { createClient } = require("@supabase/supabase-js");
const { verifyManifest, canonicalBytes, deviceIdFromPub } = require("../lib/canonical");

// Generate a static mock keypair for simulation mode so verification works locally
let mockKeyPair;
try {
  mockKeyPair = crypto.generateKeyPairSync("ed25519");
} catch (e) {
  console.warn("Failed to generate mock keypair", e);
}

module.exports = async (req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { challenge_id, signed_nonce } = req.body || {};
  if (!challenge_id || !signed_nonce) {
    return res.status(400).json({ error: "Missing challenge_id or signed_nonce" });
  }

  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const authorityPrivateKey = process.env.AUTHORITY_PRIVATE_KEY;

  // Fallback to Simulation Mode if config is missing
  if (!stripeSecretKey || !supabaseUrl || !supabaseServiceKey) {
    console.log('[ENROLL/COMPLETE] Running in SIMULATED mode.');
    
    // In simulation mode, accept the signature verification using our canon verification
    if (!verifyManifest(signed_nonce)) {
      return res.status(400).json({ error: "Cryptographic signature validation failed on signed nonce" });
    }

    // Generate simulated certificate signed by our mock keypair
    const now = new Date();
    const exp = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000); // 30 days
    const authPubKey = mockKeyPair.publicKey.export({ type: "spki", format: "der" }).slice(12).toString("base64");
    const authDevId = deviceIdFromPub(authPubKey);

    const cert = {
      schema: "matrixscroll.identity_certificate.v1",
      subject: {
        public_key: signed_nonce.signature.public_key,
        device_id: signed_nonce.signature.device_id,
        display_name: "Simulated Developer Profile",
        verified_accounts: [
          { type: "github", value: "simulated-dev", method: "oauth" },
          { type: "email", value: "simulated@matrixscroll.com", method: "oauth" }
        ],
        plan: "basic",
        issued_at: now.toISOString().replace(/\.\d+Z$/, 'Z'),
        expires_at: exp.toISOString().replace(/\.\d+Z$/, 'Z')
      },
      issuer: {
        authority: "matrixscroll-authority-v1",
        public_key: authPubKey,
        device_id: authDevId
      }
    };

    // Sign the certificate using Node's crypto
    const canonicalPayload = canonicalBytes(cert);
    const signatureVal = crypto.sign(null, canonicalPayload, mockKeyPair.privateKey).toString("base64");

    cert.signature = {
      schema: "matrixscroll.signature.v1",
      algorithm: "ed25519",
      device_id: authDevId,
      public_key: authPubKey,
      mode: "emulated",
      signed_at: now.toISOString().replace(/\.\d+Z$/, 'Z'),
      value: signatureVal
    };

    return res.status(200).json({ status: "issued", certificate: cert });
  }

  // Real Mode
  try {
    const db = createClient(supabaseUrl, supabaseServiceKey);

    // 1. Fetch challenge from db
    const { data: ch, error: chErr } = await db
      .from("enroll_challenges")
      .select("*")
      .eq("challenge_id", challenge_id)
      .single();

    if (chErr || !ch) {
      return res.status(404).json({ error: "Enrollment challenge not found" });
    }

    if (ch.consumed_at) {
      return res.status(400).json({ error: "Enrollment challenge already consumed" });
    }

    if (new Date(ch.expires_at) < new Date()) {
      return res.status(400).json({ error: "Enrollment challenge has expired" });
    }

    // 2. Validate client signature over challenge nonce
    if (signed_nonce.nonce !== ch.nonce || signed_nonce.challenge_id !== challenge_id) {
      return res.status(400).json({ error: "Challenge nonce mismatch" });
    }

    if (!verifyManifest(signed_nonce)) {
      return res.status(400).json({ error: "Cryptographic signature validation failed on signed nonce" });
    }

    if (signed_nonce.signature.public_key !== ch.public_key) {
      return res.status(400).json({ error: "Key does not match enrolled public key" });
    }

    // 3. Verify active subscription tied to this challenge ID
    const { data: sub, error: subErr } = await db
      .from("subscriptions")
      .select("*")
      .eq("enroll_challenge_id", challenge_id)
      .maybeSingle();

    if (subErr || !sub || !["active", "trialing"].includes(sub.status)) {
      return res.status(200).json({ status: "pending_subscription" });
    }

    // 4. Load Authority private key and sign identity certificate
    let privateKeyObj;
    let authPubKey;
    
    if (authorityPrivateKey) {
      privateKeyObj = crypto.createPrivateKey(authorityPrivateKey);
      const pubKeyObj = crypto.createPublicKey(privateKeyObj);
      authPubKey = pubKeyObj.export({ type: "spki", format: "der" }).slice(12).toString("base64");
    } else {
      // Fallback to mock key if missing env var (for debugging on non-prod stages)
      privateKeyObj = mockKeyPair.privateKey;
      authPubKey = mockKeyPair.publicKey.export({ type: "spki", format: "der" }).slice(12).toString("base64");
    }

    const authDevId = deviceIdFromPub(authPubKey);
    const now = new Date();
    const exp = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000); // 30 days

    const cert = {
      schema: "matrixscroll.identity_certificate.v1",
      subject: {
        public_key: ch.public_key,
        device_id: ch.device_id,
        display_name: sub.display_name || "Developer Profile",
        verified_accounts: sub.verified_accounts || [],
        plan: sub.plan,
        issued_at: now.toISOString().replace(/\.\d+Z$/, 'Z'),
        expires_at: exp.toISOString().replace(/\.\d+Z$/, 'Z')
      },
      issuer: {
        authority: "matrixscroll-authority-v1",
        public_key: authPubKey,
        device_id: authDevId
      }
    };

    // Sign canonicalized cert payload
    const canonicalPayload = canonicalBytes(cert);
    const signatureVal = crypto.sign(null, canonicalPayload, privateKeyObj).toString("base64");

    cert.signature = {
      schema: "matrixscroll.signature.v1",
      algorithm: "ed25519",
      device_id: authDevId,
      public_key: authPubKey,
      mode: "emulated",
      signed_at: now.toISOString().replace(/\.\d+Z$/, 'Z'),
      value: signatureVal
    };

    // 5. Update database state and persist identity mapping
    await db
      .from("enroll_challenges")
      .update({ consumed_at: now.toISOString() })
      .eq("challenge_id", challenge_id);

    await db.from("identities").upsert({
      public_key: ch.public_key,
      device_id: ch.device_id,
      user_id: sub.user_id,
      display_name: cert.subject.display_name,
      verified_accounts: cert.subject.verified_accounts,
      cert_json: cert,
      issued_at: cert.subject.issued_at,
      expires_at: cert.subject.expires_at,
      revoked_at: null
    });

    return res.status(200).json({ status: "issued", certificate: cert });

  } catch (err) {
    console.error('[ENROLL/COMPLETE ERROR]', err);
    return res.status(500).json({ error: 'Internal server error: ' + err.message });
  }
};
