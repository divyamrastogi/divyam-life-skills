#!/usr/bin/env python3
"""Parse credit-card / bank statements into a normalised transaction ledger.

Usage:
  parse_statements.py [--paths PDF_OR_DIR ...] [--commit]

Without --paths, every folder named in ../config.json is scanned.
Parses all PDFs, validates each statement (Barclays: printed transactions
total; HSBC: balance walk + Payments In/Out box), merges with multiplicity
(identical same-day charges are legitimate), diffs against ledger.json and
prints the NEW transactions as JSON. With --commit, the ledger is updated
(timestamped backup made first).
"""
import argparse, datetime, json, os, re, shutil, sys
from collections import Counter

import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "..", "config.json")))
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTHS = {m: i + 1 for i, m in enumerate(MON)}

# ---------------------------------------------------------------- helpers
def pdf_text(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            out.append(p.extract_text() or "")
    return "\n".join(out)


def iso(y, mon, day):
    return f"{y:04d}-{MONTHS[mon]:02d}-{int(day):02d}"


def stmt_year_rule(tx_mon, stmt_mon, stmt_year):
    """A transaction dated in a later month than the statement's month belongs
    to the statement's previous year (e.g. 'Dec' charges on a Jan statement)."""
    return stmt_year - 1 if MON.index(tx_mon) > MON.index(stmt_mon) else stmt_year


def num(s):
    return float(s.replace(",", "").replace("£", ""))

# ---------------------------------------------------------------- Barclays
TX_RE = re.compile(r'(\d{2} [A-Z][a-z]{2}) (.+?) £(\d[\d,]*\.\d{2})(CR)?(?=\s|$)')
ISSUED_RE = re.compile(r'issued on (\d{2}) (\w+) (\d{4})')
TOTAL_RE = re.compile(r'Transactions, interest and charges £([\d,]+\.\d{2})')

def parse_barclays(path, who):
    """Proven regex: per line, 'DD Mon <desc> £12.34 [CR]'.
    Skips lines starting with 'Payment ' (card payment settlements, not spend),
    strips trailing ' e' pdf artifacts. Validates against the printed
    'Transactions, interest and charges £X' total."""
    text = pdf_text(path)
    m = ISSUED_RE.search(text)
    if not m:
        raise ValueError(f"{path}: no 'issued on' date — not a Barclays statement?")
    stmt_mon = next((x for x in MON if x.lower() == m.group(2).lower()[:3]), None)
    if stmt_mon is None:
        raise ValueError(f"{path}: unparseable statement month {m.group(2)}")
    stmt_year = int(m.group(3))
    stmt = f"{stmt_mon}{str(stmt_year)[2:]}"
    txs, stmt_total = [], None
    for line in text.splitlines():
        mm = TOTAL_RE.search(line)
        if mm:
            stmt_total = num(mm.group(1))
        for tm in TX_RE.finditer(line):
            date_s, desc, amt_s, cr = tm.groups()
            desc = desc.strip()
            if desc.startswith("Payment"):
                continue  # card payment settlement, not spend
            if desc.endswith(" e"):
                desc = desc[:-2]
            day, mon = date_s.split()
            yr = stmt_year_rule(mon, stmt_mon, stmt_year)
            txs.append({"source": "Barclays", "who": who, "stmt": stmt,
                        "date": iso(yr, mon, day), "desc": desc,
                        "amt": num(amt_s), "cr": bool(cr)})
    if stmt_total is not None:
        tot = sum((-t["amt"] if t["cr"] else t["amt"]) for t in txs)
        if abs(abs(tot) - stmt_total) > 0.02:
            raise ValueError(f"{os.path.basename(path)}: parsed £{tot:,.2f} vs "
                             f"printed £{stmt_total:,.2f} — statement validation FAILED")
    return txs

# ---------------------------------------------------------------- Amex
AMEX_TX = re.compile(r'^([A-Z][a-z]{2}\d{1,2})\s+([A-Z][a-z]{2}\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})$')
AMEX_PERIOD = re.compile(r'_(\d{1,2})_([A-Z][a-z]{2})_(\d{4})')

def parse_amex(path, who):
    """Lines: 'Apr10 Apr10 DESCRIPTION 31.51' (process date, tx date, desc,
    amount). A bare 'CR' on its own line marks the PREVIOUS transaction as a
    credit. 'PAYMENT RECEIVED' lines are card payments, not spend. Statement
    month/year from the filename period (e.g. 29_Mar_2026_-_28_Apr_2026) or
    the DD/MM/YY statement date in the page header."""
    base = os.path.basename(path)
    pm = AMEX_PERIOD.search(base)
    if pm:
        stmt_mon, stmt_year = pm.group(2), int(pm.group(3))
    else:
        dm = re.search(r'(\d{2})/(\d{2})/(\d{2})', pdf_text(path))
        if not dm:
            raise ValueError(f"{base}: cannot determine Amex statement period")
        stmt_mon, stmt_year = MON[int(dm.group(2)) - 1], 2000 + int(dm.group(3))
    stmt = f"{stmt_mon}{str(stmt_year)[2:]}"
    txs, just_matched = [], None
    for line in pdf_text(path).splitlines():
        s = line.strip()
        if s == "CR":
            if just_matched is not None:
                just_matched["cr"] = True
            continue
        m = AMEX_TX.match(s)
        if not m:
            continue
        pdate, tdate, desc, amt_s = m.groups()
        mon, day = tdate[:3], tdate[3:]
        if mon not in MON or not day.isdigit():
            continue
        just_matched = None
        if "PAYMENT RECEIVED" in desc.upper():
            continue  # card payment settlement, not spend
        yr = stmt_year_rule(mon, stmt_mon, stmt_year)
        tx = {"source": "Amex", "who": who, "stmt": stmt,
              "date": iso(yr, mon, day), "desc": desc.strip(),
              "amt": num(amt_s), "cr": False}
        txs.append(tx)
        just_matched = tx
    return txs

# ---------------------------------------------------------------- HSBC
HSBC_DATE = re.compile(r'^(\d{2}) ([A-Z][a-z]{2}) (\d{2}) (.+)$')
NUMW = re.compile(r'^£?\(?-?[\d,]+\.\d{2}\)?$')
BROUGHT = re.compile(r'BALANCEBROUGHTFORWARD\s*\.?\s*£?([\d,]+\.\d{2})')
CARRIED = re.compile(r'BALANCECARRIEDFORWARD')
CLOSING = re.compile(r'ClosingBalance\s*£?([\d,]+\.\d{2})')
PAY_IN = re.compile(r'Payments\s*In\s*£([\d,]+\.\d{2})')
PAY_OUT = re.compile(r'Payments\s*Out\s*£([\d,]+\.\d{2})')
TYPE_TOKEN = re.compile(r'^(?:\){2,}|(?:DD|CR|BP|VIS|OBP|TFR|TRF|SO|ATM|CHQ|BGC|DEB|ITL|VRP|FPI|FPO|DR)\b)')

def _visual_lines(path):
    """Reconstruct visual lines from word positions: list of lists of words,
    each inner list sorted left-to-right. Needed because extract_text()
    interleaves wrapped multi-column rows."""
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = sorted(page.extract_words() or [], key=lambda w: (w["top"], w["x0"]))
            line, anchor = [], None
            for w in words:
                if anchor is None or abs(w["top"] - anchor) <= 3:
                    line.append(w)
                    anchor = w["top"] if anchor is None else anchor
                else:
                    out.append(sorted(line, key=lambda x: x["x0"]))
                    line, anchor = [w], w["top"]
            if line:
                out.append(sorted(line, key=lambda x: x["x0"]))
    return out

def parse_hsbc(path, who):
    """HSBC Premier current account. The date is printed once per day-group;
    rows are '<TYPE> <description...> <amount> <balance>' (TYPE = DD/CR/BP/
    VIS/OBP/TFR/...), descriptions wrap, and a row may start on a line
    WITHOUT a date. Direction (paid in vs paid out) is read from the x-column
    the amount word sits in (£Paid out / £Paid in / £Balance header anchors) —
    transfers' direction cannot be inferred from balances alone. Validated by
    balance walk == ClosingBalance and sums == Payments In/Out box."""
    vlines = _visual_lines(path)
    text = pdf_text(path)

    # column anchors from the '£Paid out £Paid in £Balance' header
    anchors = {}
    for ws in vlines:
        t = [w["text"].lstrip("£") for w in ws]
        if any(x == "Paid" for x in t) and any(x.startswith("Balanc") for x in t):
            for w, txt in zip(ws, t):
                if txt == "out":
                    anchors["out"] = w["x0"]
                elif txt == "in":
                    anchors["in"] = w["x0"]
                elif txt.startswith("Balanc"):
                    anchors["bal"] = w["x0"]
    if "bal" not in anchors:
        raise ValueError(f"{os.path.basename(path)}: no £Paid out/in/Balance header")

    def col(word):
        return min(anchors, key=lambda a: abs(word["x0"] - anchors[a]))

    stmt = ""
    fm = re.match(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(path))
    if fm:
        stmt = MON[int(fm.group(2)) - 1] + fm.group(3)[2:]
    txs = []
    state = {"balance": None, "cur": None, "date": None}

    def flush(nums_with_cols):
        """nums_with_cols: [(value, colname, word)] in left-to-right order."""
        cur = state["cur"]
        state["cur"] = None
        if cur is None or not nums_with_cols:
            return
        desc = re.sub(r"\s+", " ", " ".join(cur["desc_parts"])).strip()
        bal_nums = [n for n in nums_with_cols if n[1] == "bal"]
        amt_nums = [n for n in nums_with_cols if n[1] != "bal"]
        if not desc or not amt_nums:
            return  # balance-only line = informational row
        amt, acol = amt_nums[0][0], amt_nums[0][1]
        newbal = bal_nums[-1][0] if bal_nums else None
        direction = "out" if acol in ("out",) else "in"
        bal = state["balance"]
        if newbal is not None and bal is not None:
            expect = round(bal + (amt if direction == "in" else -amt), 2)
            if abs(expect - newbal) > 0.02:
                # column read disagrees with arithmetic — trust arithmetic
                alt = "in" if direction == "out" else "out"
                if abs(round(bal + (amt if alt == "in" else -amt), 2) - newbal) < 0.02:
                    direction = alt
        txs.append({"source": "HSBC", "who": who, "stmt": stmt,
                    "date": cur["date"], "desc": desc, "amt": amt,
                    "cr": direction == "in", "dir": direction})
        if newbal is not None:
            state["balance"] = newbal
        elif bal is not None:
            state["balance"] = round(bal + (amt if direction == "in" else -amt), 2)

    def start_cur(date, typ, body):
        if state["cur"] is not None:
            state["cur"] = None  # number-less row = informational
        state["cur"] = {"date": date, "type": typ, "desc_parts": [body.strip(" .")]}
        state["date"] = date

    for ws in vlines:
        texts = [w["text"] for w in ws]
        line = " ".join(texts)
        compact = line.replace(" ", "")
        bm = BROUGHT.search(compact)
        if bm and "BALANCE" in compact:
            state["balance"] = num(bm.group(1))
            state["cur"] = None
            continue
        if CARRIED.search(compact):
            nums = [(num(w["text"]), col(w), w) for w in ws if NUMW.match(w["text"])]
            state["cur"] = None
            if nums and state["balance"] is not None:
                state["balance"] = nums[-1][0]
            continue
        dm = HSBC_DATE.match(line)
        if dm:
            day, mon, yy, rest = dm.groups()
            toks = rest.split()
            typ = toks[0] if toks else ""
            body = " ".join(t for t in toks[1:] if not NUMW.match(t))
            start_cur(iso(2000 + int(yy), mon, day), typ, body)
            nums = [(num(w["text"]), col(w), w) for w in ws if NUMW.match(w["text"])]
            if nums:
                flush(nums)
            continue
        if state["date"] is not None and TYPE_TOKEN.match(line):
            toks = line.split()
            body = " ".join(t for t in toks[1:] if not NUMW.match(t))
            start_cur(state["date"], toks[0], body)
            nums = [(num(w["text"]), col(w), w) for w in ws if NUMW.match(w["text"])]
            if nums:
                flush(nums)
            continue
        nums = [(num(w["text"]), col(w), w) for w in ws if NUMW.match(w["text"])]
        if state["cur"] is not None:
            if nums:
                head = " ".join(w["text"] for w in ws if not NUMW.match(w["text"]))
                if head:
                    state["cur"]["desc_parts"].append(head.strip(" ."))
                flush(nums)
            else:
                state["cur"]["desc_parts"].append(line)
    # trailing cur without numbers is informational; drop

    # --- validation 1: balance walk vs ClosingBalance
    cm = CLOSING.search(text)
    bm = BROUGHT.search(text.replace(" ", ""))
    if cm is not None and bm is not None and txs:
        bal = num(bm.group(1))
        for t in txs:
            bal = round(bal + (t["amt"] if t["cr"] else -t["amt"]), 2)
        if abs(bal - num(cm.group(1))) > 0.05:
            raise ValueError(f"{os.path.basename(path)}: HSBC balance walk "
                             f"£{bal:,.2f} != ClosingBalance £{num(cm.group(1)):,.2f}")
    # --- validation 2: sums vs Payments In / Payments Out box
    pin, pout = PAY_IN.search(text), PAY_OUT.search(text)
    if pin and pout:
        ins = sum(t["amt"] for t in txs if t["cr"])
        outs = sum(t["amt"] for t in txs if not t["cr"])
        if abs(ins - num(pin.group(1))) > 0.05 or abs(outs - num(pout.group(1))) > 0.05:
            raise ValueError(f"{os.path.basename(path)}: HSBC sums in £{ins:,.2f}/"
                             f"out £{outs:,.2f} != box £{num(pin.group(1)):,.2f}/"
                             f"£{num(pout.group(1)):,.2f}")
    return txs

# ---------------------------------------------------------------- merge/dedupe
def tx_key(t):
    return (t["source"], t["who"], t["date"], t["desc"],
            round(t["amt"], 2), "CR" if t.get("cr") else "")

def detect(path):
    p = os.path.normpath(path)
    for s in CONFIG["sources"]:
        if s["folder"] in p:
            return s["provider"], s["who"]
    base = os.path.basename(p).lower()
    if "barclaycard" in base:
        return "barclays", "Deeksha"
    if "premier bank" in base:
        return "hsbc", "Divyam"
    raise ValueError(f"Cannot detect provider for {path}")

def parse_all(paths):
    """Parse every PDF; merge duplicate statement files with max-multiplicity
    (identical same-day charges are legitimate and must not collapse)."""
    merged = Counter()
    for path in paths:
        provider, who = detect(path)
        parser = {"barclays": parse_barclays, "amex": parse_amex, "hsbc": parse_hsbc}[provider]
        txs = parser(path, who)
        c = Counter(tx_key(t) for t in txs)
        for k, n in c.items():
            if merged[k] < n:
                merged[k] = n
    return merged

def load_ledger():
    p = CONFIG["ledger"]
    if not os.path.exists(p):
        return Counter()
    out = {}
    for k, n in json.load(open(p)).items():
        src, who, date, desc, amt, cr = k.split("|")
        out[(src, who, date, desc, round(float(amt), 2), cr)] = n
    return Counter(out)

def save_ledger(ledger, merged):
    """Merge parsed counts into the ledger (max multiplicity) — never replace,
    so committing a single new statement can't erase history."""
    p = CONFIG["ledger"]
    if os.path.exists(p):
        shutil.copy(p, p + f".bak-{datetime.date.today().isoformat()}")
    for k, n in merged.items():
        if ledger[k] < n:
            ledger[k] = n
    json.dump({"|".join(map(str, k)): n for k, n in sorted(ledger.items())},
              open(p, "w"), indent=1)
    return ledger

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="*", default=None)
    ap.add_argument("--commit", action="store_true", help="update ledger.json")
    a = ap.parse_args()

    paths = []
    if a.paths:
        for p in a.paths:
            if os.path.isdir(p):
                paths += sorted(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(".pdf"))
            else:
                paths.append(p)
    else:
        for s in CONFIG["sources"]:
            d = os.path.join(CONFIG["statements_root"], s["folder"])
            paths += sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".pdf"))

    merged = parse_all(paths)
    ledger = load_ledger()
    result = {"statements_parsed": len(paths),
              "parsed_total": sum(merged.values()),
              "ledger_before": sum(ledger.values()),
              "new_count": 0, "new": []}
    for k, n in sorted(merged.items()):
        if n > ledger.get(k, 0):
            src, who, date, desc, amt, cr = k
            result["new"].append({"source": src, "who": who, "date": date,
                                  "desc": desc, "amt": float(amt),
                                  "cr": cr == "CR", "mult": n - ledger.get(k, 0)})
    result["new_count"] = len(result["new"])
    print(json.dumps(result, indent=1))
    if a.commit:
        save_ledger(ledger, merged)
        print(f"LEDGER COMMITTED: {CONFIG['ledger']}", file=sys.stderr)

if __name__ == "__main__":
    main()
