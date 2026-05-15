from __future__ import annotations

from typing import Any


def generate_daily_report(
    merchant: dict[str, Any],
    summary: dict[str, Any],
    health: dict[str, Any],
    reconciliation: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Daily Report — {merchant.get('name', 'Warung')}",
        "",
        "## Cashflow",
        f"- Expected: Rp {summary.get('expected_revenue', 0):,}",
        f"- Collected: Rp {summary.get('collected_revenue', 0):,}",
        f"- Expenses: Rp {summary.get('expenses', 0):,}",
        f"- Net: Rp {summary.get('net_cash_position', 0):,}",
        "",
        f"## Health score: {health.get('score')}",
        "",
        "## Reconciliation snapshot",
    ]
    for r in reconciliation[:20]:
        lines.append(
            f"- {r.get('order_id')}: {r.get('status')} (matched Rp {r.get('matched_amount', 0):,})"
        )
    return "\n".join(lines)


def validate_outputs(
    state_summary: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ok = True
    for name, present in state_summary.items():
        passed = bool(present)
        checks.append({"check": name, "passed": passed})
        ok = ok and passed
    return {"ok": ok, "checks": checks}
