from __future__ import annotations

from typing import Any

from tools.llm_client import refine_financing_narrative, refine_payment_reminder


def merchant_display_name(merchant: dict[str, Any]) -> str:
    return str(
        merchant.get("merchant_name") or merchant.get("name") or "Warung"
    ).strip()


def merchant_owner_name(merchant: dict[str, Any]) -> str:
    return str(merchant.get("owner_name") or merchant.get("owner") or "").strip()


def generate_daily_report(
    merchant: dict[str, Any],
    summary: dict[str, Any],
    health: dict[str, Any],
    reconciliation: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Daily Report — {merchant_display_name(merchant)}",
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

def generate_reminders(
    orders: list[dict[str, Any]], reconciliation: list[dict[str, Any]], llm_mode: str
) -> list[dict[str, Any]]:
    by_oid = {r["order_id"]: r for r in reconciliation}
    out: list[dict[str, Any]] = []
    for o in orders:
        oid = str(o.get("order_id"))
        r = by_oid.get(oid)
        if not r:
            continue
        if r.get("status") in {"UNPAID", "PARTIALLY_PAID"}:
            name = o.get("customer_name") or "Bapak/Ibu pelanggan"
            amt = o.get("amount_expected")
            paid = int(r.get("matched_amount") or 0)
            template = (
                f"Halo {name}, untuk pesanan {oid} "
                f"total Rp {amt or 'TBD'}. "
                f"Saat ini kami catat pembayaran Rp {paid}. "
                "Mohon konfirmasi jika sudah transfer. Terima kasih."
            )
            if llm_mode == "live":
                template = refine_payment_reminder(
                    str(name), oid, amt, paid, template
                )
            out.append({"order_id": oid, "channel": "whatsapp", "text": template})
    return out


def generate_financing_readiness(
    health: dict[str, Any], validation: dict[str, Any], llm_mode: str
) -> dict[str, Any]:
    score = int(health.get("score") or 0)
    narrative = (
        f"Financing readiness snapshot: internal health score {score}/100. "
        "Rekonsiliasi harian dan bukti digital meningkatkan kredibilitas ke bank."
    )
    if validation.get("ok") is False:
        narrative += " Perhatian: laporan memerlukan review sebelum diajukan."
    if llm_mode == "live":
        narrative = refine_financing_narrative(narrative, score)
    return {"score": score, "narrative": narrative}
