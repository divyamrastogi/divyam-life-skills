// Emails a notification for each new contact form submission.
// Invoked by the contact_submission_notify trigger (pg_net) on INSERT.
//
// Transport priority: Brevo API (BREVO_API_KEY) -> SMTP (SMTP_USER/PASSWORD)
// -> Resend (RESEND_API_KEY). Brevo alone is enough; the others are optional
// fallbacks so notifications survive one provider being reconfigured.
// The email template lives in ./email.ts.

import { SMTPClient } from "https://deno.land/x/denomailer@1.6.0/mod.ts";
import { buildEmail } from "./email.ts";

const BREVO_API_KEY = Deno.env.get("BREVO_API_KEY");
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
// Comma-separated recipient list
const NOTIFY_TO = (Deno.env.get("CONTACT_NOTIFY_TO") ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const SMTP_USER = Deno.env.get("SMTP_USER");
const SMTP_PASSWORD = Deno.env.get("SMTP_PASSWORD");
const SMTP_HOST = Deno.env.get("SMTP_HOST") ?? "smtp-relay.brevo.com";
const SMTP_PORT = Number(Deno.env.get("SMTP_PORT") ?? "587");
// From-address. SMTP_FROM wins (relays where the login differs from the sender),
// then the authenticated mailbox, then CONTACT_NOTIFY_FROM.
const FROM = Deno.env.get("SMTP_FROM") ??
  (SMTP_USER
    ? `Contact <${SMTP_USER}>`
    : Deno.env.get("CONTACT_NOTIFY_FROM") ?? "Contact <onboarding@resend.dev>");

async function sendViaBrevo(record: Record<string, string>) {
  const { subject, html, text } = buildEmail(record);
  const m = FROM.match(/^(.*)<(.+)>$/); // "Name <email>" -> split for Brevo
  const sender = m ? { name: m[1].trim(), email: m[2].trim() } : { email: FROM };
  const res = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": BREVO_API_KEY!, "Content-Type": "application/json" },
    body: JSON.stringify({
      sender,
      to: NOTIFY_TO.map((email) => ({ email })),
      replyTo: { email: record.email },
      subject,
      htmlContent: html,
      textContent: text,
    }),
  });
  if (!res.ok) throw new Error(`brevo ${res.status}: ${await res.text()}`);
}

async function sendViaSmtp(record: Record<string, string>) {
  const { subject, html, text } = buildEmail(record);
  const client = new SMTPClient({
    connection: {
      hostname: SMTP_HOST,
      port: SMTP_PORT,
      tls: SMTP_PORT === 465, // 465 implicit TLS; 587 STARTTLS
      auth: { username: SMTP_USER!, password: SMTP_PASSWORD! },
    },
  });
  try {
    await client.send({ from: FROM, to: NOTIFY_TO.join(", "), replyTo: record.email, subject, content: text, html });
  } finally {
    await client.close();
  }
}

async function sendViaResend(record: Record<string, string>) {
  const { subject, html, text } = buildEmail(record);
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: FROM, to: NOTIFY_TO, reply_to: record.email, subject, html, text }),
  });
  if (!res.ok) throw new Error(`resend ${res.status}: ${await res.text()}`);
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
  if (NOTIFY_TO.length === 0 || (!BREVO_API_KEY && !RESEND_API_KEY && !(SMTP_USER && SMTP_PASSWORD))) {
    return new Response("missing configuration", { status: 500 });
  }

  let record;
  try {
    ({ record } = await req.json());
  } catch {
    return new Response("bad request", { status: 400 });
  }
  // Adjust required fields to match the form.
  if (!record?.name || !record?.email || !record?.details) {
    return new Response("bad request", { status: 400 });
  }

  try {
    if (BREVO_API_KEY) { await sendViaBrevo(record); return new Response("ok (brevo)", { status: 200 }); }
    if (SMTP_USER && SMTP_PASSWORD) { await sendViaSmtp(record); return new Response("ok (smtp)", { status: 200 }); }
    await sendViaResend(record); return new Response("ok (resend)", { status: 200 });
  } catch (err) {
    console.error("send failed", err);
    return new Response("email send failed", { status: 502 });
  }
});
