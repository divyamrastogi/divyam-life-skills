---
name: supabase-brevo-contact-form
description: >-
  Wire a website contact form to a Supabase table and send a branded email for
  every submission via Brevo. Use this whenever the user wants a contact form,
  lead form, "get in touch" / "start a project" form, enquiry form, or a
  waitlist/signup form that must STORE submissions AND NOTIFY someone by email —
  even if they don't name Supabase or Brevo. Also use it when adding a backend
  to an existing static form, when they ask "where do form submissions go", when
  they want email alerts on new leads, or when reusing an existing Supabase
  project (free-tier 2-project limit) rather than spinning up a new one. Covers
  the insert-only RLS security model, the pg_net trigger → Edge Function → email
  pipeline, Brevo domain authentication, and end-to-end testing.
---

# Supabase + Brevo contact form

Stand up the full pipeline for a website contact/lead form:

```
form submit
  → Supabase REST insert  (table with insert-only RLS)
    → Postgres AFTER INSERT trigger (pg_net, async — never blocks the insert)
      → Edge Function (contact-notify)
        → Brevo API → branded email to the team
```

Everything runs on free tiers. The public key in the form is safe to commit —
its safety comes entirely from RLS, not from hiding it.

## Before you start — gather these

Ask the user for anything not already known. Don't guess; several of these are
credentials only they can provide.

1. **Supabase project** — a *ref* (the `xxxx` in `xxxx.supabase.co`). Reusing an
   existing project is fine and often necessary (free tier allows only 2 active
   projects). If reused, you MUST touch only the new table — never other tables.
2. **Table name** — e.g. `contact_submissions`. Default to that.
3. **Form fields** — default is `name`, `email`, `project_type`, `details`.
   Adjust the migration, form, and email template together if they differ.
4. **Recipient(s)** — where notification emails go. Comma-separated is fine.
5. **Brevo API key** — from the user's Brevo account (Settings → SMTP & API →
   API Keys). The free plan is per *team*; a second team gets its own free slot
   if the first is taken. See `references/brevo-domain-setup.md`.
6. **From address + brand** — e.g. `Acme <hello@acme.com>` and the brand's name
   and accent colour for the email. A from-address on the user's own domain
   needs domain authentication (below); until then, Brevo can send from a
   shared/verified domain.

The `supabase` CLI must be installed and logged in. Confirm with
`supabase projects list`.

## Workflow

Work through these in order. Each step is verifiable before moving on — don't
batch them blindly, because a mistake in the RLS policy or the trigger is much
cheaper to catch here than after the form is live.

### 1. Create the table with insert-only RLS

Copy `assets/migration.sql` into the project's `supabase/migrations/` as
`<UTC timestamp>_<table>.sql` and fill in the table name and columns. The policy
is the security model, so get it right: enable RLS, add **one** policy allowing
`insert` for the `anon` role and nothing else. The public can submit; the public
key can never read, update, or delete.

Apply it:

```bash
supabase link --project-ref <REF>
supabase db push
```

If the project is shared, `db push` still only applies *your* new migration
file — but review it first to be certain it references only the new table.

### 2. Verify the security model empirically

Do NOT trust that the policy is right — prove it. Run
`scripts/test_pipeline.sh` (see step 6) or, minimally, check by hand with the
**publishable/anon key**:

- `POST` a row → expect `201`.
- `GET ...?select=*` → expect `[]` (reads blocked).
- `DELETE ...?id=neq.<impossible>` → may return `204`, but the row count must be
  unchanged. A `204` here is ambiguous; confirm rows survived before trusting it.

This is the single most important check in the whole skill. A form that leaks
every lead to anyone with the (public, committed) key is the failure mode to
rule out.

### 3. Add the Edge Function

Copy `assets/functions/contact-notify/` into the project's
`supabase/functions/`. It has three files:

- `index.ts` — HTTP handler + Brevo send (with optional SMTP/Resend fallback).
- `email.ts` — the branded, email-safe template. Edit the brand name, accent
  colour, and field rows here.
- `theme.ts` — palette. Keep it in sync if the site has a design system.

Set secrets (never commit these — they're read from the environment at runtime):

```bash
supabase secrets set BREVO_API_KEY=<key> --project-ref <REF>
supabase secrets set CONTACT_NOTIFY_TO='a@x.com,b@y.com' --project-ref <REF>
supabase secrets set CONTACT_NOTIFY_FROM='Brand <hello@brand.com>' --project-ref <REF>
```

Deploy with JWT verification **off** — the caller is a Postgres trigger, which
cannot mint a JWT:

```bash
supabase functions deploy contact-notify --no-verify-jwt --project-ref <REF>
```

Test the function directly before wiring the trigger — this isolates
email/Brevo problems from database problems:

```bash
curl -s -X POST https://<REF>.supabase.co/functions/v1/contact-notify \
  -H "Content-Type: application/json" \
  -d '{"record":{"name":"Test","email":"you@example.com","project_type":"Web","details":"hi"}}'
```

Expect `ok (brevo)` and an email in the inbox.

### 4. Wire the trigger

Add `assets/trigger.sql` as a second migration (it's kept separate so you can
deploy the function first — the trigger references its URL). It enables `pg_net`
and creates an `AFTER INSERT` trigger that POSTs the new row to the function.
**Async by design**: a failed email must never roll back or block the insert.
Fill in the project ref in the function URL, then `supabase db push`.

### 5. Add the form to the site

- `assets/form.html` — accessible markup with a hidden success panel and an
  error message.
- `assets/script.js` — submit handler. It POSTs to Supabase REST and handles
  **both** key generations: new `sb_publishable_…` keys go in the `apikey`
  header only; legacy JWT (`eyJ…`) keys also need `Authorization: Bearer`. It
  shows the success panel on `2xx` and re-enables the button on failure.
- Put the project URL and **publishable/anon** key in a `config.js` (or inline).
  This key is public by design; its safety is the RLS policy from step 1.

### 6. Test end to end

Run the bundled script — it does the full RLS proof plus a real insert that
fires the email:

```bash
scripts/test_pipeline.sh <REF> <publishable-or-anon-key> <table>
```

It inserts a clearly-labelled `[TEST]` row (which triggers a real email),
confirms reads/deletes are blocked, and reports the transport used. Tell the
user to check the inbox, and note that test rows accumulate — they can only be
deleted from the Supabase dashboard (the public key can't).

## Key facts worth internalising

- **The anon/publishable key is meant to be public.** Committing it is fine.
  RLS is the wall, not secrecy. If you ever feel tempted to hide the key,
  that's a sign the RLS policy is doing too little.
- **`--no-verify-jwt` is required**, because database triggers can't authenticate.
  Practical exposure is nil beyond what the form already allows (someone could
  POST a fake "lead"); the function validates payload shape and only emails.
- **Reusing a project means strict blast-radius discipline**: migrations name
  only the new table; never alter another app's schema.
- **If the site's whole repo is deployed to a public host** (e.g. Hostinger Git
  deploy serving `public_html`), block backend source, migrations, and secrets
  from being served (an `.htaccess` 404 rule), or the schema becomes readable.
- **Email HTML is not web HTML.** See `references/email-html-rules.md` before
  editing the template: tables not flexbox, inline styles only, no remote images
  for critical branding, always include a plain-text alternative.
- **From-address on the user's domain** needs Brevo DNS authentication
  (DKIM/DMARC). See `references/brevo-domain-setup.md`. Until it's verified, send
  from Brevo's shared domain. Set `reply-to` to the lead so replies reach them.

## Reference material

- `references/brevo-domain-setup.md` — register + DKIM-authenticate a sending
  domain in Brevo (via API or dashboard), and the DNS records involved.
- `references/email-html-rules.md` — the rules that keep the email rendering
  across clients, and how to preview it locally without sending.
- `references/troubleshooting.md` — symptoms → causes for the common failures
  (no email, insert 401, `204` delete scare, blank email in Outlook, etc.).

## Optional niceties (offer, don't impose)

- A tiny task runner (`./sbr`-style shell script) so routine ops — add a
  recipient, send a test, deploy the function — are one command each. Recipient
  management needs a local source-of-truth file because Supabase never reveals a
  secret's value.
- Multi-transport fallback (Brevo → SMTP → Resend) so notifications survive one
  provider being reconfigured. `index.ts` already supports it; just set the
  extra secrets.
