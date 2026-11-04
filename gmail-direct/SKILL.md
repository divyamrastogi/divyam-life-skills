---
name: gmail-direct
description: "Permanent Gmail access for divyamsuperb@gmail.com via app password (IMAP/SMTP). Use for checking email, reading messages, sending mail, saving drafts — e.g. 'check my email', 'send X the invoice', 'did payment confirmation arrive'. No OAuth, never expires."
---

# Gmail Direct (permanent access)

App password `OpenClawMail` stored in macOS keychain (service: `gmail-app-password`, account: divyamsuperb@gmail.com). Never log it, never commit it, never echo it.

## Commands (script handles auth)
```bash
python3 ~/clawd/skills/gmail-direct/scripts/mail.py list "newer_than:7d" 10   # search (Gmail syntax)
python3 ~/clawd/skills/gmail-direct/scripts/mail.py read 97847               # read message by uid
python3 ~/clawd/skills/gmail-direct/scripts/mail.py send <to> "<subject>" "<body>" "<attach1.csv,attach2.pdf>"
python3 ~/clawd/skills/gmail-direct/scripts/mail.py draft <to> "<subject>" "<body>"   # saves to Gmail Drafts
```

## Rules
- Sending to external addresses: confirm with Divyam first (standing rule), except invoice flows he's pre-approved.
- Large searches: use Gmail operators (from:, newer_than:, subject:).
- Keychain recovery: `security find-generic-password -s gmail-app-password -w`
