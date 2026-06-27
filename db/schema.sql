-- Run in the Supabase SQL editor. RLS on; the server-only service key bypasses.
create table if not exists subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  enroll_challenge_id uuid,                         -- links a checkout to an enrollment
  stripe_customer_id text,
  stripe_sub_id text,
  plan text not null default 'basic' check (plan in ('basic','team','enterprise')),
  status text not null default 'incomplete',        -- mirrors Stripe sub status
  display_name text,
  verified_accounts jsonb not null default '[]',    -- captured at OAuth/checkout
  current_period_end timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists enroll_challenges (
  challenge_id uuid primary key,
  public_key text not null,
  device_id text not null,
  nonce text not null,
  expires_at timestamptz not null,
  consumed_at timestamptz
);
create index if not exists idx_challenges_device on enroll_challenges(device_id);

create table if not exists identities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  public_key text not null unique,
  device_id text not null unique,
  display_name text not null,
  verified_accounts jsonb not null default '[]',
  cert_json jsonb not null,                         -- the signed identity_certificate.v1
  issued_at timestamptz not null,
  expires_at timestamptz not null,
  revoked_at timestamptz
);
create index if not exists idx_identities_device on identities(device_id);

-- Team tier (phase 2): same cert with plan='team', seats roll up to an org.
create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users(id),
  name text not null,
  stripe_sub_id text,
  seats int not null default 1,
  created_at timestamptz not null default now()
);
create table if not exists team_members (
  team_id uuid references teams(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  role text not null default 'member',
  primary key (team_id, user_id)
);

alter table subscriptions enable row level security;
alter table identities    enable row level security;
alter table teams         enable row level security;
alter table team_members  enable row level security;
-- enroll_challenges: service-key only, no policies.

create policy own_subs on subscriptions for select using (auth.uid() = user_id);
create policy own_ids  on identities    for select using (auth.uid() = user_id);
