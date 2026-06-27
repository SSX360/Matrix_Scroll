const crypto = require('crypto');

// Buffer Helper to read raw body for signature verification
function getRawBody(req) {
  return new Promise((resolve, reject) => {
    let chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', (err) => reject(err));
  });
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const sigHeader = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SIGNING_SECRET;
  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  let rawBody;
  try {
    rawBody = await getRawBody(req);
  } catch (err) {
    return res.status(400).json({ error: 'Failed to parse raw body' });
  }

  // Fallback to Simulation Mode if config is missing
  if (!webhookSecret || !stripeSecretKey || !supabaseUrl || !supabaseServiceRoleKey) {
    console.log('[WEBHOOK] Running in SIMULATED mode. No signature checked.');
    let event;
    try {
      event = JSON.parse(rawBody.toString());
    } catch (e) {
      return res.status(400).json({ error: 'Invalid JSON body' });
    }
    
    console.log(`[WEBHOOK EVENT SIMULATED] Type: ${event.type}`, event);
    return res.status(200).json({ received: true, simulated: true });
  }

  if (!sigHeader) {
    return res.status(400).json({ error: 'Missing stripe-signature header' });
  }

  // Cryptographic Webhook Signature Verification in Vanilla Node.js
  let event;
  try {
    // Parse signature header components
    const parts = sigHeader.split(',');
    const timestampPart = parts.find(p => p.startsWith('t='));
    const signaturePart = parts.find(p => p.startsWith('v1='));

    if (!timestampPart || !signaturePart) {
      throw new Error('Signature header missing t or v1 fields');
    }

    const timestamp = timestampPart.split('=')[1];
    const signature = signaturePart.split('=')[1];

    // Compute signature hash
    const signedPayload = `${timestamp}.${rawBody.toString()}`;
    const expectedSignature = crypto
      .createHmac('sha256', webhookSecret)
      .update(signedPayload)
      .digest('hex');

    // Time-constant comparison to protect against timing attacks
    const hmacMatches = crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expectedSignature, 'hex')
    );

    if (!hmacMatches) {
      throw new Error('HMAC signature mismatch');
    }

    event = JSON.parse(rawBody.toString());
  } catch (err) {
    console.error('[WEBHOOK SIGNATURE VERIFY FAILED]', err.message);
    return res.status(400).json({ error: `Signature verification failed: ${err.message}` });
  }

  // Handle Stripe Webhook Events
  try {
    const session = event.data.object;
    
    switch (event.type) {
      case 'checkout.session.completed': {
        const customerId = session.customer;
        const subscriptionId = session.subscription;
        const supabaseUserId = session.metadata.supabase_user_id;

        if (!supabaseUserId) {
          console.warn('[WEBHOOK WARNING] No supabase_user_id found in session metadata');
          break;
        }

        // Retrieve subscription info to verify status
        const subResponse = await fetch(`https://api.stripe.com/v1/subscriptions/${subscriptionId}`, {
          headers: { 'Authorization': `Bearer ${stripeSecretKey}` }
        });
        const subscription = await subResponse.json();

        // Update profile subscription status in Supabase Database (RLS bypassed using Service Role key)
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/profiles?id=eq.${supabaseUserId}`, {
          method: 'PATCH',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
          },
          body: JSON.stringify({
            stripe_customer_id: customerId,
            stripe_subscription_id: subscriptionId,
            subscription_status: subscription.status,
            price_id: subscription.items.data[0]?.price.id
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB UPDATE ERROR]', updateError);
        } else {
          console.log(`[WEBHOOK SUCCESS] Profile ${supabaseUserId} updated to active subscription.`);
        }
        break;
      }

      case 'customer.subscription.updated': {
        const subscription = session;
        const customerId = subscription.customer;

        // Sync updated status to Database
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/profiles?stripe_customer_id=eq.${customerId}`, {
          method: 'PATCH',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            subscription_status: subscription.status,
            price_id: subscription.items.data[0]?.price.id
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB UPDATE ERROR]', updateError);
        } else {
          console.log(`[WEBHOOK SUCCESS] Customer ${customerId} subscription updated to: ${subscription.status}`);
        }
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = session;
        const customerId = subscription.customer;

        // Downgrade user back to free tier (status: canceled, price_id: null)
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/profiles?stripe_customer_id=eq.${customerId}`, {
          method: 'PATCH',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            subscription_status: 'canceled',
            price_id: null
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB UPDATE ERROR]', updateError);
        } else {
          console.log(`[WEBHOOK SUCCESS] Customer ${customerId} subscription canceled.`);
        }
        break;
      }
    }

    return res.status(200).json({ received: true });

  } catch (err) {
    console.error('[WEBHOOK HANDLER ERROR]', err);
    return res.status(500).json({ error: 'Internal webhook handling error' });
  }
};
