from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parent.parent
_CATALOG_CANDIDATES = (
    _ROOT / "data" / "menu_price_catalog.json",
    _ROOT / "menu_price_catalog.json",
)


def load_menu_catalog(path: Path | None = None) -> dict[str, int]:
    if path is not None:
        p = path
    else:
        p = next((c for c in _CATALOG_CANDIDATES if c.exists()), _CATALOG_CANDIDATES[0])
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return {str(k).strip().lower(): int(v) for k, v in data.items()}


def _extract_customer_and_payer(text: str) -> tuple[str | None, str | None, str]:
    """Returns (customer_name, payer_name, remainder_without_trailing_name)."""
    customer = None
    payer = None
    remainder = text.strip()
    # "udah bayar dari nama X - Y" or "dari nama X - Y"
    m_payer = re.search(
        r"(?:udah\s+)?bayar\s+dari\s+nama\s+([^-\n]+?)\s*-\s*([^-\n]+)\s*$",
        remainder,
        re.IGNORECASE,
    )
    if m_payer:
        payer = m_payer.group(1).strip()
        customer = m_payer.group(2).strip()
        remainder = remainder[: m_payer.start()].strip()
        return customer, payer, remainder
    # trailing "- Name"
    m_dash = re.search(r"\s*-\s*([^\n]+?)\s*$", remainder)
    if m_dash:
        customer = m_dash.group(1).strip()
        remainder = remainder[: m_dash.start()].strip()
    return customer, payer, remainder


def _parse_money_tokens(text: str) -> dict[str, int | None]:
    """Extract total, dp, and hints."""
    out: dict[str, int | None] = {"total": None, "dp": None}
    t_lower = text.lower()
    # total 36000 / total: 36000 / total Rp 36.000
    for pat in (
        r"total\s*(?:rp\.?|idr)?\s*([\d\.\,]+)",
        r"total\s+([\d\.\,]+)",
    ):
        m = re.search(pat, t_lower)
        if m:
            out["total"] = _parse_id_number(m.group(1))
            break
    m_dp = re.search(
        r"\bdp\s*(?:rp\.?|idr)?\s*([\d\.\,]+)", t_lower
    ) or re.search(r"uang\s+muka\s*(?:rp\.?|idr)?\s*([\d\.\,]+)", t_lower)
    if m_dp:
        out["dp"] = _parse_id_number(m_dp.group(1))
    return out


def _parse_id_number(s: str) -> int | None:
    s = s.strip().replace(".", "").replace(",", "")
    if not s.isdigit():
        return None
    return int(s)


def _detect_payment_hint(text: str) -> str | None:
    tl = text.lower()
    if re.search(r"\bbayar\s+besok\b", tl):
        return "pay_tomorrow"
    if re.search(r"\btransfer\b|\bqris\b|\bva\b", tl):
        return "digital"
    if re.search(r"\bcash\b|\btunai\b", tl):
        return "cash"
    return None


def _count_items_and_estimate(remainder: str, catalog: dict[str, int]) -> tuple[int | None, str]:
    """
    Look for patterns like 'nasi uduk 3' or 'ayam geprek 2'.
    Sum estimated line totals.
    """
    tl = remainder.lower()
    estimated = 0
    found_any = False
    notes: list[str] = []
    # item qty after item name
    for item, price in catalog.items():
        for m in re.finditer(re.escape(item) + r"\s*(\d+)", tl):
            q = int(m.group(1))
            estimated += price * q
            found_any = True
            notes.append(f"{item} x{q} @ {price}")
    if not found_any:
        return None, "no_menu_items_matched"
    return estimated, "; ".join(notes)


def parse_order_message(
    raw_line: str,
    catalog: dict[str, int] | None = None,
    order_id: str | None = None,
) -> dict[str, Any]:
    """
    Deterministic parse of a single order line (e.g. WhatsApp style).
    """
    catalog = catalog or load_menu_catalog()
    text = raw_line.strip()
    oid = order_id or f"ORD-{abs(hash(text)) % 10_000_000:07d}"

    customer, payer, remainder = _extract_customer_and_payer(text)
    money = _parse_money_tokens(remainder)
    payment_hint = _detect_payment_hint(text)

    explicit_total = money.get("total")
    dp_amount = money.get("dp")

    amount_expected: int | None = explicit_total
    status: str = "OK"
    parser_note_parts: list[str] = []

    if explicit_total is None:
        est, est_note = _count_items_and_estimate(remainder, catalog)
        if est is not None:
            amount_expected = est
            parser_note_parts.append(f"estimated_from_catalog: {est_note}")
        else:
            amount_expected = None
            status = "NEEDS_REVIEW"
            parser_note_parts.append(
                "amount_expected=null; could not find explicit total or catalog match"
            )

    if dp_amount is not None and explicit_total is not None:
        parser_note_parts.append(
            f"partial_payment_dp={dp_amount} against total={explicit_total}"
        )
    elif dp_amount is not None and amount_expected is not None:
        parser_note_parts.append(
            f"partial_payment_dp={dp_amount} against expected={amount_expected}"
        )

    if payment_hint == "pay_tomorrow":
        parser_note_parts.append("payment_promise: bayar besok")

    if payer and customer and payer.lower() != customer.lower():
        parser_note_parts.append(f"payer_differs: payer={payer}, customer={customer}")

    return {
        "order_id": oid,
        "raw": raw_line,
        "customer_name": customer,
        "payer_name": payer,
        "amount_expected": amount_expected,
        "dp_amount": dp_amount,
        "payment_hint": payment_hint,
        "status": status,
        "parser_note": "; ".join(parser_note_parts) if parser_note_parts else "",
    }


def parse_orders_batch(lines: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        out.append(parse_order_message(line, order_id=f"ORD-{i+1:04d}"))
    return out
