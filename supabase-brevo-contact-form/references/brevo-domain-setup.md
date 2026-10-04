# Brevo setup & domain authentication

## Getting an API key

Brevo dashboard → **Settings → SMTP & API → API Keys → Generate a new API key**.
There's a separate "SMTP" tab (SMTP credentials) — for this pipeline you want an
**API key** (`xkeysib-…`). The free plan (300 emails/day) is per **team**; if the
account's one free domain slot is already used, create a second team (top-left
team switcher → Create team) for its own free slot.

The key is a credential — only the user can generate it. Store it as a Supabase
secret (`BREVO_API_KEY`), never in the repo.

## Sending from the user's own domain (recommended)

Until a domain is authenticated, send from Brevo's shared/verified domain. To
send as `hello@theirdomain.com`, authenticate the domain — this adds DKIM so
mail isn't spoofable and lands in inboxes.

### Via the API (if you have the key)

Register the domain:

```bash
curl -s -X POST https://api.brevo.com/v3/senders/domains \
  -H "api-key: $BREVO_API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"theirdomain.com"}'
```

The response's `dns_records` lists what to add:

- `dkim1Record` — CNAME `brevo1._domainkey` → `b1.<domain-dashed>.dkim.brevo.com`
- `dkim2Record` — CNAME `brevo2._domainkey` → `b2.<domain-dashed>.dkim.brevo.com`
- `brevo_code`  — TXT `@` → `brevo-code:<hash>`
- `dmarc_record`— TXT `_dmarc` → `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com`

Add those records at the DNS provider (many hosts have an API/MCP for this —
e.g. Hostinger DNS tools). Then trigger verification:

```bash
curl -s -X PUT https://api.brevo.com/v3/senders/domains/theirdomain.com/authenticate \
  -H "api-key: $BREVO_API_KEY"
```

DNS propagation can take minutes; poll the authenticate endpoint until it returns
`"authenticated":true`. Verify records resolve first with
`dig +short CNAME brevo1._domainkey.theirdomain.com`.

### Via the dashboard (if you only have an SMTP key)

Brevo → **Senders, Domains & Dedicated IPs → Domains → Add a domain**. It shows
the same records; add them to DNS, then click **Authenticate**.

## Notes

- **Send-only is fine.** The from-address (`hello@theirdomain.com`) doesn't need
  a real mailbox behind it. Every notification sets `reply-to` to the lead, so
  replies reach the lead — not a dead address.
- **DMARC `p=none`** is monitor-only and the right default. Don't tighten it to
  `quarantine`/`reject` without first confirming all of the domain's senders pass.
- **Free-tier branding:** Brevo's free plan adds a small "sent with Brevo"
  footer. Fine for internal lead alerts. If it must be removed, that's a paid
  plan or a different provider (SMTP2GO's 1,000/mo free has no branding).
