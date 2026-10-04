---
name: whatsapp-drive-saver
description: Save documents from WhatsApp group chats to Google Drive. Use when a document (PDF, image, etc.) is shared in the "Medical Records Ghaziabad" WhatsApp group, or when asked to save/move a WhatsApp attachment to Drive. Automatically determines the right person's folder based on the report content/caption.
---

# WhatsApp → Google Drive Saver

## Group: "Family Documents" (standing rule, Divyam 2026-09-12)
- Respond to @mentions only; otherwise stay silent.
- Any document (PDF/image/etc.) posted → save to `"$GDRIVE/Family Documents/"` under the right subfolder (Aadhaar/PAN/Passport/Bank/Health Insurance/Insurances/Medical Reports/Rental Agreements/etc.; person subfolder where applicable).
- Name files descriptively (`<Type> <DD-MM-YYYY>.<ext>`); skip duplicates (check by keyword/media hash first).
- Group ID: TBD — confirm from the session key on first inbound, then record it here.

## How It Works

1. WhatsApp media is auto-downloaded to `~/.openclaw/media/inbound/` (filename: `<media-id>---<uuid>.<ext>`)
2. Save directly to the **local Google Drive sync folder** — it auto-syncs to the cloud, no API needed

## Local Drive Path

```
GDRIVE="/Users/deeksharastogi/Library/CloudStorage/GoogleDrive-divyamsuperb@gmail.com/My Drive"
MEDICAL="$GDRIVE/Family Documents/Medical Reports"
```

## Folder Structure (already exists)

```
Family Documents/Medical Reports/
├── Chhaya Mummy/
│   ├── Endometrial Carcinoma/
│   │   ├── 00 - Surgery (07 Jan 2025) (1)/
│   │   ├── 01 - Chemo 1 .../
│   │   ├── Blood Tests (1)/
│   │   └── Reports/
│   └── (other files)
├── Mukesh/
│   ├── 2022/, 2023/, 2024/
│   └── (other files)
├── Achyut/
├── Deeksha/
├── Divyam/
├── Divya/
├── Bipul Rastogi Papaji/
└── Sonal Rastogi/
```

## Workflow

### Step 1 — Find the inbound file
```bash
ls -lt ~/.openclaw/media/inbound/ | head -5
```
Match by recent timestamp or media ID from the message.

### Step 2 — Identify whose report it is
- Read the message caption/context
- If unclear, use `pdftotext <file> - | head -30` to find the patient name

### Step 3 — Determine the right subfolder
- **Chhaya Mummy** reports: check if it's related to Endometrial Carcinoma (surgery, chemo, blood tests, IHC, MRI etc.) → use appropriate subfolder; otherwise save in `Chhaya Mummy/`
- **Mukesh** reports: check the year, save in `Mukesh/20XX/` — create the year folder if needed
- **Others**: save directly under their name folder; create if missing

### Step 4 — Copy with a descriptive name
```bash
cp ~/.openclaw/media/inbound/<file> "$MEDICAL/<Person>/<subfolder>/<Descriptive Name DD-MM-YYYY>.pdf"
```
Name format: `<Report Type> <DD-MM-YYYY>.pdf` (e.g. `IHC MMR Report 08-01-2025.pdf`, `CBC Report 18-02-2026.pdf`)

### Step 5 — Check for duplicates first
```bash
ls "$MEDICAL/<Person>/" | grep -i "<keyword>"
```
If the same media ID already exists in the folder, skip the copy — it's a duplicate.

## Rules
- Send **one** concise message when done (no progress updates)
- If genuinely unsure whose report it is, ask before saving
- `pdftotext` is available for reading PDF content
