from __future__ import annotations

from typing import Any


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
                template += " [LLM could refine wording]"
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
        narrative += " Narasi dapat diperkaya oleh LLM."
    return {"score": score, "narrative": narrative}
