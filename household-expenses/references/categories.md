# Classification Rules — Household Expenses

Every new transaction from `parse_statements.py` must be sorted into ONE of:
**one-off category** / **recurring item** / **reimbursable** / **excluded**.
When genuinely ambiguous, ask the user — never guess silently.

## EXCLUDED — never count as household spend

| Pattern (description contains) | Why |
|---|---|
| Barclays desc starting `Payment` / Amex `PAYMENT RECEIVED` / HSBC `OBP AMERICAN EXP`, `DD B/CARD AVIOS PLUS`, `DD HALIFAX`-mortgage-old-refs, `PB5xxx******` | Card payment settlements (already excluded by parser where possible) |
| `Interactive Broker`, `U21174693` | Investments |
| `Marcus`, `BP Divyam Marcus` | ISA savings |
| `Revolut`, `To Revolut`, `VRP D M Rastogi`, `Monzo` | Own-account transfers |
| `BP Wife`, `TFR ... INTERNET TRANSFER` to own accounts, `RASTOGI D Hubby` (in) | Between-household transfers (£1,000/mo wife allowance) |
| `HENGAMEH MOHAMMADK` (CR) | Parking income — £120/mo credits, NOT an expense |
| `PROTON TECHNOLOGIE`, `CLEARWATER ANALYTI`, `Stripe Payments` | Salary / business income |
| `HMRC` | Tax refunds/credits |
| Card fees already handled on the recurring sheet (`DD B/CARD AVIOS PLUS 35.00` etc.) | £20/mo × 2 cards, recurring line |

## ONE-OFF categories (exact names for update_workbook.py)

- **Shopping & electronics** — retail, gadgets, clothes (Sony, Amazon goods, Apple Store hardware)
- **Visa & immigration** — UKVI, VFS, IHS fees
- **Flights & hotels** — airlines, Booking.com, Trip.com, hotels, trip settlements (e.g. Namit Sharma £140)
- **Home, furniture & repairs** — Golding House works: ElecMec, furniture, Anjali Patel. NOT ground rent (Berkeley Commercial is recurring — see table below). Manual pre-window furniture (beds £2,300, sofa £700, IKEA £1,110 — 2024, house acquired May 2024) lives ONLY on '(one-off) House (Golding House)', never in the 14-month statement sheets; house cash-in totals live on '(cash-in) House (Golding House)'.
- **Unclassified card spending** — small charges with no clear identity (long tail)
- **Personal & services** — tennis/Fabtennis, DVSA, Post Office postage, temple/charity, gifts
- **Small tech / services** — domains (GoDaddy), Google Play, Waitrose Delivery Pass
- **Days out & attractions** — Painshill Park-style family outings, kids playgrounds

## RECURRING items — TWO homes: house items on 'House (Golding House)' (rows 5-14), everything else on 'Recurring (Annual)' (rows 5-15)

| Merchant pattern | Item |
|---|---|
| `DD MTG 40068818527466` / `DD HALIFAX` (old) | Mortgage £1,774.12/mo — HOUSE sheet |
| `RMG` | Service charge ~£1,885 semi-annual — HOUSE sheet |
| `Berkeley Commercial` / `T-BEA-GLD048` (HSBC, Dec & May) | Ground rent — £375 bi-annual (Dec/May), £750/yr (NOT a one-off) — HOUSE sheet |
| `L B BARNET` / council | Council tax — HOUSE sheet |
| ~~`EAST MIDLANDS WATER`~~ | NOT recurring — one-off £1,295 (May 2026), category 'Home, furniture & repairs' + '(one-off) House' sheet |
| `OVO ENERGY`, `FUSE ENERGY` | Energy — HOUSE sheet |
| `HYPEROPTIC`, `VODAFONE` | Broadband (Vodafone £21/mo since May 26) — HOUSE sheet |
| `UINSURE` | Home insurance annual £224.04 — HOUSE sheet |
| `VITALITY LIFE`, `LV= LIFE INSURANCE`/`LV LIFE` | Life insurance — HOUSE sheet (mortgage protection) |
| `AYUR-VAIDYA` | £550/mo treatment (paused May 26 — watch for resumption) |
| `SPUSU` | Wife's SIM — Recurring sheet |
| `CLAUDE` | £90/mo |
| `YOUR-SAVING` | Voucher site (Waitrose/Asda pre-paid groceries) |
| `Z.AI` | ~£23/mo from Apr 26 |
| `CINEWORLD` (£22.99 DD) | Unlimited card |
| `APPLE.COM/BILL` | iCloud/subs |
| `AMAZON PRIME` | annual £95 |
| `DELIVEROO`, `UBER *EATS`/`UBER EATS`, restaurants/coffee (Pret, Itsu, halal food shops, `)))` card-payment rows) | Dining line — net of refunds |
| `UBER` (not Eats), `TFL TRAVEL CH` (NOT here — reimbursable), Oyster top-ups, `LIME`, rail | Transport (Oyster top-ups stay personal per user decision) |

## REIMBURSABLE (separate sheet; recoverable from employer)

- `TFL TRAVEL CH` — commuting, ~£1,373/yr
- `TRAINLINE` — rail tickets
- `BETTER.ORG` / `GLL` — badminton court bookings £26/session (NOT a gym)
- Dental: `COCO DENTAL`, dentist check-ups — episodic

## KNOWN TRAPS (past corrections — do not repeat)

1. **Refunds must net off spend**: Deliveroo Plus refunds, Itsu credit, JoyFit Houston £159 (fully refunded → excluded entirely).
2. **`DOJO*MOORGATE POST OFFI`** = Post Office postage → Personal & services, NOT dining.
3. **`PAINSHILL`** = attraction day out → Days out, NOT dining.
4. **`SHRI VALLABH NIDHI`** = temple donation → Personal & services.
5. Barclays statement files sometimes duplicate (e.g. `_102.10` suffix) — the parser's max-multiplicity merge handles this automatically; identical same-day charges are usually REAL.
6. Barclays tx dated in a later month than the statement → previous calendar year (parser handles).
7. HSBC `)))` = recurring card payment marker; `VRP` = variable recurring payment (usually own-account sweep).
