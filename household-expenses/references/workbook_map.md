# Workbook Map — "Household Expenses 2025-26.xlsx"

Path: `~/​.zcode/workspace/default/Household Expenses 2025-26.xlsx`
(local working copy; ALWAYS copy to the Drive path in config.json after saving —
Drive location: `My Drive/Family Documents/Home Purchase/`. Statements and
ledger.json stay in `My Drive/Sync/Bank & Card Statements/`; never sync the
workbook back there.)
Sheet order: Summary · Recurring (Annual) · One-off Expenses · One-off
transactions · Reimbursable · House (Golding House) · (one-off) House
(Golding House) · (cash-in) House (Golding House) · (all tx) House
(Golding House) · Your-Saving detail · Dining detail · (charts) Variable
expenses · Sources & Notes. (Sheet names must stay ≤31 chars for Excel.)

Conventions everywhere: borderless design, table header at row 4, data from
row 5, GBP format `£#,##0.00` (annual figures) / `£#,##0` (monthly), live SUM
formulas for totals, `wb.properties.creator = "Z.ai"`, row heights cap 409.

## Summary
- Row 2 title. Row 4 header (Metric|Value). KPI rows 5–11:
  5 recurring NON-HOUSE `='Recurring (Annual)'!F16` · 6 per-month ·
  7 one-offs `='One-off Expenses'!E13` · 8 reimbursable `='Reimbursable'!F9` ·
  9 house recurring `='House (Golding House)'!E15` · 10 house one-offs &
  furniture `='(one-off) House (Golding House)'!F19` · 11 cash put into house
  `='(cash-in) House (Golding House)'!E10`
- Notes below KPIs (merged B:E, `font_caption`) — append correction history
  here whenever categories change.

## Recurring (Annual) — NON-HOUSE only: rows 5–15 (11 items), TOTAL row 16
Cols: B # | C Item | D Group | E Basis | F Annual £ | G Monthly `=ROUND(F/12,0)` | H pattern notes.
Rows: 5 Card fees · 6 Ayur-Vaidya · 7 Spusu · 8 Claude · 9 Z.ai ·
10 Cineworld · 11 Apple · 12 Amazon Prime · 13 Dining (£5,302.70 — £6,186
observed ×12/14; Ragam £414.23 group dinner counted at 1/10 share £41.42) ·
14 Personal transport (£1,701.57) · 15 Entertainment. TOTAL `=SUM(F5:F15)`
(£16,692.27/yr; combined with house £51,979.27/yr). House recurring items
do NOT live here — they are real
values on 'House (Golding House)'. Water (East Midlands £1,295, May 2026)
is a ONE-OFF ('Home, furniture & repairs' + '(one-off) House' sheet).
Changing a row: update F (annual), D (basis) and H (certainty notes) together.

## One-off Expenses — rows 5–12, TOTAL row 13 (`=SUM(E5:E12)`)
Cols: B # | C Item (category) | D Detail prose | E Amount £ | F transaction
list (one per line `DD Mon YY  £X.XX  desc`, chronological, refunds as `−£`).
Rows: 5 Shopping & electronics · 6 Visa & immigration · 7 Flights & hotels ·
8 Home, furniture & repairs · 9 Unclassified card spending · 10 Personal &
services · 11 Small tech / services · 12 Days out & attractions.
`update_workbook.py` maintains E and F; refresh D prose manually.

## One-off transactions — data rows 5..N, TOTAL last, auto-filter B4:F{N}
Cols: B Category | C Source (`Amex (Divyam)` / `Barclaycard (Deeksha)` /
`Barclaycard (Divyam)` / `HSBC (Divyam)`) | D Date `DD Mon YY` | E Description |
F Amount £ (negatives = refunds). `update_workbook.py` inserts before TOTAL
and extends the SUM + filter. Keep this sheet and 'One-off Expenses' in
lockstep — the script asserts their totals match.

## Reimbursable — rows 5–8, TOTAL row 9
TfL £1,602.26 obs/£1,373.37 ann · Trainline £228.18/£195.58 · Badminton
(Better) £78/£312 · Dental £455/£420. Cols: E Observed £ | F Annual £.

## House (Golding House) — recurring house expenses (REAL values, not refs)
Rows 5–14: Mortgage 21,289.44 · RMG 4,400 · Ground rent 750 · Council tax
2,575 (26/27 instalments £257.51/mo; 25/26 bill £2,487.85 verified — Barnet
£1,888.50 + GLA £599.35, Band E; 24/25 ≈£2,375) · Energy 840 · Broadband 252
· UInsure 224 · Life insurance 470 · Your-Saving 2,121.56 · Groceries 1,925.
TOTAL row 15 `=SUM(E5:E14)` (£34,847/yr) + monthly col F `=ROUND(E/12,0)`.
Notes 17–23 (22 = mortgage rate history; 23 = Halifax annual statement facts:
4.57% fixed to 31 Mar 26, interest £15,481.88 in 12 mo to Oct 25, £31,100
overpayments Oct 24–Oct 25). Edit house run-rate items HERE (col E), never
on 'Recurring (Annual)'.

## (one-off) House (Golding House) — one-off house expenses + furniture
B # | C Date | D Description | E Source | F Amount. Statement-window rows
5–9 (chairs £95, Anjali Patel £496, ElecMec £269.57, East Midlands Water
£1,295). Row 10 = furniture subheading; rows 11–18 = manual furniture
(2024, pre-statement-window: beds £2,000 + £300, sofa £700, IKEA £260/400/
200/100/150). TOTAL row 19 `=SUM(F5:F18)` = £6,265.57. Summary KPI refs F19.
Mirror rule: statement-window one-offs ALSO go to 'One-off Expenses' row 8 +
'One-off transactions'; pre-window manual furniture lives ONLY here (adding
it to the 14-month statement sheets would distort them).

## (cash-in) House (Golding House) — total money put into the house
B # | C Item | D Detail | E Amount. Rows 5–9: initial deposit £100,000 (May
24 — house acquired May 2024) · additional deposits £100,000 (to Oct 25 —
£54,502 VERIFIED as Halifax overpayments: £12,000 Jun 24 + £8,998 Aug 24 +
£2,000+£100 Jan 25 + £5,000+£1,000+£5,000 Mar 25 + £5,000 May & Jun 25 +
£3,000 Jul 25 + £5,000 Aug 25 via HSBC (Divyam)/Halifax stmt, + £2,404 on
06 Oct 25 via HSBC (Deeksha); balance trajectory verified: £400,000 at
outset (02 May 24) → £314,542.54 (02 Oct 25, Halifax stmt) → £312,138.54 →
£300,000 at the Apr 26 remortgage) · mortgage Jun 24–Jul 25 VERIFIED
£32,184.00 (14 payments: £3,738.43 first + 11 × £2,236.33 + 2 × £1,922.97 —
estimate retired) · mortgage Aug 25–Aug 26 VERIFIED £22,510.59 (8 ×
£1,922.97 incl. the previously-missed 1 Aug 25 + £2,256.13 Apr 26 −
£2,256.13 refunded 14 Apr 26 + £1,804.47 + 3 × £1,774.12) · one-offs &
furniture = live ref `='(one-off) House (Golding House)'!F19`. TOTAL row 10
`=SUM(E5:E9)` ≈ £260,960.16 (overpayments counted once, inside the £100k
deposits line). Mortgage rate history (verified): £3,738.43 first payment
Jun 24 → £2,236.33/mo (Jul 24–May 25) → £1,922.97/mo (Jun 25–Mar 26) →
£2,256.13 final old payment Apr 26 (refunded 14 Apr 26) → remortgage May 26
£1,804.47 first → £1,774.12/mo from Jun 26.
Update row 4 each month a new mortgage DD lands in the ledger.

## (all tx) House (Golding House) — every house transaction + subtotals
Summary table rows 5–11 (Category | # tx | Subtotal, live refs to the detail
subtotal rows). Detail from row 14: per-category bold header, chronological
tx rows (B # | C Date | D Description | E Source | F Amount), per-category
Subtotal `=SUM`, grand TOTAL = sum of subtotal cells. Six categories:
Mortgage & prepayments £109,196.59 (40 tx — 26 DDs net of the 14 Apr 26
refund −£2,256.13, + 4 Halifax deposit transfers £27,998, + 8 WORKBOOK-LEVEL
overpayment rows £26,504 sourced from the Halifax annual statement (07 Jan 25
£100, 10 Mar £5,000, 21 Mar £1,000, 28 Mar £5,000, 27 May £5,000, 16 Jun
£5,000, 30 Jul £3,000) + HSBC (Deeksha) 06 Oct 25 £2,404 — these rows are
NOT in ledger.json) · Ground rent £1,319.69 (5 tx: £187.50 × 3 + £382.19 +
£375) · Service charge RMG £6,244.58 · Works £765.57 · Council tax £3,517.89
· Home insurance £224.04. TOTAL £121,268.36 (61 tx, Jun 24–Aug 26; HSBC
statements cover from Jun 24, cards from May 25). Rebuild from the ledger
using merchant patterns (HALIFAX/MTG/MORTGAGE REFUND, BERKELEY, RMG,
ELECMEC/ANJALI, BARNET, UINSURE); re-add the 8 document-sourced overpayment
rows by hand after any rebuild. Deliberately excluded (noted on sheet):
water, energy, broadband, life insurance, furniture — add only if the owner
asks. Halifax statement facts (notes on sheet): fixed 4.57% to 31 Mar 26,
balance £314,542.54 at 02 Oct 25, interest £15,481.88/12mo, joint holders,
opened 02 May 24.
Extrapolation block (below grand TOTAL): the 4 recurring categories to full
ownership May 24–Aug 26 — ground rent fully observed £1,319.69 (run-rate
£750/yr, £375 half-yearly) · RMG ~£10,320 (Jun 24 & Jan 25 semi-annuals
estimated — Deeksha's cards start May 25) · council tax ~£5,655 (bill-
verified: 24/25 ≈£2,375, 25/26 £2,487.85; unobserved May 24–Jan 25 ≈£2,137;
run-rate £2,575/yr) · insurance £224.04 (UInsure began May 26) → ~£17,519
total (observed £11,306.20 + est. missing ~£6,212). Mortgage excluded
(actuals in category 1). Prepayments confirmed at £100,000 by loan sizes:
£400,000 initial → £300,000 at the Apr 2026 remortgage — no prepayment
statements needed.

## Dining detail
Table 1 monthly summary rows 5–19 (Month | Spend | # tx), TOTAL row 20
`=SUM(C5:C19)` + annualised run-rate below (×12/14, ties to Recurring row 13).
Table 2 'All transactions': section title row 23, header 24, data rows 25+
(B # | C Date | D Merchant | E Source | F Amount net of refunds), TOTAL last
`=SUM(F…)`, freeze panes at data start. Built from the ledger using the CSV
`classification` labels: Amex `dining`, Barclays `Dining` + `Deliveroo`
(incl Plus sub), HSBC `food` (Too Good To Go, Deliveroo). HSBC ledger descs
are cleaned (`DELIVEROO LONDON` vs CSV `VIS DELIVEROO`) — match on amount/
date if a row goes missing. Rebuild from the ledger; don't hand-edit rows.
Total £6,186.48 (Ragam 30 Apr 26 £414.23 group dinner ×10 people is
counted at the £41.42 share; the ledger keeps the full statement amount).

## (charts) Variable expenses
Data table rows 4–20: Month | Dining | Groceries | Personal transport |
Entertainment | Total (live SUM per row and TOTAL row 20). 4 bar charts (one
per category) + 1 combined line chart anchored H4/H21/H38/H55/H72. Series
rebuilt from the ledger via CSV classification labels with EXCLUDES: TfL +
Trainline (reimbursable), Barclays 'Uber *Eats' £195.44 (mislabelled
transport), dining's Post Office/temple/Painshill rows. Dining column must
always equal the 'Dining detail' sheet total (currently £6,186.48).

## Your-Saving detail / Sources & Notes
Reference sheets; update only when new data changes them. Sources & Notes:
source table rows 5–11 — rows 5–8 the 44 parsed card/bank statements, rows
9–11 DOCUMENTS read directly (not ledger sources): Halifax annual mortgage
statement (printed 02 Oct 25, acct •••40200), HSBC Premier (Deeksha) Jun–Oct
25 (mortgage-application evidence, `My Drive/Family Documents/Home
Purchase/Mortgage 2026/Deeksha/`), Barnet council tax bill 25/26. Notes
13–16 (merged B:F) incl. the rule that document-sourced rows are workbook-
level additions — ledger.json mirrors parsed statements only.

## QA before every sync
```bash
python3 -c "from openpyxl import load_workbook; wb=load_workbook('<file>');
wt=wb['One-off transactions']; wo=wb['One-off Expenses']
# totals must match; TOTAL row is wt.max_row where col C == 'TOTAL'
print(sum(wt.cell(row=r,column=6).value or 0 for r in range(5,wt.max_row)) ,
      sum(wo.cell(row=r,column=5).value or 0 for r in range(5,13)))"
```
Then `cp` to the Drive path from config.json.
