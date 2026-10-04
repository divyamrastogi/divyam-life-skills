-- Contact form submissions.
-- Rename the table and adjust columns to match the form's fields.
-- The RLS policy is the security model: public can INSERT, nobody can read,
-- update, or delete through the anon/publishable key.

create table if not exists public.contact_submissions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  project_type text not null,
  details text not null,
  created_at timestamptz not null default now()
);

alter table public.contact_submissions enable row level security;

-- The ONLY policy: anon may insert. No select/update/delete policy exists, so
-- those are denied for the anon role. Verify this empirically after applying
-- (see scripts/test_pipeline.sh) — never assume it's correct.
create policy "anon can insert contact submissions"
  on public.contact_submissions
  for insert
  to anon
  with check (true);
