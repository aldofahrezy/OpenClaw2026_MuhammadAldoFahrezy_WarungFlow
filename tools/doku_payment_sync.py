"""Poll DOKU Check Status API and record bot order payment when SUCCESS."""

from __future__ import annotations

import os
from typing import Any

from config import has_doku_credentials
from tools import event_store
from tools.bot_service import simulate_mock_payment
from tools.doku_sandbox_provider import DokuSandboxProvider, _extract_transaction_status


def _doku_provider() -> DokuSandboxProvider | None:
    if not has_doku_credentials():
        return None
    return DokuSandboxProvider(
        (os.getenv("DOKU_CLIENT_ID") or "").strip(),
        (os.getenv("DOKU_SECRET_KEY") or "").strip(),
        (os.getenv("DOKU_SANDBOX_BASE_URL") or "").strip() or None,
    )


def _channel_label(payload: dict[str, Any]) -> str:
    channel = payload.get("channel")
    if isinstance(channel, dict) and channel.get("id"):
        return str(channel["id"]).replace("_", " ")
    service = payload.get("service")
    if isinstance(service, dict) and service.get("id"):
        return str(service["id"]).replace("_", " ")
    return "DOKU"


def sync_doku_order_payment(order_id: str) -> dict[str, Any]:
    """
    Query DOKU for invoice status; if SUCCESS, record payment in WarungFlow.

    Safe to call repeatedly (idempotent via simulate_mock_payment).
    """
    oid = (order_id or "").strip()
    if not oid:
        return {"status": "error", "detail": "missing_order_id"}

    order = event_store.get_bot_order(oid)
    if not order:
        return {"status": "error", "detail": "order_not_found"}

    if str(order.get("payment_status") or "").upper() == "PAID":
        return {"status": "already_paid", "order_id": oid, "payment_status": "PAID"}

    prov = _doku_provider()
    if prov is None:
        return {"status": "error", "detail": "doku_credentials_missing"}

    try:
        poll = prov.check_order_payment_status(oid)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc), "order_id": oid}

    raw = poll.get("raw") if isinstance(poll.get("raw"), dict) else {}
    txn_status = (
        str(poll.get("transaction_status") or poll.get("status") or "")
        .upper()
        .strip()
    )
    if not txn_status and raw:
        txn_status = _extract_transaction_status(raw)

    if txn_status == "SUCCESS":
        amount = int(
            (raw.get("order") or {}).get("amount")
            or order.get("amount_expected")
            or 0
        )
        method = _channel_label(raw) if raw else "DOKU"
        res = simulate_mock_payment(
            order_id=oid,
            amount=amount,
            payer_name=order.get("customer_name"),
            payment_method=method,
        )
        res["doku_transaction_status"] = txn_status
        res["synced_from"] = "doku_check_status"
        return res

    if txn_status in {"PENDING", "REDIRECT", "TIMEOUT", ""}:
        return {
            "status": "pending",
            "order_id": oid,
            "doku_transaction_status": txn_status or "UNKNOWN",
            "detail": "Pembayaran belum terkonfirmasi di DOKU. Coba lagi beberapa detik setelah bayar.",
        }

    return {
        "status": "not_paid",
        "order_id": oid,
        "doku_transaction_status": txn_status,
        "detail": f"Status DOKU: {txn_status}",
    }
