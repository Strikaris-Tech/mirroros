"""
Khan Mall PO Response Generator
================================
Generates a signed Purchase Order PDF from Khan Mall, accepting Strikaris's
quote for Shopify Development Services.

Variation modes (controlled via seed or explicit name):
  EXACT              — all line items match the quote exactly      (happy path)
  QUANTITY_CHANGE    — Sprint 1 quantity doubled                   (obvious mismatch)
  PARTIAL_ACCEPTANCE — Platform Integration line dropped           (partial)
  PRICE_COUNTER      — Discovery repriced at $2,000               (subtle 3.3%)

Seeded shortcuts:
  seed=42  → EXACT            (default demo — happy path)
  seed=99  → PRICE_COUNTER    (exception demo — subtle mismatch)
  seed=77  → QUANTITY_CHANGE
  seed=55  → PARTIAL_ACCEPTANCE

Usage:
    from ledger.po_generator import generate_po, QUOTE

    result = generate_po(seed=42)   # reproducible EXACT
    result = generate_po(seed=99)   # reproducible PRICE_COUNTER
    result = generate_po()          # random variation

    # result keys:
    #   pdf_path    — absolute path to generated PDF
    #   variation   — mode name
    #   label       — human-readable description
    #   line_items  — list of {description, qty, unit_price, total}
    #   po_total    — sum of PO line items (may differ from quote_total)
    #   quote_total — original Strikaris quote total ($15,000)
    #   po_number   — PO identifier string
    #   quote_id    — Strikaris quote ID being accepted
"""

from __future__ import annotations

import io
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

# ── The Strikaris quote being accepted ────────────────────────────────────────

QUOTE: dict[str, Any] = {
    "quote_id":  "STR-2026-Q-018",
    "client":    "Khan Mall",
    "issued_by": "Strikaris Technology Inc.",
    "line_items": [
        {"description": "Shopify Discovery & Architecture", "qty": 1, "unit_price": 2500},
        {"description": "Sprint 1 Implementation",          "qty": 1, "unit_price": 8500},
        {"description": "Platform Integration",             "qty": 1, "unit_price": 4000},
    ],
}
QUOTE["total"] = sum(i["qty"] * i["unit_price"] for i in QUOTE["line_items"])

# ── Variation definitions ──────────────────────────────────────────────────────

def _apply(items: list, overrides: dict | None = None, drop_last: bool = False) -> list:
    result = []
    src = items if not drop_last else items[:-1]
    for i, item in enumerate(src):
        row = dict(item)
        if overrides and i in overrides:
            row.update(overrides[i])
        row["total"] = row["qty"] * row["unit_price"]
        result.append(row)
    return result

VARIATIONS: dict[str, dict] = {
    "EXACT": {
        "fn":    lambda items: _apply(items),
        "label": "Exact match — all line items accepted as quoted",
    },
    "QUANTITY_CHANGE": {
        "fn":    lambda items: _apply(items, overrides={1: {"qty": 2}}),
        "label": "Quantity change — Sprint 1 qty doubled to 2",
    },
    "PARTIAL_ACCEPTANCE": {
        "fn":    lambda items: _apply(items, drop_last=True),
        "label": "Partial acceptance — Platform Integration dropped",
    },
    "PRICE_COUNTER": {
        "fn":    lambda items: _apply(items, overrides={0: {"unit_price": 2000}}),
        "label": "Price counter-offer — Discovery repriced at $2,000 (quoted $2,500)",
    },
}

_SEED_MAP: dict[int, str] = {
    42: "EXACT",
    99: "PRICE_COUNTER",
    77: "QUANTITY_CHANGE",
    55: "PARTIAL_ACCEPTANCE",
}


def _pick_variation(seed: int | None) -> str:
    if seed in _SEED_MAP:
        return _SEED_MAP[seed]
    rng = random.Random(seed)
    return rng.choices(
        population=["EXACT", "QUANTITY_CHANGE", "PARTIAL_ACCEPTANCE", "PRICE_COUNTER"],
        weights=[60, 15, 15, 10],
    )[0]


# ── PDF rendering ──────────────────────────────────────────────────────────────

def _fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def _build_pdf(line_items: list, po_number: str, date_str: str) -> bytes:
    """Render the purchase order to PDF bytes using reportlab canvas."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as pdfcanvas

    buf = io.BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=letter)
    W, H = letter  # 612 × 792 pts

    # ── Khan Mall header ──────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 745, "KHAN MALL")
    c.setFont("Helvetica", 10)
    c.drawString(50, 731, "Development Corp.")
    c.drawString(50, 719, "4820 Commerce Drive, Suite 300")
    c.drawString(50, 707, "Las Vegas, NV 89109")

    # ── PO label (right-aligned) ──────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(W - 50, 745, "PURCHASE ORDER")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - 50, 729, f"PO Number:  {po_number}")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 50, 715, f"Date:  {date_str}")

    # ── Divider ───────────────────────────────────────────────────────────────
    c.setLineWidth(1)
    c.line(50, 700, W - 50, 700)

    # ── To / Re block ─────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 684, "TO:")
    c.setFont("Helvetica", 10)
    c.drawString(75, 684, "Strikaris Technology Inc.")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 670, "RE:")
    c.setFont("Helvetica", 10)
    c.drawString(75, 670, f"Quote {QUOTE['quote_id']} — Shopify Development Services")

    # ── Line items table ──────────────────────────────────────────────────────
    COL = {"no": 50, "desc": 72, "qty": 340, "up": 395, "total": 495}
    ROW_H = 20
    y = 644

    # Header row
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.rect(50, y - 4, W - 100, ROW_H, fill=1, stroke=0)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(COL["no"],    y + 4, "#")
    c.drawString(COL["desc"],  y + 4, "Description")
    c.drawString(COL["qty"],   y + 4, "Qty")
    c.drawString(COL["up"],    y + 4, "Unit Price")
    c.drawString(COL["total"], y + 4, "Line Total")
    c.setFillColorRGB(0, 0, 0)
    y -= ROW_H

    # Data rows
    c.setFont("Helvetica", 9)
    for idx, item in enumerate(line_items, 1):
        c.drawString(COL["no"],   y + 4, str(idx))
        c.drawString(COL["desc"], y + 4, item["description"])
        c.drawString(COL["qty"],  y + 4, str(item["qty"]))
        c.drawRightString(COL["up"]    + 65, y + 4, _fmt(item["unit_price"]))
        c.drawRightString(COL["total"] + 65, y + 4, _fmt(item["total"]))
        c.setLineWidth(0.4)
        c.line(50, y - 1, W - 50, y - 1)
        y -= ROW_H

    # Grand total
    grand_total = sum(i["total"] for i in line_items)
    c.setLineWidth(1)
    c.line(50, y + ROW_H, W - 50, y + ROW_H)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(COL["total"] - 5,  y + ROW_H + 6, "GRAND TOTAL:")
    c.drawRightString(COL["total"] + 65, y + ROW_H + 6, _fmt(grand_total))

    # ── Terms ─────────────────────────────────────────────────────────────────
    y -= 18
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(50, y,
        "This Purchase Order constitutes formal acceptance of the referenced quote.")
    y -= 12
    c.drawString(50, y,
        "Payment terms: NET-30.  All work performed per the agreed statement of work.")
    c.setFillColorRGB(0, 0, 0)

    # ── Signature block ───────────────────────────────────────────────────────
    y -= 48
    c.setLineWidth(0.8)
    c.line(50, y, 270, y)
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(55, y + 7, "K. Hassan")
    c.setFont("Helvetica", 9)
    c.drawString(50, y - 13, "Authorized Signature")
    c.drawString(50, y - 25, "Kaleel Hassan — Director of Operations")
    c.drawString(50, y - 37, "Khan Mall Development Corp.")

    # Initials box
    c.rect(W - 110, y - 12, 60, 36, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W - 80, y + 6, "KH")
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(W - 80, y - 15, "Initials")
    c.setFillColorRGB(0, 0, 0)

    c.save()
    return buf.getvalue()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_po(
    seed: int | None = None,
    variation: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """
    Generate a Khan Mall Purchase Order PDF.

    Purpose:
        Produces a signed PO PDF with optional variation from the original quote.
        Used by quote_demo.py to simulate Khan Mall's response.

    Args:
        seed:       Random seed for reproducible variation selection.
        variation:  Explicit variation name (overrides seed).
        output_dir: Directory to write PDF.  Defaults to system temp dir.

    Returns:
        dict with keys: pdf_path, variation, label, line_items,
                        po_total, quote_total, po_number, quote_id.

    Violations:
        Raises ImportError if reportlab is not installed.
        Raises ValueError if variation name is unrecognised.
    """
    if variation is None:
        variation = _pick_variation(seed)

    var_def = VARIATIONS.get(variation)
    if var_def is None:
        raise ValueError(
            f"Unknown variation: {variation!r}.  Choose from {list(VARIATIONS)}"
        )

    line_items = var_def["fn"](QUOTE["line_items"])
    po_total   = sum(i["total"] for i in line_items)
    po_number  = "KM-2026-0042"
    date_str   = datetime.now().strftime("%B %d, %Y")

    pdf_bytes = _build_pdf(line_items, po_number, date_str)

    out_dir  = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"khan_mall_po_{po_number}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    return {
        "pdf_path":    str(pdf_path),
        "variation":   variation,
        "label":       var_def["label"],
        "line_items":  line_items,
        "po_total":    po_total,
        "quote_total": QUOTE["total"],
        "po_number":   po_number,
        "quote_id":    QUOTE["quote_id"],
    }


if __name__ == "__main__":
    import subprocess
    import sys

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    result = generate_po(seed=seed)
    variance = abs(result["po_total"] - result["quote_total"]) / result["quote_total"] * 100
    print(f"PDF:       {result['pdf_path']}")
    print(f"Variation: {result['variation']}  —  {result['label']}")
    print(f"PO total:  ${result['po_total']:,}  (quoted ${result['quote_total']:,})")
    print(f"Variance:  {variance:.1f}%")
    subprocess.run(["open", result["pdf_path"]], check=False)
