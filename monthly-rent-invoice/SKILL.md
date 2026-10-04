---
name: monthly-rent-invoice
description: Use when Divyam asks to generate, create, make, or sign the monthly office-rent tax invoices for Emami Agrotech (lessors Deeksha Rastogi and Divyam Mukesh Rastogi), or invoices for a specific month like "the July rent invoices" / "rent invoice for August 2026". Produces two final, non-editable, pre-signed PDFs — one per person — with correct auto-incremented invoice numbers.
---

# Monthly Rent Invoice

## Overview
Generates the monthly office-rent **Tax Invoices** billed to Emami Agrotech Limited. The rent is split equally and issued as **two separate invoices per month — one for Deeksha Rastogi, one for Divyam Mukesh Rastogi** — each with that person's own PAN, bank account, and signature.

Output is **flat (non-editable)**: all values are baked in as text with no form fields, so a sent invoice can't be altered.

**Invoice number rule:** one shared series, two per month, **Deeksha takes the odd number, Divyam the even**. Anchored at June 2026 = `001`/`002`. The `INV-2026` prefix is the fixed lease series and does *not* change with the calendar year.

## When to Use
- "Generate / make / create the rent invoices for <month>"
- "I need the August 2026 invoices"
- "Send me just Deeksha's invoice for September"

## Usage
```bash
python3 scripts/invoice_generator.py "July 2026"                 # both invoices -> cwd
python3 scripts/invoice_generator.py 2026-08 /path/to/outdir     # both -> outdir
python3 scripts/invoice_generator.py "July 2026" --only deeksha  # just one
python3 scripts/invoice_generator.py Jul                         # year defaults to 2026
```
Month accepts `"July 2026"`, `2026-07`, `08/2026`, `Jul`, or `7`. `--only` takes `deeksha` or `divyam`.

The script prints each lessor's invoice number, date, and output path. Files are named
`Tax_Invoice_<INVNO>_<Full_Name>_<Month>_<Year>.pdf`. **Relay the output paths to the user.**

Requires `reportlab` (`pip install reportlab`). Known-good interpreter on this Mac:
`/Users/deeksharastogi/projects/pdf-redact/venv/bin/python`.

## Invoice Number Reference
| Month | Deeksha | Divyam |
|-------|---------|--------|
| June 2026 | INV-2026-001 | INV-2026-002 |
| July 2026 | INV-2026-003 | INV-2026-004 |
| Aug 2026 | INV-2026-005 | INV-2026-006 |
| Dec 2026 | INV-2026-013 | INV-2026-014 |
| Jan 2027 | INV-2026-015 | INV-2026-016 |

Formula: `monthIndex = (year - 2026) * 12 + (month - 6)`; Deeksha = `monthIndex * 2 + 1`, Divyam = `monthIndex * 2 + 2`. Months before June 2026 are rejected.

## What Changes vs. What's Fixed
- **Per month (auto-computed):** invoice number, date (always the 1st, `DD/MM/YY`), and the description period (`01 <Month> <Year>` to `<last day> <Month> <Year>`, leap-year aware).
- **Per person (in `LESSORS`):** name, PAN, email, bank, IFSC, account number, signature file.
- **Fixed constants:** `RENT_HALF` ₹46,450.80 each, `ROUND_OFF` ₹0.20, `TOTAL` ₹46,451.00, area, HSN, bill-to details.

If the **rent changes**, edit `RENT_HALF` / `ROUND_OFF` / `TOTAL` at the top of `scripts/invoice_generator.py` — the amount-in-words line is generated automatically from `TOTAL` (Indian numbering), so it stays in sync.

## Notes
- Output is non-editable by design — to change the month, re-run the script rather than editing the PDF.
- Bill-to GSTIN `09AABCN7953M1ZT` (Noida premises; updated 2026-09-10 per Divyam, checksum-verified — the old 19AABCN7953M1ZS Kolkata one is outdated).
- Signatures (`scripts/sig_deeksha.png`, `scripts/sig_divyam.png`) are transparent PNGs and must stay alongside the script.
