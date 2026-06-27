module.exports = async (req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'authorization, content-type');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const authHeader = req.headers.authorization;
  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Determine Origin
  const protocol = req.headers['x-forwarded-proto'] || 'http';
  const host = req.headers.host || 'localhost:3000';
  const origin = `${protocol}://${host}`;

  // Fallback to Simulation Mode if variables are missing
  if (!stripeSecretKey || !supabaseUrl || !supabaseAnonKey) {
    console.log('[PORTAL] Missing Stripe or Supabase config. Running in SIMULATED mode.');
    return res.status(200).json({
      url: `${origin}/authority/?manage_billing=true&simulated=true`,
      message: 'Billing Portal session generated (Simulated Mode)'
    });
  }

  // Real Mode: Authenticate User JWT via Supabase Auth REST endpoint
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authentication token' });
  }

  try {
    // 1. Authenticate user
    const authResponse = await fetch(`${supabaseUrl}/auth/v1/user`, {
      method: 'GET',
      headers: {
        'apikey': supabaseAnonKey,
        'Authorization': authHeader
      }
    });

    if (!authResponse.ok) {
      const errorText = await authResponse.text();
      return res.status(401).json({ error: `Authentication failed: ${errorText}` });
    }

    const userData = await authResponse.json();
    const userId = userData.id;

    if (!userId) {
      return res.status(401).json({ error: 'Unable to resolve user profile' });
    }

    // 2. Fetch customer ID from profiles table via Supabase REST API
    const dbResponse = await fetch(`${supabaseUrl}/rest/v1/profiles?select=stripe_customer_id&id=eq.${userId}`, {
      method: 'GET',
      headers: {
        'apikey': supabaseAnonKey,
        'Authorization': authHeader
      }
    });

    if (!dbResponse.ok) {
      const dbError = await dbResponse.text();
      return res.status(500).json({ error: `Database fetch failed: ${dbError}` });
    }

    const profiles = await dbResponse.json();
    const customerId = profiles[0]?.stripe_customer_id;

    if (!customerId) {
      return res.status(404).json({ error: 'No Stripe customer record found for this user.' });
    }

    // 3. Create Stripe Billing Portal Session
    const stripeParams = new URLSearchParams({
      'customer': customerId,
      'return_url': `${origin}/authority/`
    });

    const stripeResponse = await fetch('https://api.stripe.com/v1/billing_portal/sessions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${stripeSecretKey}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: stripeParams.toString()
    });

    const session = await stripeResponse.json();

    if (!stripeResponse.ok) {
      return res.status(500).json({ error: session.error?.message || 'Stripe API Error' });
    }

    return res.status(200).json({ url: session.url });

  } catch (err) {
    console.error('[PORTAL ERROR]', err);
    return res.status(500).json({ error: 'Internal server error: ' + err.message });
  }
};
