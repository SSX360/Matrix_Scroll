const crypto = require("crypto");
const { createClient } = require("@supabase/supabase-js");
const Stripe = require("stripe");
const { deviceIdFromPub } = require("../lib/canonical");

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

  const { public_key, device_id } = req.body || {};
  if (!public_key || !device_id) {
    return res.status(400).json({ error: "Missing public_key or device_id" });
  }

  if (deviceIdFromPub(public_key) !== device_id) {
    return res.status(400).json({ error: "public_key/device_id mismatch" });
  }

  const protocol = req.headers['x-forwarded-proto'] || 'http';
  const host = req.headers.host || 'localhost:3000';
  const origin = `${protocol}://${host}`;

  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const stripePriceId = process.env.STRIPE_PRICE_ID || 'price_basic_gtm';

  // Fallback to Simulation Mode if keys are missing
  if (!stripeSecretKey || !supabaseUrl || !supabaseServiceKey) {
    console.log('[ENROLL/START] Missing Stripe/Supabase config. Running in SIMULATED mode.');
    const challenge_id = crypto.randomUUID();
    const nonce = crypto.randomBytes(24).toString("base64");
    
    return res.status(200).json({
      challenge_id,
      nonce,
      login_url: `${origin}/authority/?payment_success=true&cid=${challenge_id}&simulated=true`,
      message: 'Enroll Start (Simulated Mode)'
    });
  }

  // Real Mode
  try {
    const db = createClient(supabaseUrl, supabaseServiceKey);
    const stripe = Stripe(stripeSecretKey);

    const challenge_id = crypto.randomUUID();
    const nonce = crypto.randomBytes(24).toString("base64");
    const expires_at = new Date(Date.now() + 10 * 60 * 1000).toISOString(); // 10-min TTL

    const { error: dbErr } = await db.from("enroll_challenges").insert({
      challenge_id,
      public_key,
      device_id,
      nonce,
      expires_at,
      consumed_at: null
    });

    if (dbErr) {
      return res.status(500).json({ error: `Database error: ${dbErr.message}` });
    }

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [{ price: stripePriceId, quantity: 1 }],
      success_url: `${origin}/authority/?payment_success=true&cid=${challenge_id}`,
      cancel_url: `${origin}/authority/?payment_cancel=true`,
      client_reference_id: challenge_id,
      metadata: { challenge_id, device_id },
    });

    return res.status(200).json({ challenge_id, nonce, login_url: session.url });
  } catch (err) {
    console.error('[ENROLL/START ERROR]', err);
    return res.status(500).json({ error: 'Internal server error: ' + err.message });
  }
};
