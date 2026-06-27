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

  // Webhook Signature Verification in Vanilla Node.js
  let event;
  try {
    const parts = sigHeader.split(',');
    const timestampPart = parts.find(p => p.startsWith('t='));
    const signaturePart = parts.find(p => p.startsWith('v1='));

    if (!timestampPart || !signaturePart) {
      throw new Error('Signature header missing t or v1 fields');
    }

    const timestamp = timestampPart.split('=')[1];
    const signature = signaturePart.split('=')[1];

    const signedPayload = `${timestamp}.${rawBody.toString()}`;
    const expectedSignature = crypto
      .createHmac('sha256', webhookSecret)
      .update(signedPayload)
      .digest('hex');

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
    const fetch = require('node-fetch'); // globally available in Vercel Node 18+

    switch (event.type) {
      case 'checkout.session.completed': {
        const customerId = session.customer;
        const subscriptionId = session.subscription;
        const challengeId = session.metadata?.challenge_id || session.client_reference_id;

        if (!challengeId) {
          console.warn('[WEBHOOK WARNING] No challenge_id found in checkout session metadata');
          break;
        }

        // Retrieve subscription info from Stripe
        const subResponse = await fetch(`https://api.stripe.com/v1/subscriptions/${subscriptionId}`, {
          headers: { 'Authorization': `Bearer ${stripeSecretKey}` }
        });
        const subscription = await subResponse.json();

        // Extract customer name/email for display
        const customerResponse = await fetch(`https://api.stripe.com/v1/customers/${customerId}`, {
          headers: { 'Authorization': `Bearer ${stripeSecretKey}` }
        });
        const customer = await customerResponse.json();

        const displayName = customer.name || 'Developer Profile';
        const verifiedAccounts = [
          { type: 'email', value: customer.email || 'dev@matrixscroll.com', method: 'oauth' }
        ];

        // Upsert subscription into Supabase
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/subscriptions`, {
          method: 'POST',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates'
          },
          body: JSON.stringify({
            enroll_challenge_id: challengeId,
            stripe_customer_id: customerId,
            stripe_sub_id: subscriptionId,
            status: subscription.status,
            plan: 'basic',
            display_name: displayName,
            verified_accounts: verifiedAccounts,
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString()
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB SUBSCRIPTION INSERT ERROR]', updateError);
        } else {
          console.log(`[WEBHOOK SUCCESS] Subscription ${subscriptionId} synchronized for challenge ${challengeId}.`);
        }
        break;
      }

      case 'customer.subscription.updated': {
        const subscription = session;
        const subscriptionId = subscription.id;

        // Sync status to subscriptions table
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/subscriptions?stripe_sub_id=eq.${subscriptionId}`, {
          method: 'PATCH',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            status: subscription.status,
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString()
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB UPDATE ERROR]', updateError);
        } else {
          console.log(`[WEBHOOK SUCCESS] Subscription ${subscriptionId} status updated to: ${subscription.status}`);
        }
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = session;
        const subscriptionId = subscription.id;

        // 1. Mark subscription as canceled
        const updateResponse = await fetch(`${supabaseUrl}/rest/v1/subscriptions?stripe_sub_id=eq.${subscriptionId}`, {
          method: 'PATCH',
          headers: {
            'apikey': supabaseServiceRoleKey,
            'Authorization': `Bearer ${supabaseServiceRoleKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
          },
          body: JSON.stringify({
            status: 'canceled'
          })
        });

        if (!updateResponse.ok) {
          const updateError = await updateResponse.text();
          console.error('[WEBHOOK DB DOWNGRADE ERROR]', updateError);
          break;
        }

        const subRecords = await updateResponse.json();
        const challengeId = subRecords[0]?.enroll_challenge_id;

        if (challengeId) {
          // 2. Fetch challenge details to resolve device_id / public_key
          const chResponse = await fetch(`${supabaseUrl}/rest/v1/enroll_challenges?challenge_id=eq.${challengeId}`, {
            headers: {
              'apikey': supabaseServiceRoleKey,
              'Authorization': `Bearer ${supabaseServiceRoleKey}`
            }
          });
          const chRecords = await chResponse.json();
          const publicKey = chRecords[0]?.public_key;

          if (publicKey) {
            // 3. Mark the identity certificate as revoked
            const revokeResponse = await fetch(`${supabaseUrl}/rest/v1/identities?public_key=eq.${publicKey}`, {
              method: 'PATCH',
              headers: {
                'apikey': supabaseServiceRoleKey,
                'Authorization': `Bearer ${supabaseServiceRoleKey}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                revoked_at: new Date().toISOString()
              })
            });

            if (!revokeResponse.ok) {
              console.error('[WEBHOOK DB REVOCATION ERROR]', await revokeResponse.text());
            } else {
              console.log(`[WEBHOOK SUCCESS] Key ${publicKey} successfully revoked due to subscription cancellation.`);
            }
          }
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

module.exports.config = {
  api: {
    bodyParser: false
  }
};
