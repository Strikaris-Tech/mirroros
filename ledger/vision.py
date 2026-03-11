"""
Nova Vision — PO extraction via Amazon Nova Pro (Bedrock)
=========================================================
Sends a PDF directly to Amazon Nova Pro and returns a structured
extraction of the purchase order fields.

Feature flag MOCK_VISION (default True) allows the full demo to run
without Bedrock access.  Flip to False once credentials are confirmed.

Usage:
    from ledger.vision import extract_po

    # Real mode (requires AWS credentials + AWS_BEARER_TOKEN_BEDROCK):
    result = extract_po(pdf_path, mock=False)

    # Mock mode (derives extraction from po_generator metadata):
    result = extract_po(pdf_path, mock=True, mock_data=po_result)

    # result keys:
    #   po_number         — PO identifier string
    #   reference_quote   — Strikaris quote ID being accepted
    #   date              — date string
    #   line_items        — list of {description, qty, unit_price, line_total}
    #   grand_total       — total amount on the PO
    #   signature_present — bool
    #   initials_present  — bool
    #   _source           — "mock" or "nova_pro"
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

# ── Feature flag ──────────────────────────────────────────────────────────────
# Flip to False once AWS_BEARER_TOKEN_BEDROCK is confirmed working.
MOCK_VISION = True

# ── Model ─────────────────────────────────────────────────────────────────────
NOVA_PRO_MODEL = "amazon.nova-pro-v1:0"

# ── Extraction prompt ─────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """\
You are extracting structured data from a purchase order document.
Return ONLY a valid JSON object — no markdown fences, no explanation.

Extract these exact fields:
{
  "po_number":        "<string>",
  "reference_quote":  "<string — the Strikaris quote number this PO accepts>",
  "date":             "<string>",
  "line_items": [
    {
      "description": "<string>",
      "qty":         <number>,
      "unit_price":  <number — USD, strip $ and commas>,
      "line_total":  <number — USD, strip $ and commas>
    }
  ],
  "grand_total":       <number — USD, strip $ and commas>,
  "signature_present": <boolean>,
  "initials_present":  <boolean>
}

Rules:
- Strip all currency symbols ($) and commas from numeric values.
- If a field is absent, use null.
- qty defaults to 1 if not shown explicitly.\
"""


# ── Real extraction via Nova Pro ──────────────────────────────────────────────

def _call_nova_pro(pdf_path: str) -> dict[str, Any]:
    """Send PDF bytes to Nova Pro via Bedrock Converse API and parse response."""
    import boto3

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    client    = boto3.client("bedrock-runtime", region_name="us-east-1")

    response = client.converse(
        modelId=NOVA_PRO_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "document": {
                        "format": "pdf",
                        "name":   "purchase_order",
                        "source": {"bytes": pdf_bytes},
                    }
                },
                {"text": EXTRACTION_PROMPT},
            ],
        }],
    )

    raw = response["output"]["message"]["content"][0]["text"].strip()
    # Strip markdown code fences if model wraps response anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ── Mock extraction ───────────────────────────────────────────────────────────

def _mock_from_po_data(mock_data: dict) -> dict[str, Any]:
    """
    Build a mock extraction result from po_generator metadata.

    Simulates what Nova Pro would return for the generated PDF — used to
    test the full MRS governance pipeline without a Bedrock API call.
    """
    return {
        "po_number":        mock_data["po_number"],
        "reference_quote":  mock_data["quote_id"],
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "line_items": [
            {
                "description": item["description"],
                "qty":         item["qty"],
                "unit_price":  item["unit_price"],
                "line_total":  item["total"],
            }
            for item in mock_data["line_items"]
        ],
        "grand_total":       mock_data["po_total"],
        "signature_present": True,
        "initials_present":  True,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def extract_po(
    pdf_path: str,
    mock: bool = MOCK_VISION,
    mock_data: dict | None = None,
) -> dict[str, Any]:
    """
    Extract purchase order data from a PDF.

    Purpose:
        Sends the PDF to Amazon Nova Pro for structured field extraction.
        In mock mode, returns data derived from po_generator metadata
        without making a Bedrock API call.

    Args:
        pdf_path:   Path to the PDF file to analyse.
        mock:       Use mock mode (default: True until Bedrock confirmed).
        mock_data:  po_generator result dict, required when mock=True.

    Returns:
        dict with keys: po_number, reference_quote, date, line_items,
                        grand_total, signature_present, initials_present,
                        _source ("mock" or "nova_pro").

    Violations:
        Raises ValueError if mock=True but mock_data is None.
        Raises ImportError if boto3 not installed (real mode).
        Raises json.JSONDecodeError if Nova Pro returns malformed JSON.
    """
    if mock:
        if mock_data is None:
            raise ValueError("mock_data is required when mock=True")
        result = _mock_from_po_data(mock_data)
        result["_source"] = "mock"
        return result

    result = _call_nova_pro(pdf_path)
    result["_source"] = "nova_pro"
    return result
