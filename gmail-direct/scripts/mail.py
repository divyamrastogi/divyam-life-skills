#!/usr/bin/env python3
"""Permanent Gmail access via app password (IMAP/SMTP). Password lives in macOS keychain."""
import imaplib, smtplib, sys, email, os, getpass
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

USER = "divyamsuperb@gmail.com"

def getpwd():
    out = os.popen("security find-generic-password -s gmail-app-password -w 2>/dev/null").read().strip()
    if out: return out
    return getpass.getpass("Gmail app password: ")

def connect():
    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(USER, getpwd())
    m.select("INBOX")
    return m

def cmd_list(query, n=10, mailbox="INBOX"):
    m = connect()
    if mailbox.lower() in ("sent", "sent mail"):
        mailbox = '"[Gmail]/Sent Mail"'
    m.select(mailbox)
    try:
        typ, data = m.search(None, "X-GM-RAW", f'"{query}"' if query else "ALL")
    except imaplib.IMAP4.error:
        # OR/paren queries can fail BAD on Gmail IMAP; fall back to plain text search
        typ, data = m.search(None, "TEXT", f'"{query}"')
    ids = data[0].split()[-int(n):]
    for i in reversed(ids):
        typ, d = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        raw = d[0][1].decode("utf-8", "ignore")
        msg = email.message_from_string(raw)
        print(f"[{i.decode()}] {msg.get('Date','')[:16]} | {msg.get('From','')[:40]} | {msg.get('Subject','')[:70]}")
    m.logout()

def cmd_read(uid):
    m = connect()
    typ, d = m.fetch(uid, "(BODY.PEEK[])")
    msg = email.message_from_bytes(d[0][1])
    print(f"From: {msg.get('From')}\nDate: {msg.get('Date')}\nSubject: {msg.get('Subject')}\n")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8","ignore"); break
    else:
        body = msg.get_payload(decode=True).decode("utf-8","ignore")
    print(body[:3000])
    m.logout()

def cmd_send(to, subject, body, attach=None):
    m = EmailMessage()
    m["From"] = USER; m["To"] = to; m["Subject"] = subject
    m.set_content(body)
    if attach:
        for path in attach.split(","):
            with open(path.strip(), "rb") as f:
                m.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=os.path.basename(path.strip()))
    s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
    s.login(USER, getpwd()); s.send_message(m); s.quit()
    print(f"SENT → {to} | {subject}" + (f" | attachments: {attach}" if attach else ""))

def cmd_draft(to, subject, body):
    m = connect()
    msg = EmailMessage(); msg["From"] = USER; msg["To"] = to; msg["Subject"] = subject
    msg.set_content(body)
    m.append('"[Gmail]/Drafts"', None, None, msg.as_bytes())
    print(f"DRAFT saved → {to} | {subject}")
    m.logout()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list": cmd_list(sys.argv[2] if len(sys.argv) > 2 else "", sys.argv[3] if len(sys.argv) > 3 else 10, sys.argv[4] if len(sys.argv) > 4 else "INBOX")
    elif cmd == "read": cmd_read(sys.argv[2])
    elif cmd == "send": cmd_send(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "draft": cmd_draft(sys.argv[2], sys.argv[3], sys.argv[4])
    else: print("usage: mail.py list [query] [n] [mailbox=INBOX|sent] | read <uid> | send <to> <subject> <body> [attachments-csv] | draft <to> <subject> <body>")
