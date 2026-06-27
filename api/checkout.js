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
  const stripePriceId = process.env.STRIPE_PRICE_ID || 'price_basic_gtm';

  // Determine Origin
  const protocol = req.headers['x-forwarded-proto'] || 'http';
  const host = req.headers.host || 'localhost:3000';
  const origin = `${protocol}://${host}`;

  // Fallback to Simulation Mode if variables are missing
  if (!stripeSecretKey || !supabaseUrl || !supabaseAnonKey) {
    console.log('[CHECKOUT] Missing Stripe or Supabase config. Running in SIMULATED mode.');
    
    // In simulation mode, return a success redirect directly back to authority portal
    return res.status(200).json({
      url: `${origin}/authority/?payment_success=true&simulated=true`,
      message: 'Checkout Session generated (Simulated Mode)'
    });
  }

  // Real Mode: Authenticate User JWT via Supabase Auth REST endpoint
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authentication token' });
  }

  try {
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

    // Call Stripe API to Create Checkout Session
    const stripeParams = new URLSearchParams({
      'payment_method_types[0]': 'card',
      'line_items[0][price]': stripePriceId,
      'line_items[0][quantity]': '1',
      'mode': 'subscription',
      'success_url': `${origin}/authority/?payment_success=true`,
      'cancel_url': `${origin}/authority/?payment_cancel=true`,
      'metadata[supabase_user_id]': userId
    });

    const stripeResponse = await fetch('https://api.stripe.com/v1/checkout/sessions', {
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
    console.error('[CHECKOUT ERROR]', err);
    return res.status(500).json({ error: 'Internal server error: ' + err.message });
  }
};
