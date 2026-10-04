#!/usr/bin/env python3
"""Generate the two monthly office-rent Tax Invoices (Deeksha + Divyam).

Each month the rent is split equally and billed to Emami Agrotech Limited as
two separate invoices, one per lessor, each signed by that person only.

Invoice numbers run as ONE shared series, two per month, Deeksha first:
    June 2026 -> 001 (Deeksha) / 002 (Divyam)
    July 2026 -> 003 (Deeksha) / 004 (Divyam)   ... and so on.

Usage:
    python invoice_generator.py "July 2026"                # both, into cwd
    python invoice_generator.py 2026-08 /path/to/outdir    # both, into outdir
    python invoice_generator.py "July 2026" --only deeksha # just one
"""
import sys
import os
import re
import calendar

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, black
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    sys.exit(
        "This skill needs reportlab. Install it with:\n"
        "    pip install reportlab\n"
        "or run with a Python that already has it."
    )

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Business constants — edit here if the lease terms change.
# ---------------------------------------------------------------------------
SERIES_PREFIX = "INV-2026"
ANCHOR_YEAR, ANCHOR_MONTH = 2026, 6      # June 2026 == sequence 001/002
DEFAULT_YEAR = 2026

RENT_HALF = 46450.80                      # each lessor's half of the rent
ROUND_OFF = 0.20                          # per-invoice round off
TOTAL = 46451.00                          # RENT_HALF + ROUND_OFF

HSN = "997212"
PERIOD = "1 Month"
AREA_LINE = "Carpet/Super Area: 844.56 Sq. Ft."

BILL_TO_NAME = "Emami Agrotech Limited"
BILL_TO_ADDR = "31st FL., Plot No.L-2A, Unit/Office No. 10 at Silver Office, Wave One, Sector-18, Noida - 201301"
BILL_TO_GSTIN = "09AABCN7953M1ZT"         # checksum-verified; updated 2026-09-10 per Divyam (Noida premises)
OFFICE_ADDR_1 = "Silver Office, Unit No. 10, 31st Floor, Wave One, Sector-18,"
OFFICE_ADDR_2 = "Noida – 201301"
PHONE = "9557931157"
BRANCH = "EMBASSY GOLF LINKS BENGALURU"

# Lessors, in invoice-number order (slot 0 = odd number, slot 1 = even).
LESSORS = [
    {
        "key": "deeksha",
        "name": "Deeksha Rastogi",
        "pan": "BHNPR8858Q",
        "email": "deek.rastogi94@gmail.com",
        "bank": "HDFC Bank",
        "ifsc": "HDFC0009498",
        "account": "50100294995167",
        "signature": "sig_deeksha.png",
    },
    {
        "key": "divyam",
        "name": "Divyam Mukesh Rastogi",
        "pan": "AOTPR9468N",
        "email": "divyamrastogi2@gmail.com",
        "bank": "ICICI BANK",
        "ifsc": "ICIC0003442",
        "account": "098401510126",
        "signature": "sig_divyam.png",
    },
]

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
HELV_TTC = "/System/Library/Fonts/Helvetica.ttc"
REG, BOLD = "Helv", "Helv-Bold"
try:
    pdfmetrics.registerFont(TTFont("Helv", HELV_TTC, subfontIndex=0))
    pdfmetrics.registerFont(TTFont("Helv-Bold", HELV_TTC, subfontIndex=1))
except Exception:
    REG, BOLD = "Helvetica", "Helvetica-Bold"

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})

# ---------------------------------------------------------------------------
# Number to words (Indian system)
# ---------------------------------------------------------------------------
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
         "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
         "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
         "Eighty", "Ninety"]


def _two(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _three(n):
    parts = []
    if n // 100:
        parts.append(_ONES[n // 100] + " Hundred")
    if n % 100:
        parts.append(_two(n % 100))
    return " ".join(parts)


def num_to_words_indian(n):
    """46451 -> 'Forty Six Thousand Four Hundred Fifty One'."""
    n = int(n)
    if n == 0:
        return "Zero"
    parts = []
    for div, label in ((10**7, "Crore"), (10**5, "Lakh"), (10**3, "Thousand")):
        if n >= div:
            parts.append(_two(n // div) + " " + label)
            n %= div
    if n:
        parts.append(_three(n))
    return " ".join(p for p in parts if p)


def money(v):
    return f"{v:,.2f}"


# ---------------------------------------------------------------------------
# Month parsing + derived fields
# ---------------------------------------------------------------------------
def parse_month(spec):
    s = spec.strip()
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d{1,2})[-/](\d{4})", s)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.fullmatch(r"([A-Za-z]+)[\s,]*(\d{4})?", s)
    if m and m.group(1).lower() in MONTHS:
        return (int(m.group(2)) if m.group(2) else DEFAULT_YEAR), MONTHS[m.group(1).lower()]
    m = re.fullmatch(r"(\d{1,2})", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return DEFAULT_YEAR, int(m.group(1))
    raise ValueError(
        f"Could not parse month from {spec!r}. "
        "Try 'July 2026', '2026-07', 'Jul', or '7'."
    )


def month_index(year, month):
    return (year - ANCHOR_YEAR) * 12 + (month - ANCHOR_MONTH)


def derive(year, month, slot):
    """Return (invoice_no, date_str, desc_text) for one lessor slot."""
    if not (1 <= month <= 12):
        raise ValueError(f"Month out of range: {month}")
    mi = month_index(year, month)
    if mi < 0:
        raise ValueError(
            f"{calendar.month_name[month]} {year} precedes the lease start "
            f"(June 2026 = {SERIES_PREFIX}-001/002)."
        )
    seq = mi * 2 + slot + 1
    invoice_no = f"{SERIES_PREFIX}-{seq:03d}"
    date_str = f"01/{month:02d}/{year % 100:02d}"
    last = calendar.monthrange(year, month)[1]
    mname = calendar.month_name[month]
    desc = (f"Monthly Office Rent for the period 01 {mname} {year} "
            f"to {last} {mname} {year}")
    return invoice_no, date_str, desc


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = 595.28, 841.89
MX = 40
RX = PAGE_W - MX
CONTENT_W = RX - MX
LINE = HexColor("#000000")

# table columns
T_DESC, T_HSN, T_PER = MX, MX + 225, MX + 270
T_RATE, T_AMT, T_END = MX + 315, MX + 405, RX


def wrap(s, font, size, max_w):
    """Greedy word wrap to max_w points."""
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def build_pdf(out_path, lessor, invoice_no, date_str, desc):
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Tax Invoice {invoice_no} - {lessor['name']}")

    def yt(top):
        return PAGE_H - top

    def text(x, top, s, font=REG, size=9):
        c.setFont(font, size); c.setFillColor(black); c.drawString(x, yt(top), s)

    def rtext(x, top, s, font=REG, size=9):
        c.setFont(font, size); c.setFillColor(black); c.drawRightString(x, yt(top), s)

    def ctext(x, top, s, font=REG, size=9):
        c.setFont(font, size); c.setFillColor(black); c.drawCentredString(x, yt(top), s)

    def box(x0, top0, x1, top1):
        c.setLineWidth(1); c.setStrokeColor(LINE)
        c.rect(x0, yt(top1), x1 - x0, top1 - top0, stroke=1, fill=0)

    def hline(x0, x1, top):
        c.setLineWidth(1); c.setStrokeColor(LINE); c.line(x0, yt(top), x1, yt(top))

    def vline(x, top0, top1):
        c.setLineWidth(1); c.setStrokeColor(LINE); c.line(x, yt(top0), x, yt(top1))

    def lbl(x, top, label, value, lf=BOLD, vf=REG, size=9):
        text(x, top, label, lf, size)
        text(x + pdfmetrics.stringWidth(label, lf, size), top, value, vf, size)

    # Title
    ctext(PAGE_W / 2, 50, "TAX INVOICE", BOLD, 13)
    tw = pdfmetrics.stringWidth("TAX INVOICE", BOLD, 13)
    hline(PAGE_W / 2 - tw / 2, PAGE_W / 2 + tw / 2, 53)

    # Lessor details
    t = 62
    text(MX + 5, t + 11, "LESSOR DETAILS", BOLD, 9)
    text(MX + 5, t + 23, lessor["name"], BOLD, 10)
    lbl(MX + 5, t + 35, "Office Address: ", OFFICE_ADDR_1)
    text(MX + 5, t + 46, OFFICE_ADDR_2, REG, 9)
    lbl(MX + 5, t + 58, "PAN: ", lessor["pan"], BOLD, BOLD)
    lbl(MX + 5, t + 70, "Email: ", lessor["email"])
    lbl(MX + 5, t + 82, "Phone: ", PHONE, BOLD, BOLD)
    lb = t + 90
    box(MX, t, RX, lb)

    # Bill to
    t = lb + 6
    text(MX + 5, t + 11, "BILL TO", BOLD, 9)
    text(MX + 5, t + 23, BILL_TO_NAME, BOLD, 10)
    text(MX + 5, t + 35, BILL_TO_ADDR, REG, 9)
    lbl(MX + 5, t + 47, "GSTIN: ", BILL_TO_GSTIN, BOLD, BOLD)
    bb = t + 55
    box(MX, t, RX, bb)

    # Invoice details
    t = bb + 6
    text(MX + 5, t + 11, "Invoice Details", BOLD, 9)
    lbl(MX + 5, t + 24, "Invoice No: ", invoice_no, BOLD, BOLD)
    dl = "Date "
    rtext(RX - 5, t + 24, date_str, BOLD, 9)
    dw = pdfmetrics.stringWidth(date_str, BOLD, 9)
    text(RX - 5 - dw - pdfmetrics.stringWidth(dl, BOLD, 9), t + 24, dl, BOLD, 9)
    ib = t + 30
    box(MX, t, RX, ib)

    # ---- Items table ----
    tt = ib
    hb = tt + 16
    c.setFillColor(HexColor("#F2F2F2"))
    c.rect(MX, yt(hb), CONTENT_W, hb - tt, stroke=0, fill=1)
    c.setFillColor(black)
    ctext((T_DESC + T_HSN) / 2, tt + 11, "Description of Services/Items", BOLD, 8.5)
    ctext((T_HSN + T_PER) / 2, tt + 11, "HSN/SAC", BOLD, 8.5)
    ctext((T_PER + T_RATE) / 2, tt + 11, "Period", BOLD, 8.5)
    ctext((T_RATE + T_AMT) / 2, tt + 11, "Unit Rate", BOLD, 8.5)
    ctext((T_AMT + T_END) / 2, tt + 11, "Amount", BOLD, 8.5)

    # item row: wrapped description + area line
    desc_lines = wrap(desc, REG, 9, (T_HSN - T_DESC) - 10)
    it = hb
    y = it + 12
    for ln in desc_lines:
        text(T_DESC + 4, y, ln, REG, 9)
        y += 11
    text(T_DESC + 4, y, AREA_LINE, REG, 9)
    ib2 = max(y + 8, it + 42)
    ctext((T_HSN + T_PER) / 2, it + 12, HSN, REG, 9)
    ctext((T_PER + T_RATE) / 2, it + 12, PERIOD, REG, 9)
    rtext(T_AMT - 6, it + 12, money(RENT_HALF), REG, 9)
    rtext(T_END - 6, it + 12, money(RENT_HALF), REG, 9)

    # round off row
    rt = ib2
    rb = rt + 15
    text(T_RATE + 4, rt + 11, "Round", REG, 9)
    rtext(T_END - 6, rt + 11, money(ROUND_OFF), REG, 9)

    # total row
    trt = rb
    trb = trt + 16
    words = f"INR {num_to_words_indian(TOTAL)} Only"
    ctext((T_DESC + T_RATE) / 2, trt + 11, words, BOLD, 8.5)
    text(T_RATE + 4, trt + 11, "Total", BOLD, 9)
    rtext(T_END - 6, trt + 11, money(TOTAL), BOLD, 9)

    box(MX, tt, RX, trb)
    hline(MX, RX, hb); hline(MX, RX, ib2); hline(T_RATE, RX, rb)
    for cx in (T_HSN, T_PER, T_RATE, T_AMT):
        vline(cx, tt, ib2)
    vline(T_RATE, ib2, trb); vline(T_AMT, ib2, trb)

    # Disbursement
    t = trb + 14
    text(MX, t, "DISBURSEMENT INSTRUCTIONS", BOLD, 9)
    text(MX, t + 14, "Kindly remit the invoice amount into the following bank accounts:", BOLD, 9)

    # Bank box
    t += 22
    text(MX + 5, t + 11, "Bank Account Detail", BOLD, 9)
    lbl(MX + 5, t + 24, "Bank Name :  ", lessor["bank"], REG, REG)
    lbl(MX + 5, t + 36, "Account Name: ", lessor["name"], REG, REG)
    lbl(MX + 5, t + 48, "Account Number: ", lessor["account"], REG, REG)
    lbl(MX + 285, t + 24, "IFSC Code: ", lessor["ifsc"], REG, REG)
    text(MX + 285, t + 36, "Branch: " + BRANCH, REG, 9)
    bkb = t + 56
    box(MX, t, RX, bkb)

    # Terms
    t = bkb + 14
    text(MX, t, "Terms & Conditions", REG, 9)
    text(MX, t + 13, "1. Payment due within 15 days from invoice date.", REG, 9)
    text(MX, t + 25, "2. Interest @18% p.a. will be charged on delayed payments.", REG, 9)
    text(MX, t + 37, "3. Subject to Noida jurisdiction.", REG, 9)

    # Signature
    t += 60
    text(MX + 5, t, "For " + lessor["name"], REG, 9)
    sig = os.path.join(HERE, lessor["signature"])
    if os.path.exists(sig):
        c.drawImage(sig, MX + 10, yt(t + 52), width=150, height=44,
                    mask="auto", preserveAspectRatio=True, anchor="sw")
    text(MX + 5, t + 67, "Authorized Signatory", REG, 9)

    c.showPage()
    c.save()


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    only = None
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--only":
            i += 1
            only = argv[i].lower() if i < len(argv) else None
        else:
            args.append(argv[i])
        i += 1
    if not args:
        print(__doc__)
        return 2

    year, month = parse_month(args[0])
    outdir = os.path.abspath(args[1]) if len(args) > 1 else os.getcwd()
    os.makedirs(outdir, exist_ok=True)

    targets = [l for l in LESSORS if only is None or l["key"] == only]
    if not targets:
        raise SystemExit(f"Unknown --only {only!r}; use one of: "
                         + ", ".join(l["key"] for l in LESSORS))

    for lessor in targets:
        slot = LESSORS.index(lessor)
        invoice_no, date_str, desc = derive(year, month, slot)
        fname = (f"Tax_Invoice_{invoice_no}_{lessor['name'].replace(' ', '_')}_"
                 f"{calendar.month_name[month]}_{year}.pdf")
        out_path = os.path.join(outdir, fname)
        build_pdf(out_path, lessor, invoice_no, date_str, desc)
        print(f"{lessor['name']:24} {invoice_no}  {date_str}  -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
