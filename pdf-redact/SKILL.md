---
name: pdf-redact
description: >
  Redact transactions from a PDF bank or credit-card statement, keeping only
  the ones the user wants and blacking out everything else. Use whenever the
  user says things like "keep only travel", "redact everything except X",
  "filter this statement to Y", "I only want to show travel spending", or
  hands over a PDF statement and asks to strip/hide/remove transactions by
  category or keyword. Triggers on the combination of a PDF + a keep/filter
  intent, even when the word "redact" is never used.
---

# pdf-redact

Redact (black out) every transaction on a credit-card or bank PDF *except* the
ones the user wants to keep. The user states a keep intent — a category like
"travel", a merchant like "tfl", or a mix — and this skill produces a new PDF
where all other transactions are covered with black bars and their amounts
removed. The kept transactions are summed and reported.

The engine lives in the pdf-redact project at `~/projects/pdf-redact`
(override with the `PDF_REDACT_PROJECT` env var). It auto-detects the statement
provider (American Express, Barclaycard, or generic) and applies the right
layout-aware redactor. Don't reimplement the redaction logic — call the script.

## When to use this skill

Trigger when the user provides (or points at) a PDF statement **and** asks to
keep/filter/redact/show only a category or keyword. Examples of phrasing to
treat as a trigger:

- "Keep only travel"
- "Redact everything except TFL and Trainline"
- "Filter this statement to groceries"
- "I only want to show my travel spending"
- "Strip out everything that isn't food or fuel"
- "Here's my statement — keep just trainline/oyster"

If the user only sends a PDF with no keep intent, ask what they want to keep
before running anything.

## The one command

Run `scripts/redact.py` with the project's `venv` (the one with the pinned
PyMuPDF — see "PyMuPDF version" below):

```bash
~/projects/pdf-redact/venv/bin/python ~/clawd/skills/pdf-redact/scripts/redact.py \
  "<input.pdf>" "<output.pdf>" --keep travel
```

Add `--json` to get machine-readable output for downstream steps:

```bash
~/projects/pdf-redact/venv/bin/python ~/clawd/skills/pdf-redact/scripts/redact.py \
  "<input.pdf>" "<output.pdf>" --keep travel --json
```

The script prints the whitelisted total and the output path. With `--json` it
emits `{"ok": true, "output": ..., "total_kept": ..., "kept_count": ...,
"keywords": [...]}`.

The engine logs a verbose per-span trace by default; the script suppresses it
to WARNING. Set `PDF_REDACT_VERBOSE=1` if you ever need the engine's full log
to debug a mis-detection.

### Args

- `input` / `output` — PDF paths. Always put the output in a writable location
  (e.g. the user's current working directory, not inside the project repo).
- `--keep` — comma-separated list of **categories** and/or **raw keywords** to
  keep. Order doesn't matter; case-insensitive. Examples: `travel`,
  `travel,groceries`, `tfl,oyster,trainline`, `travel,acme corp`.
- `--provider` — `auto` (default), `amex_uk`, or `barclaycard`. Leave on
  `auto`; it detects from the PDF text and filename.
- `--list-categories` — print the category → keyword map and exit.
- `--json` — emit JSON on stdout (hints still go to stderr).

### Built-in categories

The script maps a category name to a keyword list and matches case-insensitively
as a **substring** against transaction text. Run `--list-categories` for the
authoritative list. Summary:

| Category       | Examples (not exhaustive)                                            |
| -------------- | ------------------------------------------------------------------- |
| `travel`       | trainline, tfl, transport for london, oyster, national rail, uber, bolt, heathrow express, easyjet, ryanair, british airways |
| `groceries`    | tesco, sainsbury, asda, aldi, lidl, waitrose, m&s food, co-op, morrisons, ocado |
| `food`         | deliveroo, just eat, ubereats, mcdonald, pret a manger, costa, starbucks, greggs |
| `subscriptions`| netflix, spotify, disney, prime video, apple, google, hyperoptic, vodafone, sky |
| `fuel`         | shell, bp, esso, texaco, tesco fuel                                 |
| `utilities`    | octopus, british gas, edf, thames water                             |

Any `--keep` token that **isn't** a category name is treated as a raw keyword,
so users can mix freely: `--keep travel,gym,acme corp` keeps travel merchants
plus literal matches for "gym" and "acme corp".

If a user asks for a category the script doesn't know (e.g. "keep only
charitable donations"), ask for one or two example merchant names and pass
those as raw keywords. Don't guess keywords silently.

## Workflow

1. **Locate the input PDF.** If the user attached a file, find its path. If
   they pasted a path, use it. If you can't find it, ask.
2. **Parse the keep intent** into a `--keep` value:
   - Category phrasing ("just travel", "food only") → category name(s).
   - Named merchants ("keep TFL and Trainline") → raw keywords.
   - Both → mix freely, comma-separated.
3. **Choose an output path** in the user's working directory. Default to
   `<input-stem>_redacted.pdf` in the same folder as the input unless the user
   named a destination.
4. **Run the script** with `--json`. Parse the result; if `ok` is false or the
   process exits non-zero, read the error from stderr and report it to the user
   — don't try to "fix" the PDF by hand.
5. **Report back** the output path, the kept total, and the keyword list the
   engine actually matched on. Offer to adjust the keep list and re-run if the
   result doesn't look right.

## Important notes

- **PyMuPDF version matters — and the script enforces it.** The project pins
  `PyMuPDF==1.27.2`. Older versions merge text spans differently and *silently*
  miss transactions on Barclaycard statements (the coordinate-sensitive path) —
  this is exactly the bug in project commit `7ae4bc0`; the output looks fine but
  rows are wrong. So the script **refuses to run** under PyMuPDF < 1.27 rather
  than ship a silently-bad redaction. The project has two venvs: use
  `~/projects/pdf-redact/venv/` (has 1.27.2), **not** `.venv/` (has 1.24.10,
  broken). If the script errors on version, run with the correct venv or
  `~/projects/pdf-redact/venv/bin/pip install 'PyMuPDF==1.27.2'`.
- **Keyword matching is a substring test**, not whole-word or regex. "fuel"
  also matches "Misfuel"; "bp" can match inside other words. If the user cares
  about precision, suggest more specific keywords.
- **This is a destructive-looking but non-destructive operation.** The input
  PDF is never modified — a new redacted PDF is written to the output path.
  Redaction bars are burned into the output (applied, not annotations), so the
  redacted text is not recoverable from the output.
- **The engine sums the kept amounts** and (for Barclaycard statements) prints
  a green "Whitelisted transactions total" box on page 2 of the output.
- **Privacy path is intentionally not exposed.** The web app has an
  "enhanced privacy" mode, but it carries statement-specific personal-data
  overrides and only works for AMEX. If the user needs full financial-detail
  redaction (name, card number, balance), tell them that mode isn't available
  through this skill yet.
- **Keep the user's data in their environment.** Don't upload the PDF or its
  contents anywhere. The script runs locally against the project checkout.

## Examples

User: "Here's my statement `/Users/me/july.pdf`, keep only travel"
→ Run with `--keep travel`, output to `/Users/me/july_redacted.pdf`, report
  the travel total and matched keywords.

User: "Redact everything except TFL and Trainline from july.pdf"
→ Run with `--keep tfl,trainline` (raw keywords), report total.

User: "I want to see just groceries and my gym membership"
→ Run with `--keep groceries,gym` (groceries expands; gym is a raw keyword),
  report total. If "gym" over-matches, offer to narrow to a specific gym name.

User: "Keep only travel" with no file
→ Ask which PDF to process.
