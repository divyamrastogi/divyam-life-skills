#!/usr/bin/env python3
"""Append classified one-off transactions to the Household Expenses workbook.

Input: a JSON file like
  {"oneoff": [
     {"category": "Flights & hotels", "source": "Amex", "who": "Divyam",
      "date": "2026-09-14", "desc": "EASYJET LONDON", "amount": 210.00},
     ...amount negative for refunds...],
   "reimbursable": [ ...same shape, optional... ]}

What it does (atomically, after backing up the workbook):
  1. 'One-off transactions' sheet: inserts the rows before the TOTAL row,
     styles them, extends the SUM formula and auto-filter.
  2. 'One-off Expenses' sheet: adds each amount to its category row (col E)
     and inserts the transaction line into the category's chronological
     transaction list (col F).
  3. Verifies both sheets' totals still agree, saves, prints before/after.

Recurring run-rate lines, Summary KPIs and the House sheet are NOT touched —
the agent updates those per references/workbook_map.md when needed.
Categories must be the exact item names on the 'One-off Expenses' sheet.
"""
import argparse, datetime, json, os, re, shutil, sys

from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "..", "config.json")))
GBP2 = '£#,##0.00'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

CAT_ROWS = {  # 'One-off Expenses' data rows (5..12), TOTAL row 13
    "Shopping & electronics": 5, "Visa & immigration": 6, "Flights & hotels": 7,
    "Home, furniture & repairs": 8, "Unclassified card spending": 9,
    "Personal & services": 10, "Small tech / services": 11,
    "Days out & attractions": 12,
}
SOURCE_LABEL = {("Amex", "Divyam"): "Amex (Divyam)",
                ("Barclays", "Divyam"): "Barclaycard (Divyam)",
                ("Barclays", "Deeksha"): "Barclaycard (Deeksha)",
                ("HSBC", "Divyam"): "HSBC (Divyam)"}


def dmy(iso_date):
    y, m, d = iso_date.split("-")
    return f"{int(d):02d} {MON[int(m) - 1]} {y[2:]}"


def sort_key(line):
    m = re.match(r'(\d{2}) ([A-Z][a-z]{2}) (\d{2})', line)
    if not m:
        return (99, 99, 99)
    return (int(m.group(3)), MON.index(m.group(2)), int(m.group(1)))


def tx_line(t):
    amt = t["amount"]
    astr = f"−£{abs(amt):,.2f}" if amt < 0 else f"£{amt:,.2f}"
    return f"{dmy(t['date'])}  {astr}  {t['desc']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("classification", help="JSON file with classified transactions")
    a = ap.parse_args()
    data = json.load(open(a.classification))
    oneoff = data.get("oneoff", [])
    if not oneoff:
        print("nothing to do")
        return
    for t in oneoff:
        if t["category"] not in CAT_ROWS:
            sys.exit(f"unknown category {t['category']!r}; must be one of {list(CAT_ROWS)}")
        if t["source"] not in ("Amex", "Barclays", "HSBC"):
            sys.exit(f"unknown source {t['source']!r}")

    wb_path = CONFIG["workbook_local"]
    if not os.path.exists(wb_path):  # fall back to the Drive copy
        wb_path = CONFIG["workbook_drive"]
    backup = wb_path + f".bak-{datetime.date.today().isoformat()}"
    shutil.copy(wb_path, backup)

    wb = load_workbook(wb_path)

    # ---- 1. One-off transactions sheet ----
    wt = wb["One-off transactions"]
    total_row = wt.max_row  # TOTAL row is last
    while wt.cell(row=total_row, column=3).value != "TOTAL":
        total_row -= 1
    data_end = total_row - 1
    n = len(oneoff)
    wt.insert_rows(total_row, n)
    for i, t in enumerate(oneoff):
        r = total_row + i
        label = SOURCE_LABEL.get((t["source"], t.get("who", "Divyam")), t["source"])
        for ci, v in enumerate([t["category"], label, dmy(t["date"]),
                                t["desc"], t["amount"]], start=2):
            wt.cell(row=r, column=ci, value=v)
        wt.cell(row=r, column=6).number_format = GBP2
    new_total_row = total_row + n
    wt.cell(row=new_total_row, column=6, value=f"=SUM(F5:F{new_total_row - 1})")
    wt.auto_filter.ref = f"B4:F{new_total_row - 1}"
    # styling: copy font/fill of the row above the block
    from copy import copy as _copy
    for r in range(total_row, new_total_row):
        for ci in range(2, 7):
            src, dst = wt.cell(row=total_row - 1, column=ci), wt.cell(row=r, column=ci)
            dst.font = _copy(src.font); dst.fill = _copy(src.fill)
            dst.border = _copy(src.border); dst.alignment = _copy(src.alignment)

    # ---- 2. One-off Expenses sheet ----
    wo = wb["One-off Expenses"]
    for t in oneoff:
        r = CAT_ROWS[t["category"]]
        wo.cell(row=r, column=5, value=round((wo.cell(row=r, column=5).value or 0)
                                              + t["amount"], 2))
        existing = wo.cell(row=r, column=6).value or ""
        lines = (existing + "\n" + tx_line(t)).strip("\n").split("\n")
        lines = sorted(lines, key=sort_key)
        wo.cell(row=r, column=6, value="\n".join(lines))

    # ---- 3. verify + save ----
    wt_sum = sum(wt.cell(row=r, column=6).value or 0 for r in range(5, new_total_row))
    wo_sum = sum(wo.cell(row=r, column=5).value or 0 for r in range(5, 13))
    if abs(wt_sum - wo_sum) > 0.02:
        sys.exit(f"ABORT: transactions sheet £{wt_sum:,.2f} != categories "
                 f"£{wo_sum:,.2f} — workbook NOT saved; backup at {backup}")
    wb.properties.creator = "Z.ai"
    wb.save(wb_path)
    print(f"one-off total: £{wo_sum:,.2f} (+£{sum(t['amount'] for t in oneoff):,.2f})")
    print(f"rows appended: {n} | backup: {backup}")
    print("Remember to also update: category Detail text (col D), recurring "
          "run-rate lines, Summary notes, and the House sheet if relevant — "
          "see references/workbook_map.md")


if __name__ == "__main__":
    main()
