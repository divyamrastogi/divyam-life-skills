---
name: gmail-direct
description: "Permanent Gmail access for divyamsuperb@gmail.com via app password (IMAP/SMTP). Use for checking email, reading messages, sending mail, saving drafts — e.g. 'check my email', 'send X the invoice', 'did payment confirmation arrive'. No OAuth, never expires."
---

# Gmail Direct (permanent access)

App password `OpenClawMail` stored in macOS keychain (service: `gmail-app-password`, account: divyamsuperb@gmail.com). Never log it, never commit it, never echo it.

## Commands (script handles auth)
```bash
python3 ~/clawd/skills/gmail-direct/scripts/mail.py list "newer_than:7d" 10   # search INBOX (Gmail syntax)
python3 ~/clawd/skills/gmail-direct/scripts/mail.py list "from:x has:attachment" 6 sent  # search a mailbox: INBOX (default) or sent
python3 ~/clawd/skills/gmail-direct/scripts/mail.py read 97847               # read message by uid
python3 ~/clawd/skills/gmail-direct/scripts/mail.py send <to> "<subject>" "<body>" "<attach1.csv,attach2.pdf>"
python3 ~/clawd/skills/gmail-direct/scripts/mail.py draft <to> "<subject>" "<body>"   # saves to Gmail Drafts
```

## Pitfalls (verified 2026-11-05)
- **Drafts must append to `'"[Gmail]/Drafts"'`** — appending to bare `Drafts` silently succeeds but the message never appears in Gmail's Drafts folder. (Script already fixed; keep it that way.)
- **`X-GM-RAW` rejects parenthesised OR queries** (`from:x (A OR B)` → `BAD Could not parse`). The script falls back to a TEXT search on error — results are looser, so verify matches by subject before citing. Prefer simple `from:`/`has:attachment` queries that work directly.
- Fetching by stale uid can return `(int, None)` — re-search instead of reusing old uids across sessions.

## Rules
- Sending to external addresses: confirm with Divyam first (standing rule), except invoice flows he's pre-approved.
- Large searches: use Gmail operators (from:, newer_than:, subject:).
- Keychain recovery: `security find-generic-password -s gmail-app-password -w`
