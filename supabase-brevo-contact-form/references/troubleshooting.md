# Troubleshooting

Symptom → likely cause → fix.

## Insert fails (form shows the error message)

- **401 / "No API key found"** — the `apikey` header is missing or wrong. Check
  `config.js` has the **publishable/anon** key, not empty. For a legacy JWT key,
  the `Authorization: Bearer` header is also required (`script.js` adds it when
  the key starts with `eyJ`).
- **401 / "new row violates row-level security"** — RLS is on but there's no
  insert policy for `anon`, or the policy's `with check` is false. Re-apply the
  migration's policy.
- **400 / column errors** — the payload keys don't match the table columns. Align
  the form field `name`s, the table, and the function's required-field check.

## Reads are NOT blocked (test step 2 returns rows)

There's a `select` policy for `anon`, or RLS isn't enabled. Enable RLS and delete
any non-insert policy. This is a data leak — fix before going live.

## The DELETE test returned 204 and I panicked

`204` is ambiguous (PostgREST returns it even when the filter matched nothing).
The real proof reads didn't leak is test step 2. Confirm rows still exist via the
dashboard; the insert-only policy means nothing was deleted.

## No email arrives

Test the function directly (skill step 3) to isolate DB vs email:

- **Function returns 500 "missing configuration"** — `CONTACT_NOTIFY_TO` or
  `BREVO_API_KEY` secret isn't set. `supabase secrets set …`, then no redeploy
  needed (secrets are read per-invocation).
- **Function returns 502 "email send failed"** — check the function logs
  (`supabase functions logs contact-notify` or the dashboard). Usually a bad
  Brevo key, or sending from an unverified domain — send from Brevo's shared
  domain until the domain is authenticated.
- **Function returns 200 but nothing in inbox** — check spam (new sending
  domains land there first; mark "not spam" once to train). Confirm
  `CONTACT_NOTIFY_TO` is the address you're checking.
- **Insert works but the trigger never calls the function** — `pg_net` not
  enabled, or the trigger's function URL is wrong. Re-check `trigger.sql`, that
  `<REF>` is filled in, and that the function was deployed **before** the trigger.

## Function deploy or trigger call is rejected with 401

The function was deployed without `--no-verify-jwt`. A Postgres trigger can't
mint a JWT, so redeploy: `supabase functions deploy contact-notify --no-verify-jwt`.

## Email looks broken (blank in Outlook, distorted shapes)

See `references/email-html-rules.md`. Outlook shows only a GIF's first frame;
coloured cells need explicit dimensions; images may be blocked — never rely on
them for essential content.

## Backend source is readable on the live site

If the host deploys the whole repo to a public web root (e.g. Hostinger Git
deploy), `supabase/…` source and migrations get served. Add a rule that 404s
those paths (`.htaccess`: `RedirectMatch 404 ^/supabase(/|$)` etc.). Lead data
itself stays protected by RLS regardless.
