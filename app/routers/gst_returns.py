"""Government-ready GST return exports: GSTR-1 (outward) and GSTR-3B (summary).

Output is shaped to match the GSTN JSON schema (sections b2b / b2cs / hsn for
GSTR-1; sup_details / itc_elg for GSTR-3B). It is computed from invoices, their
items, and the customer's GST state vs the seller's home state (COMPANY_STATE_CODE).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date
from decimal import Decimal
from collections import defaultdict

from .. import models
from ..database import get_db
from ..gst import COMPANY_STATE_CODE, state_code_from_gstin, is_intra_state, split_gst

router = APIRouter(prefix="/gst", tags=["gst_returns"])


def _f(v) -> float:
    """Round a Decimal/number to 2dp float for JSON."""
    return float(Decimal(str(v or 0)).quantize(Decimal("0.01")))


def _period(d: date) -> str:
    """GSTN return period format: MMYYYY."""
    return d.strftime("%m%Y")


def _ddmmyyyy(d: date) -> str:
    return d.strftime("%d-%m-%Y") if d else ""


def _sale_invoices(db: Session, date_from: date, date_to: date):
    return (
        db.query(models.Invoice)
        .options(joinedload(models.Invoice.items), joinedload(models.Invoice.customer))
        .filter(
            models.Invoice.invoice_type == "sale",
            models.Invoice.status == "active",
            models.Invoice.invoice_date >= date_from,
            models.Invoice.invoice_date <= date_to,
        )
        .all()
    )


def _line_tax(item, intra: bool):
    """Return (taxable, rate, cgst, sgst, igst) for one invoice item."""
    taxable = Decimal(str(item.selling_price or 0)) * Decimal(str(item.quantity or 0))
    rate = Decimal(str(item.tax_percent or 0))
    tax = taxable * rate / Decimal("100")
    if intra:
        cgst = (tax / Decimal("2")).quantize(Decimal("0.01"))
        sgst = tax - cgst
        igst = Decimal("0")
    else:
        cgst = sgst = Decimal("0")
        igst = tax
    return taxable, rate, cgst, sgst, igst


@router.get("/gstr1")
def get_gstr1(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    invoices = _sale_invoices(db, date_from, date_to)

    # Product HSN lookup
    product_ids = {it.product_id for inv in invoices for it in inv.items if it.product_id}
    hsn_map = {}
    if product_ids:
        for p in db.query(models.Product).filter(models.Product.id.in_(product_ids)).all():
            hsn_map[p.id] = (p.hsncode or "", p.item or "", p.unit or "")

    b2b_by_ctin = defaultdict(list)
    b2cs_acc = defaultdict(lambda: {"txval": Decimal("0"), "iamt": Decimal("0"),
                                    "camt": Decimal("0"), "samt": Decimal("0")})
    hsn_acc = defaultdict(lambda: {"qty": Decimal("0"), "txval": Decimal("0"),
                                   "iamt": Decimal("0"), "camt": Decimal("0"), "samt": Decimal("0"),
                                   "desc": "", "uqc": "NOS"})

    for inv in invoices:
        pos = inv.place_of_supply or COMPANY_STATE_CODE
        intra = is_intra_state(pos)
        customer = inv.customer
        ctin = (customer.gstin if customer else None) or None

        # Per-rate aggregation within the invoice (GSTN groups items by rate)
        by_rate = defaultdict(lambda: {"txval": Decimal("0"), "iamt": Decimal("0"),
                                       "camt": Decimal("0"), "samt": Decimal("0")})
        inv_total = Decimal("0")
        for it in inv.items:
            taxable, rate, cgst, sgst, igst = _line_tax(it, intra)
            r = by_rate[float(rate)]
            r["txval"] += taxable
            r["camt"] += cgst
            r["samt"] += sgst
            r["iamt"] += igst
            inv_total += taxable + cgst + sgst + igst

            # HSN summary
            hsn, name, uqc = hsn_map.get(it.product_id, ("", "", "NOS"))
            h = hsn_acc[(hsn, float(rate))]
            h["qty"] += Decimal(str(it.quantity or 0))
            h["txval"] += taxable
            h["camt"] += cgst
            h["samt"] += sgst
            h["iamt"] += igst
            h["desc"] = name
            h["uqc"] = uqc or "NOS"

        itms = []
        for i, (rate, v) in enumerate(sorted(by_rate.items()), start=1):
            itms.append({
                "num": i,
                "itm_det": {
                    "rt": rate,
                    "txval": _f(v["txval"]),
                    "iamt": _f(v["iamt"]),
                    "camt": _f(v["camt"]),
                    "samt": _f(v["samt"]),
                },
            })

        if ctin:
            # B2B: registered customer
            b2b_by_ctin[ctin].append({
                "inum": inv.invoice_number,
                "idt": _ddmmyyyy(inv.invoice_date),
                "val": _f(inv_total),
                "pos": pos,
                "rchrg": "N",
                "inv_typ": "R",
                "itms": itms,
            })
        else:
            # B2C (small): summarize by place of supply + rate
            for rate, v in by_rate.items():
                key = (pos, rate, "INTRA" if intra else "INTER")
                acc = b2cs_acc[key]
                acc["txval"] += v["txval"]
                acc["iamt"] += v["iamt"]
                acc["camt"] += v["camt"]
                acc["samt"] += v["samt"]

    b2b = [{"ctin": ctin, "inv": inv_list} for ctin, inv_list in b2b_by_ctin.items()]

    b2cs = []
    for (pos, rate, sply_ty), v in b2cs_acc.items():
        b2cs.append({
            "sply_ty": sply_ty,
            "pos": pos,
            "typ": "OE",
            "rt": rate,
            "txval": _f(v["txval"]),
            "iamt": _f(v["iamt"]),
            "camt": _f(v["camt"]),
            "samt": _f(v["samt"]),
        })

    hsn_data = []
    for i, ((hsn, rate), v) in enumerate(sorted(hsn_acc.items()), start=1):
        hsn_data.append({
            "num": i,
            "hsn_sc": hsn,
            "desc": v["desc"],
            "uqc": v["uqc"],
            "qty": _f(v["qty"]),
            "rt": rate,
            "txval": _f(v["txval"]),
            "iamt": _f(v["iamt"]),
            "camt": _f(v["camt"]),
            "samt": _f(v["samt"]),
        })

    return {
        "gstin": None,  # set the seller GSTIN at filing time
        "fp": _period(date_to),
        "from": str(date_from),
        "to": str(date_to),
        "b2b": b2b,
        "b2cs": b2cs,
        "hsn": {"data": hsn_data},
    }


@router.get("/gstr3b")
def get_gstr3b(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    invoices = _sale_invoices(db, date_from, date_to)

    # 3.1(a) Outward taxable supplies (from sales)
    out_txval = Decimal("0")
    out_iamt = Decimal("0")
    out_camt = Decimal("0")
    out_samt = Decimal("0")
    for inv in invoices:
        intra = is_intra_state(inv.place_of_supply or COMPANY_STATE_CODE)
        for it in inv.items:
            taxable, rate, cgst, sgst, igst = _line_tax(it, intra)
            out_txval += taxable
            out_camt += cgst
            out_samt += sgst
            out_iamt += igst

    # 4 Eligible ITC (from input GST accounts on purchases)
    def _itc_for_code(code):
        result = (
            db.query(
                func.coalesce(func.sum(models.JournalLine.debit), 0).label("d"),
                func.coalesce(func.sum(models.JournalLine.credit), 0).label("c"),
            )
            .join(models.Account, models.JournalLine.account_id == models.Account.id)
            .join(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
            .filter(
                models.Account.code == code,
                models.JournalEntry.entry_date >= date_from,
                models.JournalEntry.entry_date <= date_to,
            )
            .first()
        )
        return Decimal(str(result.d)) - Decimal(str(result.c)) if result else Decimal("0")

    itc_camt = _itc_for_code("2111")
    itc_samt = _itc_for_code("2112")
    itc_iamt = _itc_for_code("2113")

    return {
        "gstin": None,
        "fp": _period(date_to),
        "from": str(date_from),
        "to": str(date_to),
        "sup_details": {
            "osup_det": {
                "txval": _f(out_txval),
                "iamt": _f(out_iamt),
                "camt": _f(out_camt),
                "samt": _f(out_samt),
                "csamt": 0,
            }
        },
        "itc_elg": {
            "itc_avl": [
                {
                    "ty": "OTH",
                    "iamt": _f(itc_iamt),
                    "camt": _f(itc_camt),
                    "samt": _f(itc_samt),
                    "csamt": 0,
                }
            ]
        },
    }
