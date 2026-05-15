from __future__ import annotations

import re
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    import difflib

    class _Fuzz:
        @staticmethod
        def ratio(a: str, b: str) -> float:
            return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100

    fuzz = _Fuzz()  # type: ignore[misc, assignment]


def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def _name_score(a: str | None, b: str | None) -> float:
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return 0.0
    return float(fuzz.ratio(na, nb)) / 100.0


def _amount_match_score(expected: int | None, paid: int | None) -> float:
    if expected is None or paid is None:
        return 0.0
    if expected == 0:
        return 1.0 if paid == 0 else 0.0
    diff = abs(expected - paid)
    ratio = 1.0 - min(1.0, diff / max(expected, 1))
    return ratio


def _ref_note_score(order: dict[str, Any], pay: dict[str, Any]) -> float:
    note = (pay.get("reference_note") or "") + " " + (pay.get("description") or "")
    note_l = note.lower()
    hits = 0
    for key in ("customer_name", "payer_name", "order_id"):
        v = order.get(key)
        if v and str(v).lower() in note_l:
            hits += 1
    if hits >= 2:
        return 1.0
    if hits == 1:
        return 0.6
    return 0.0


def _payment_hint_consistency(order: dict[str, Any], pay: dict[str, Any]) -> float:
    oh = order.get("payment_hint")
    pm = pay.get("payment_method")
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
    hint_part = _payment_hint_consistency(order, pay)

    score = 40 * name_part + 40 * amt_part + 15 * ref_part + 5 * hint_part
    breakdown = {
        "name_match_component": 40 * name_part,
        "amount_match_component": 40 * amt_part,
        "reference_component": 15 * ref_part,
        "hint_component": 5 * hint_part,
    }
    return score, breakdown


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
    Greedy best-match reconciliation with fuzzy names and confidence scoring.
    """
    used_payment_ids: set[str] = set()
    results: list[dict[str, Any]] = []

    for order in orders:
        oid = str(order.get("order_id"))
        best: tuple[float, dict[str, Any], int] | None = None

        for pay in payments:
            pid = str(pay.get("id") or pay.get("payment_id") or "")
            if pid and pid in used_payment_ids:
                continue
            amt = pay.get("amount")
            if amt is None:
                continue
            paid_amt = int(amt)
            conf, breakdown = _confidence(order, pay, paid_amt)
            if best is None or conf > best[0]:
                best = (conf, pay, paid_amt)

        if best is None:
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
                    "notes": "no_payments_in_pool",
                }
            )
            continue

        conf, pay, paid_amt = best
        if conf < 38.0:
            exp = order.get("amount_expected")
            st = "UNKNOWN" if exp is None else "UNPAID"
            results.append(
                {
                    "order_id": oid,
                    "status": st,
                    "matched_payment_ids": [],
                    "matched_amount": 0,
                    "confidence": round(conf, 2),
                    "confidence_breakdown": {},
                    "notes": "no_confident_match",
                }
            )
            continue
        pid = str(pay.get("id") or pay.get("payment_id") or "")
        if pid:
            used_payment_ids.add(pid)

        exp = order.get("amount_expected")
        expected_int = int(exp) if isinstance(exp, int) else None

        # DP / partial: if order has dp and payment equals dp, still PARTIALLY_PAID vs total
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
                "notes": pay.get("description") or "",
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
