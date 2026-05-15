from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz

_HONORIFIC_RE = re.compile(
    r"^(?:pak|bu|ibu|bapak|mas|mbak|bang|teh|kak|tante|om)\s+",
    re.IGNORECASE,
)
_LEGAL_SUFFIX_RE = re.compile(r"\b(?:pt|cv|tbk|ud|firma)\b", re.IGNORECASE)
_PM_ALIASES = {
    "bank_transfer": "transfer",
    "wire": "transfer",
    "virtual_account": "va",
}

_FUZZY_REF_STRONG = 85
_FUZZY_REF_WEAK = 70
_MATCH_CONFIDENCE_FLOOR = 38.0

_W_REF = 50.0
_W_AMT = 30.0
_W_NAME = 20.0


def _norm_id_name(s: str | None) -> str:
    """Normalize Indonesian personal/company names for fuzzy comparison."""
    if not s:
        return ""
    text = s.strip().lower().replace("dj", "j")
    while True:
        m = _HONORIFIC_RE.match(text)
        if not m:
            break
        text = text[m.end() :].strip()
    text = _LEGAL_SUFFIX_RE.sub(" ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _norm_payment_method(pm: str | None) -> str:
    if not pm:
        return ""
    key = str(pm).lower().strip()
    return _PM_ALIASES.get(key, key)


def _name_score(a: str | None, b: str | None) -> float:
    na, nb = _norm_id_name(a), _norm_id_name(b)
    if not na or not nb:
        return 0.0
    token = float(fuzz.token_set_ratio(na, nb))
    partial = float(fuzz.partial_ratio(na, nb))
    return (0.5 * token + 0.5 * partial) / 100.0


def _payment_note_text(pay: dict[str, Any]) -> str:
    ref = str(pay.get("reference_note") or "").strip()
    desc = str(pay.get("description") or "").strip()
    return f"{ref} {desc}".strip()


def _note_lower(pay: dict[str, Any]) -> str:
    return _payment_note_text(pay).lower().strip()


def _order_id_in_note(order: dict[str, Any], pay: dict[str, Any]) -> bool:
    oid = order.get("order_id")
    if not oid:
        return False
    oid_s = str(oid).lower().strip()
    return oid_s in _note_lower(pay)


def _fuzzy_name_in_note(name: str | None, note: str) -> float:
    """Return 0–1 fuzzy overlap between a name and a transaction note."""
    nn = _norm_id_name(name)
    note_n = _norm_id_name(note)
    if not nn or not note_n:
        return 0.0
    token = float(fuzz.token_set_ratio(nn, note_n))
    partial = float(fuzz.partial_ratio(nn, note_n))
    return max(token, partial) / 100.0


def _amount_match_score(expected: int | None, paid: int | None) -> float:
    if expected is None or paid is None:
        return 0.0
    if expected == 0:
        return 1.0 if paid == 0 else 0.0
    diff = abs(expected - paid)
    return 1.0 - min(1.0, diff / max(expected, 1))


def _ref_note_score(order: dict[str, Any], pay: dict[str, Any]) -> float:
    note = _payment_note_text(pay)
    if not note:
        return 0.0
    note_l = note.lower().strip()

    oid = order.get("order_id")
    if oid:
        oid_s = str(oid).lower().strip()
        if oid_s in note_l:
            return 1.0

    strength = 0.0
    for key in ("customer_name", "payer_name"):
        v = order.get(key)
        if not v:
            continue
        name_s = str(v).lower().strip()
        if name_s in note_l:
            strength = max(strength, 1.0)
            continue
        fs = _fuzzy_name_in_note(name_s, note_l)
        if fs * 100 >= _FUZZY_REF_STRONG:
            strength = max(strength, 1.0)
        elif fs * 100 >= _FUZZY_REF_WEAK:
            strength = max(strength, 0.65)

    if strength >= 1.0:
        return 1.0
    if strength >= 0.65:
        return 0.75
    if strength > 0:
        return 0.6
    return 0.0


def _payment_hint_consistency(order: dict[str, Any], pay: dict[str, Any]) -> float:
    oh = order.get("payment_hint")
    pm = _norm_payment_method(pay.get("payment_method"))
    if not oh or not pm:
        return 0.5
    if oh == "digital" and pm in {"qris", "transfer", "va"}:
        return 1.0
    if oh == "cash" and pm == "cash":
        return 1.0
    if oh == "pay_tomorrow" and pm in {"pending", "promise"}:
        return 1.0
    return 0.2


def _confidence(
    order: dict[str, Any], pay: dict[str, Any], paid_amount: int
) -> tuple[float, dict[str, float]]:
    expected = order.get("amount_expected")
    cust = order.get("customer_name")
    payer_o = order.get("payer_name")
    payer_p = pay.get("payer_name") or pay.get("sender_name")

    n1 = max(_name_score(cust, payer_p), _name_score(payer_o, payer_p))
    n2 = _name_score(cust, pay.get("counterparty"))
    name_part = max(n1, n2)

    amt_part = _amount_match_score(
        expected if isinstance(expected, int) else None, paid_amount
    )
    ref_part = _ref_note_score(order, pay)

    score = _W_REF * ref_part + _W_AMT * amt_part + _W_NAME * name_part
    breakdown = {
        "reference_component": _W_REF * ref_part,
        "amount_match_component": _W_AMT * amt_part,
        "name_match_component": _W_NAME * name_part,
        "order_id_in_note": 1.0 if _order_id_in_note(order, pay) else 0.0,
    }
    return score, breakdown


def _payment_id(pay: dict[str, Any]) -> str:
    return str(pay.get("transaction_id") or pay.get("id") or pay.get("payment_id") or "")


def _orders_cited_in_payment(
    orders: list[dict[str, Any]], pay: dict[str, Any]
) -> list[dict[str, Any]]:
    note_l = _note_lower(pay)
    cited: list[dict[str, Any]] = []
    for order in orders:
        oid = order.get("order_id")
        if oid and str(oid).lower().strip() in note_l:
            cited.append(order)
    return cited


def _reconcile_status(
    expected: int | None, matched_total: int, confidence: float
) -> str:
    if expected is None:
        if confidence >= 55:
            return "NEEDS_REVIEW"
        return "UNKNOWN"
    if confidence < 50:
        return "NEEDS_REVIEW"
    if matched_total == expected:
        return "PAID"
    if matched_total < expected:
        return "PARTIALLY_PAID"
    if matched_total > expected:
        return "OVERPAID"
    return "UNPAID"


def reconcile_orders(
    orders: list[dict[str, Any]],
    payments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Globally sorted reconciliation with order-ID-first mandatory assignment.
    """
    used_payment_ids: set[str] = set()
    matched_orders: dict[str, tuple[float, dict[str, Any], int, dict[str, float]]] = {}

    # Phase 1: payments that cite an order_id in the note MUST go to that order.
    for pay in payments:
        pid = _payment_id(pay)
        if pid and pid in used_payment_ids:
            continue
        amt = pay.get("amount")
        if amt is None:
            continue
        paid_amt = int(amt)
        cited = _orders_cited_in_payment(orders, pay)
        if not cited:
            continue
        if len(cited) == 1:
            order = cited[0]
        else:
            order = max(
                cited,
                key=lambda o: _confidence(o, pay, paid_amt)[0],
            )
        oid = str(order.get("order_id"))
        if oid in matched_orders:
            continue
        conf, breakdown = _confidence(order, pay, paid_amt)
        matched_orders[oid] = (conf, pay, paid_amt, breakdown)
        if pid:
            used_payment_ids.add(pid)

    # Phase 2: greedy best-match for remaining orders/payments.
    pairs: list[tuple[tuple[int, float], float, dict[str, Any], dict[str, Any], int, dict[str, float]]] = []
    for order in orders:
        oid = str(order.get("order_id"))
        if oid in matched_orders:
            continue
        for pay in payments:
            pid = _payment_id(pay)
            if pid and pid in used_payment_ids:
                continue
            amt = pay.get("amount")
            if amt is None:
                continue
            paid_amt = int(amt)
            conf, breakdown = _confidence(order, pay, paid_amt)
            if conf < _MATCH_CONFIDENCE_FLOOR:
                continue
            id_lock = 1 if _order_id_in_note(order, pay) else 0
            pairs.append(((id_lock, conf), conf, order, pay, paid_amt, breakdown))

    pairs.sort(key=lambda x: (x[0][0], x[0][1], x[1]), reverse=True)

    for _sort_key, conf, order, pay, paid_amt, breakdown in pairs:
        oid = str(order.get("order_id"))
        pid = _payment_id(pay)
        if oid in matched_orders or (pid and pid in used_payment_ids):
            continue
        matched_orders[oid] = (conf, pay, paid_amt, breakdown)
        if pid:
            used_payment_ids.add(pid)

    results: list[dict[str, Any]] = []
    for order in orders:
        oid = str(order.get("order_id"))
        if oid not in matched_orders:
            exp = order.get("amount_expected")
            st = "UNKNOWN" if exp is None else "UNPAID"
            results.append(
                {
                    "order_id": oid,
                    "status": st,
                    "matched_payment_ids": [],
                    "matched_amount": 0,
                    "confidence": 0.0,
                    "confidence_breakdown": {},
                    "notes": "no_payments_in_pool" if not payments else "no_confident_match",
                }
            )
            continue

        conf, pay, paid_amt, breakdown = matched_orders[oid]
        pid = _payment_id(pay)
        exp = order.get("amount_expected")
        expected_int = int(exp) if isinstance(exp, int) else None

        status = _reconcile_status(expected_int, paid_amt, conf)
        if status == "UNKNOWN" and conf >= 60:
            status = "NEEDS_REVIEW"

        results.append(
            {
                "order_id": oid,
                "status": status,
                "matched_payment_ids": [pid] if pid else [],
                "matched_amount": paid_amt,
                "confidence": round(conf, 2),
                "confidence_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
                "notes": pay.get("description") or pay.get("reference_note") or "",
            }
        )

    return results


def detect_payment_issues(
    orders: list[dict[str, Any]], reconciliation: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    by_oid = {r["order_id"]: r for r in reconciliation}
    for o in orders:
        oid = str(o.get("order_id"))
        r = by_oid.get(oid)
        if not r:
            continue
        st = r.get("status")
        if st in {"PARTIALLY_PAID", "UNPAID", "OVERPAID", "NEEDS_REVIEW", "UNKNOWN"}:
            issues.append(
                {
                    "order_id": oid,
                    "issue_type": st,
                    "detail": r.get("notes") or "",
                    "confidence": r.get("confidence"),
                }
            )
    return issues
