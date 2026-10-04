#!/usr/bin/env python3
"""
pdf-redact skill helper.

Runs an input PDF through the pdf-redact project's redaction engine, keeping
only transactions that match a category (e.g. "travel") or raw keywords, and
redacting everything else.

Usage
-----
    redact.py <input.pdf> <output.pdf> --keep travel
    redact.py <input.pdf> <output.pdf> --keep travel,groceries
    redact.py <input.pdf> <output.pdf> --keep "tfl,oyster,trainline"   # raw keywords
    redact.py <input.pdf> <output.pdf> --keep travel --provider barclaycard
    redact.py <input.pdf> <output.pdf> --list-categories

How it works
------------
1.  Expand `--keep` into a flat keyword list. Barewords that match a category
    name (travel, groceries, ...) are replaced by that category's keywords.
    Unknown barewords are kept as-is — so a category and explicit keywords can
    be freely mixed.
2.  Dispatch through the project's `process_single_file` logic:
        - Barclaycard statements (auto-detected, or via --provider barclaycard)
          use the column-aware row redactor.
        - Everything else uses the generic span-by-span redactor with provider
          auto-detection (AMEX, Barclaycard, default).
3.  The output PDF is written to <output.pdf>. The project's redactors normally
    suffix the path with the kept total (e.g. `out_12.34.pdf`); this script
    renames the result to the exact output path you asked for.

Exits non-zero on any error so the calling agent can react.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Project location
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.expanduser(
    os.environ.get("PDF_REDACT_PROJECT", "~/projects/pdf-redact")
)

# ---------------------------------------------------------------------------
# Category -> keyword map.
#
# These are deliberately UK-leaning because the underlying engine was built for
# UK statements (TFL, Trainline, etc.). Every category is optional — users can
# also pass raw keywords directly with --keep. Keep these lists as substrings
# the engine matches case-insensitively against transaction text.
# ---------------------------------------------------------------------------
CATEGORIES = {
    "travel": [
        "trainline",
        "tfl",
        "transport for london",
        "oyster",
        "national rail",
        "govia",
        "gwr",
        "lner",
        "avanti",
        "southwestern",
        "south western",
        "thameslink",
        "southeastern",
        "greater anglia",
        "emirates airline",
        "uber",
        "bolt",
        "lyft",
        "addison lee",
        "heathrow express",
        "easyjet",
        "ryanair",
        "british airways",
        "wizz air",
    ],
    "groceries": [
        "tesco",
        "sainsbury",
        "asda",
        "aldi",
        "lidl",
        "waitrose",
        "m&s food",
        "marks and spencer",
        "co-op",
        "coop",
        "iceland",
        "morrisons",
        "ocado",
    ],
    "food": [
        "deliveroo",
        "just eat",
        "ubereats",
        "mcdonald",
        "kfc",
        "pret a manger",
        "nando",
        "wagamama",
        "costa",
        "starbucks",
        "caffe nero",
        "greggs",
        "wetherspoon",
    ],
    "subscriptions": [
        "netflix",
        "spotify",
        "disney",
        "prime video",
        "amazon prime",
        "now tv",
        "apple",
        "google",
        "microsoft",
        "dropbox",
        "hyperoptic",
        "vodafone",
        "ee limited",
        "three.co.uk",
        "sky ",
    ],
    "fuel": [
        "shell",
        "bp ",
        "esso",
        "texaco",
        "sainsbury fuel",
        "tesco fuel",
        "asda fuel",
    ],
    "utilities": [
        "octopus",
        "british gas",
        "edf",
        "ee ",
        "thames water",
        "uk power",
    ],
}


def list_categories() -> None:
    print("Categories (case-insensitive substring matches against transaction text):")
    for name, keywords in CATEGORIES.items():
        print(f"\n  {name}  ({len(keywords)} keywords)")
        for kw in keywords:
            print(f"    - {kw}")
    print(
        "\nTip: pass any other token with --keep to use it as a raw keyword, "
        'e.g. --keep "acme corp".'
    )


def expand_keep(items: List[str]) -> List[str]:
    """Turn --keep tokens into a flat keyword list.

    A token that names a category (e.g. "travel") is expanded to that
    category's keywords AND keeps the category name itself as a literal
    keyword — so "keep travel" still matches a merchant literally containing
    "travel" (e.g. "SQ *Lumo. Travel Well"). Anything else is kept verbatim as
    a custom keyword. Order is preserved and duplicates are dropped.

    This mirrors what the web UI does: the user types "travel" and the engine
    matches it as a raw substring. Dropping the literal category name caused a
    regression where category-named runs missed transactions the UI kept.
    """
    expanded: List[str] = []
    for item in items:
        key = item.strip().lower()
        if not key:
            continue
        if key in CATEGORIES:
            # Keep the literal category name first, then its keyword list.
            if item not in expanded:
                expanded.append(item)
            for kw in CATEGORIES[key]:
                if kw not in expanded:
                    expanded.append(kw)
        else:
            if item not in expanded:
                expanded.append(item)
    return expanded


# ---------------------------------------------------------------------------
# Engine invocation — mirrors app.py:process_single_file but without the web
# layer, and without the enhanced-privacy path (which is AMEX-only and carries
# statement-specific personal-data overrides).
# ---------------------------------------------------------------------------
def _fitz_version_tuple() -> Tuple[int, ...]:
    """Return the installed PyMuPDF version as a tuple, or () if unknown."""
    try:
        import fitz

        for probe in (getattr(fitz, "VersionBind", "") or "",
                      getattr(fitz, "__doc__", "") or ""):
            m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", probe)
            if m:
                return tuple(int(x) for x in m.groups() if x is not None)
    except Exception:
        pass
    return ()


def _ensure_fitz_version() -> None:
    """Verify PyMuPDF is importable and new enough.

    The project pins PyMuPDF==1.27.2 because older versions merge text spans
    differently and silently break transaction detection on the
    coordinate-sensitive Barclaycard path (see project commit 7ae4bc0). Older
    versions don't error — they produce wrong output — so we refuse to run
    rather than ship a silently-bad redaction.
    """
    try:
        import fitz  # noqa: F401
    except ImportError:
        sys.exit(
            "ERROR: PyMuPDF (fitz) is not importable. Install it in the project "
            "venv and re-run:\n"
            f"  {PROJECT_DIR}/venv/bin/pip install -r "
            f"{PROJECT_DIR}/requirements.txt"
        )

    v = _fitz_version_tuple()
    # Require >= 1.27.x. Older versions merge spans and silently drop rows.
    if v and v[:2] < (1, 27):
        sys.exit(
            f"ERROR: PyMuPDF {'.'.join(map(str, v))} is too old. The project "
            "pins 1.27.2 — older versions merge text spans differently and "
            "silently miss transactions on Barclaycard statements (commit "
            "7ae4bc0). Run with the project venv that has 1.27.2 installed:\n"
            f"  {PROJECT_DIR}/venv/bin/python <this script>\n"
            f"or upgrade:\n  {PROJECT_DIR}/venv/bin/pip install "
            "'PyMuPDF==1.27.2'"
        )


def detect_is_barclaycard(input_path: str, filename: str, provider: str) -> bool:
    """Replicate app.py's Barclaycard detection (content + filename + override)."""
    if provider == "barclaycard":
        return True
    filename_lower = (filename or "").lower()
    if "barclaycard" in filename_lower or "barclay" in filename_lower:
        return True
    try:
        import fitz

        doc = fitz.open(input_path)
        text = doc[0].get_text().lower() if len(doc) > 0 else ""
        doc.close()
        if "barclaycard" in text or "barclays" in text or "mastercard avios" in text:
            return True
    except Exception:
        pass
    return False


def redact(
    input_path: str, output_path: str, keep_keywords: List[str], provider: str
) -> Tuple[str, float, int]:
    """Run the engine. Returns (final_output_path, total_kept, kept_count_or_-1)."""
    _ensure_fitz_version()

    if not keep_keywords:
        sys.exit("ERROR: no keep keywords after expansion. Pass --keep.")

    sys.path.insert(0, PROJECT_DIR)

    # The project modules each call logging.basicConfig(level=INFO), which would
    # flood stderr with a per-span INFO line. basicConfig is a no-op once a
    # handler exists, so configure the root logger first to silence them. Set
    # PDF_REDACT_VERBOSE=1 to restore the engine's verbose logging.
    import logging

    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("PDF_REDACT_VERBOSE") else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    logging.getLogger().setLevel(
        logging.DEBUG if os.environ.get("PDF_REDACT_VERBOSE") else logging.WARNING
    )

    import uuid

    is_barclaycard = detect_is_barclaycard(
        input_path, os.path.basename(input_path), provider
    )

    # Use a deterministic temp name so we can find/renamed the engine's output.
    tmp_out = os.path.join(
        os.path.dirname(os.path.abspath(output_path)) or ".",
        f"tmp_out_{uuid.uuid4().hex}.pdf",
    )

    if is_barclaycard:
        from redact_barclaycard import redact_barclaycard

        # redact_barclaycard writes exactly to tmp_out.
        engine_out, total, kept = redact_barclaycard(input_path, tmp_out, keep_keywords)
        kept_count = len(kept)
    else:
        from redact_generic import redact_pdf_generic

        # redact_pdf_generic appends "_<total>.2f.pdf" to the stem it is given,
        # so pass a clean stem and locate the suffixed file afterwards.
        stem = re.sub(r"\.pdf$", "", tmp_out, flags=re.IGNORECASE)
        engine_out, total = redact_pdf_generic(input_path, keep_keywords, stem, provider)
        kept_count = -1

    # Normalise to the user's requested output path.
    if os.path.abspath(engine_out) != os.path.abspath(output_path):
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(engine_out, output_path)

    return output_path, total, kept_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="redact.py",
        description=(
            "Redact transactions from a PDF, keeping only those matching a "
            "category or raw keywords. Uses the pdf-redact project engine."
        ),
    )
    p.add_argument("input", nargs="?", help="Path to input PDF")
    p.add_argument("output", nargs="?", help="Path for redacted output PDF")
    p.add_argument(
        "--keep",
        default="",
        help=(
            "Comma-separated categories and/or raw keywords to KEEP, e.g. "
            "'travel', 'travel,groceries', 'tfl,trainline'. "
            "Categories: " + ", ".join(CATEGORIES.keys())
        ),
    )
    p.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "amex_uk", "barclaycard"],
        help="Statement provider (default: auto-detect).",
    )
    p.add_argument(
        "--list-categories",
        action="store_true",
        help="Print the category -> keyword map and exit.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable result JSON on stdout instead of prose.",
    )
    args = p.parse_args(argv)

    if args.list_categories:
        list_categories()
        return 0

    if not args.input or not args.output:
        p.error("input and output PDF paths are required (or use --list-categories)")

    if not os.path.isfile(args.input):
        sys.exit(f"ERROR: input PDF not found: {args.input}")

    keep_raw = [k.strip() for k in args.keep.split(",") if k.strip()]
    keep_keywords = expand_keep(keep_raw)

    if args.json:
        # Still print a short human hint about expanded keywords to stderr so
        # the agent can see what ran.
        print(
            "Expanded keep keywords: " + (", ".join(keep_keywords) or "(none)"),
            file=sys.stderr,
        )
    else:
        print(f"Input:    {args.input}")
        print(f"Output:   {args.output}")
        print(f"Provider: {args.provider}")
        print(f"Keeping:  {', '.join(keep_keywords) or '(none)'}")
        print("-" * 60)

    try:
        out_path, total, kept_count = redact(
            args.input, args.output, keep_keywords, args.provider
        )
    except SystemExit:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        sys.exit(f"ERROR: redaction failed: {e}")

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": out_path,
                    "total_kept": round(total, 2),
                    "kept_count": kept_count,
                    "keywords": keep_keywords,
                }
            )
        )
    else:
        print(f"\nDone. Redacted PDF written to: {out_path}")
        print(f"Whitelisted transactions total: £{total:.2f}")
        if kept_count >= 0:
            print(f"Kept transaction rows: {kept_count}")
        else:
            print("(kept-row count not available for this provider path)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
