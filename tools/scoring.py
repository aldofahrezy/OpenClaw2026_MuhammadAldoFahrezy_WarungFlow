from __future__ import annotations

from typing import Any


def calculate_cashflow(
    reconciliation: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    expenses: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_total = 0
    collected = 0
    for o in orders:
        exp = o.get("amount_expected")
        if isinstance(exp, int):
            expected_total += exp
    for r in reconciliation:
        if r.get("status") in {"PAID", "PARTIALLY_PAID", "OVERPAID"}:
            collected += int(r.get("matched_amount") or 0)

    expense_total = sum(int(e.get("amount") or 0) for e in expenses)
    net = collected - expense_total
    return {
        "expected_revenue": expected_total,
        "collected_revenue": collected,
        "expenses": expense_total,
        "net_cash_position": net,
        "collection_rate": round(
            (collected / expected_total * 100) if expected_total else 0.0, 2
        ),
    }


def score_cashflow_health(summary: dict[str, Any]) -> dict[str, Any]:
    rate = float(summary.get("collection_rate") or 0)
    net = int(summary.get("net_cash_position") or 0)
    score = min(100, max(0, int(rate * 0.7 + (20 if net >= 0 else 0))))
    return {"score": score, "drivers": {"collection_rate": rate, "net": net}}
