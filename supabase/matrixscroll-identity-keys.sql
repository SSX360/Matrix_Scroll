-- Matrix Scroll hosted identity key registry (shared SSX360 Supabase project)
create table if not exists public.matrixscroll_identity_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  actor text not null,
  device_id text not null,
  public_key text not null,
  created_at timestamptz not null default now(),
  unique (user_id, device_id)
);

create index if not exists matrixscroll_identity_keys_user_id_idx
  on public.matrixscroll_identity_keys (user_id);

alter table public.matrixscroll_identity_keys enable row level security;

drop policy if exists "read own identity keys" on public.matrixscroll_identity_keys;
create policy "read own identity keys"
on public.matrixscroll_identity_keys
for select
to authenticated
using (user_id = (select auth.uid()));

drop policy if exists "insert own identity keys" on public.matrixscroll_identity_keys;
create policy "insert own identity keys"
on public.matrixscroll_identity_keys
for insert
to authenticated
with check (user_id = (select auth.uid()));

drop policy if exists "delete own identity keys" on public.matrixscroll_identity_keys;
create policy "delete own identity keys"
on public.matrixscroll_identity_keys
for delete
to authenticated
using (user_id = (select auth.uid()));
