"""Deterministic WhatsApp order parser with product catalogue pricing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools.catalogue_tools import (
    calculate_order_total_from_catalogue,
    extract_order_items,
    load_product_catalogue_from_csv,
    normalize_catalogue_tool,
)

_ROOT = Path(__file__).resolve().parent.parent
_CATALOG_CANDIDATES = (
    _ROOT / "data" / "menu_price_catalog.json",
    _ROOT / "menu_price_catalog.json",
)

_BOT_META_RE = re.compile(r"<!--\s*bot:[^>]+-->", re.I)


def strip_internal_meta(text: str) -> str:
    """Remove machine-only markers (e.g. bot order id comments) from display text."""
    return _BOT_META_RE.sub("", text or "").strip()


def _bot_order_id_for_line(line: str) -> str | None:
    """Resolve ORD-BOT id from event store when the raw line has no embedded marker."""
    try:
        from tools import event_store

        target = strip_internal_meta(line)
        for bo in event_store.get_recent_bot_orders(200):
            oid = str(bo.get("order_id") or "")
            if not oid.upper().startswith("ORD-BOT"):
                continue
            candidates = [
                bo.get("raw_whatsapp_line"),
                f"{bo.get('raw_message', '')} - {bo.get('customer_name', '')}".strip(),
            ]
            for cand in candidates:
                if cand and strip_internal_meta(str(cand)) == target:
                    return oid.upper()
    except Exception:
        pass
    return None


def load_menu_catalog(path: Path | None = None) -> dict[str, int]:
    """Legacy JSON menu map — prefer product_catalogue.csv."""
    if path is not None:
        p = path
    else:
        p = next((c for c in _CATALOG_CANDIDATES if c.exists()), _CATALOG_CANDIDATES[0])
    if not p.exists():
        cat = load_product_catalogue_from_csv()
        return {
            _alias.lower(): int(row["unit_price"])
            for row in cat
            for _alias in row.get("aliases") or [row.get("product_name", "")]
            if row.get("product_name")
        }
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return {str(k).strip().lower(): int(v) for k, v in data.items()}


def _extract_customer_and_payer(text: str) -> tuple[str | None, str | None, str]:
    customer = None
    payer = None
    remainder = strip_internal_meta(text)
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
    for pat in (
        r"\batas\s+nama\s+([^\n,.]+?)(?:\s*$|\s*,)",
        r"\ban\.?\s+([^\n,.]+?)(?:\s*$|\s*,)",
        r"\ba\.n\.?\s+([^\n,.]+?)(?:\s*$|\s*,)",
    ):
        m_named = re.search(pat, remainder, re.IGNORECASE)
        if m_named:
            customer = m_named.group(1).strip()
            remainder = (remainder[: m_named.start()] + remainder[m_named.end() :]).strip()
            break
    m_dash = re.search(r"\s*-\s*([^\n]+?)\s*$", remainder)
    if m_dash:
        customer = m_dash.group(1).strip()
        remainder = remainder[: m_dash.start()].strip()
    return customer, payer, remainder


def _parse_money_tokens(text: str) -> dict[str, int | None]:
    out: dict[str, int | None] = {"total": None, "dp": None}
    t_lower = text.lower()
    for pat in (
        r"total\s*(?:rp\.?|idr)?\s*([\d\.\,]+)",
        r"total\s+([\d\.\,]+)",
    ):
        m = re.search(pat, t_lower)
        if m:
            out["total"] = _parse_id_number(m.group(1))
            break
    m_dp = re.search(r"\bdp\s*(?:rp\.?|idr)?\s*([\d\.\,]+)", t_lower) or re.search(
        r"uang\s+muka\s*(?:rp\.?|idr)?\s*([\d\.\,]+)", t_lower
    )
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
    if re.search(r"\bbayar\s+besok\b|\bbayar\s+nanti\b", tl):
        return "pay_later"
    if re.search(r"\btransfer\b|\bqris\b|\bva\b", tl):
        return "digital"
    if re.search(r"\bcash\b|\btunai\b", tl):
        return "cash"
    return None


def parse_order_message(
    raw_line: str,
    catalogue: list[dict[str, Any]] | None = None,
    order_id: str | None = None,
) -> dict[str, Any]:
    cat = normalize_catalogue_tool(catalogue or load_product_catalogue_from_csv())
    text = strip_internal_meta(raw_line)
    bot_oid = None
    m_bot = re.search(r"<!--\s*bot:(ORD-BOT-\d+)\s*-->", raw_line, re.I)
    if m_bot:
        bot_oid = m_bot.group(1).upper()
    oid = order_id or bot_oid or f"ORD-{abs(hash(text)) % 10_000_000:07d}"

    customer, payer, remainder = _extract_customer_and_payer(text)
    money = _parse_money_tokens(remainder)
    payment_hint = _detect_payment_hint(text)
    explicit_total = money.get("total")
    dp_amount = money.get("dp")

    items = extract_order_items(remainder or text, cat)
    calc = calculate_order_total_from_catalogue(items, cat)
    unknown = list(calc.get("unknown_products") or [])
    catalogue_total = calc.get("catalogue_total")

    amount_expected: int | None
    amount_source: str
    if explicit_total is not None:
        amount_expected = explicit_total
        amount_source = "explicit_total"
    elif catalogue_total is not None:
        amount_expected = catalogue_total
        amount_source = "catalogue"
    else:
        amount_expected = None
        amount_source = "none"

    discrepancy = bool(
        explicit_total is not None
        and catalogue_total is not None
        and explicit_total != catalogue_total
    )

    parser_status = "READY_FOR_RECONCILIATION"
    if unknown or amount_expected is None:
        parser_status = "NEEDS_REVIEW"
    if discrepancy:
        parser_status = "NEEDS_REVIEW"

    parser_notes: list[str] = []
    if discrepancy:
        parser_notes.append(
            f"Explicit total ({explicit_total}) differs from catalogue ({catalogue_total})"
        )
    if unknown:
        parser_notes.append(f"unknown_products={','.join(unknown)}")

    return {
        "order_id": oid,
        "raw": raw_line,
        "raw_message": text,
        "customer_name": customer,
        "customer_phone": None,
        "payer_name": payer,
        "payer_hint": payer,
        "items": calc.get("items") or [],
        "amount_expected": amount_expected,
        "catalogue_total": catalogue_total,
        "explicit_total": explicit_total,
        "amount_source": amount_source,
        "payment_hint": payment_hint,
        "dp_amount": dp_amount,
        "unknown_products": unknown,
        "discrepancy": discrepancy,
        "parser_status": parser_status,
        "status": parser_status,
        "parser_note": "; ".join(parser_notes),
    }


def parse_orders_batch(
    lines: list[str],
    catalogue: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    cat = catalogue or load_product_catalogue_from_csv()
    out: list[dict[str, Any]] = []
    seq = 0
    for line in lines:
        if not line.strip():
            continue
        seq += 1
        m_bot = re.search(r"ORD-BOT-\d+", line, re.I)
        bot_oid = _bot_order_id_for_line(line)
        oid = (
            (m_bot.group(0).upper() if m_bot else None)
            or bot_oid
            or f"ORD-{seq:04d}"
        )
        out.append(parse_order_message(line, catalogue=cat, order_id=oid))
    return out
