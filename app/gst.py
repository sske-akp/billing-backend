"""GST helpers: place-of-supply resolution and intra/inter-state determination.

Indian GST splits tax by place of supply:
- Intra-state (buyer state == seller state)  -> CGST + SGST (half each)
- Inter-state (buyer state != seller state)  -> IGST (full)

State code = first 2 digits of the 15-char GSTIN.
"""
import os
from decimal import Decimal
from typing import Optional

# Seller's home state code. Placeholder default (33 = Tamil Nadu); override via env.
COMPANY_STATE_CODE: str = os.environ.get("COMPANY_STATE_CODE", "33")


def state_code_from_gstin(gstin: Optional[str]) -> Optional[str]:
    """Return the 2-digit state code from a GSTIN, or None if not derivable."""
    if not gstin:
        return None
    cleaned = gstin.strip()
    if len(cleaned) < 2 or not cleaned[:2].isdigit():
        return None
    return cleaned[:2]


def is_intra_state(party_state: Optional[str]) -> bool:
    """True when the supply is intra-state (CGST+SGST). Unknown party state
    defaults to intra-state, the common case for local retail."""
    if not party_state:
        return True
    return party_state == COMPANY_STATE_CODE


def split_gst(amount: Decimal, party_state: Optional[str]) -> dict:
    """Split a GST amount into CGST/SGST (intra) or IGST (inter).

    Halves are rounded to 2 dp with the remainder pushed to SGST so the parts
    always sum back to ``amount`` exactly (keeps journal entries balanced).
    Returns a dict with keys cgst, sgst, igst (Decimals; zeros where N/A).
    """
    amount = Decimal(str(amount or 0))
    if is_intra_state(party_state):
        cgst = (amount / Decimal("2")).quantize(Decimal("0.01"))
        sgst = amount - cgst
        return {"cgst": cgst, "sgst": sgst, "igst": Decimal("0")}
    return {"cgst": Decimal("0"), "sgst": Decimal("0"), "igst": amount}
