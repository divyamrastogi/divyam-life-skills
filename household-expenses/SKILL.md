---
name: household-expenses
description: Ingest new credit card / bank statement PDFs (Amex, Barclaycard ×2, HSBC) and update the Household Expenses 2025-26.xlsx workbook (recurring, one-off, reimbursable, house views) with validation and Google Drive sync. Use when the user shares new statements or asks to update/reconcile household expenses.
user-invokable: true
args:
  - name: paths
    description: PDF files or folders with new statements (optional; defaults to the watched folders in config.json)
    required: false
---

# Household Expenses — statement ingestion & workbook update

Maintains the household expense analysis workbook from bank/card statement
PDFs. All state lives in: `config.json` (paths — create it from
`config.example.json` on first install; it is machine-specific and never
committed), `ledger.json` (every parsed transaction, on Google Drive next to
the workbook) and the workbook itself.

## Workflow

### 1. Parse the statements
```bash
python3 scripts/parse_statements.py --paths <pdf-or-folder ...>
```
- Parsers: Barclays (per-line regex, validated against the printed
  "Transactions, interest and charges £X"), Amex (paired-date lines, bare
  `CR` marks the previous row as a credit), HSBC (word x-columns for
  paid-out/paid-in/balance; validated by balance walk == ClosingBalance and
  sums == Payments In/Out box).
- A statement that fails validation raises — investigate, don't skip.
- Output JSON: `new` = transactions not yet in the ledger (direction `cr`
  true = money in / refund).

### 2. Classify every new transaction
Follow `references/categories.md` — one-off category / recurring item /
reimbursable / excluded. Rules that matter most:
- Card payments, own-account transfers, salary, Hengameh parking credits are
  NEVER spend (parser already drops the obvious ones).
- Refunds net against their category (negative amount).
- TfL / Trainline / Better badminton / dental → Reimbursable.
- Ask the user only when a charge is genuinely ambiguous and material (>£50).

### 3. Commit the ledger (only after a clean parse)
```bash
python3 parse_statements.py --commit --paths <same paths>
```

### 4. Update the workbook
Write the classified one-offs to a temp JSON:
```json
{"oneoff": [{"category": "Flights & hotels", "source": "Amex",
             "who": "Divyam", "date": "2026-09-14",
             "desc": "EASYJET LONDON", "amount": 210.00}]}
```
then:
```bash
python3 scripts/update_workbook.py /tmp/oneoff.json
```
It appends to both one-off sheets, keeps their totals in lockstep, verifies
and backs up the workbook first. It does NOT touch recurring lines — update
those by hand per `references/workbook_map.md` when a recurring merchant's
rate changes, and add a Summary note for any category correction.

### 5. QA + sync
- Verify one-off sheet totals agree (script already asserts; re-check per
  workbook_map.md QA block).
- Sync: `cp "<local workbook>" "<workbook_drive>"` (paths in config.json —
  filesystem copy of the Google Drive mount; never use Google APIs).

### 6. Report
Statement count, new transactions, what was excluded and why, one-off total
before/after, and anything that needs the user's judgment.

## Guardrails
- NEVER edit the workbook without a same-day backup (update_workbook.py does
  this automatically).
- NEVER count card payment settlements or own-account transfers as spend.
- Identical same-day charges are usually real (multiplicity is preserved).
- Keep 'One-off Expenses', 'One-off transactions' and the House sheet
  consistent — they are three views of the same transactions.
- If a statement PDF has a layout the parsers don't recognise, fix the parser
  (with a validation test), don't hand-edit the ledger.
