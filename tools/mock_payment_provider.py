from __future__ import annotations

import logging
from typing import Any

from .payment_adapter import PaymentProvider

logger = logging.getLogger(__name__)


class MockPaymentProvider(PaymentProvider):
    def __init__(self) -> None:
        self._requests: dict[str, dict[str, Any]] = {}
        self._by_order: dict[str, dict[str, Any]] = {}

    def restore_request(self, record: dict[str, Any]) -> None:
        """Re-register a persisted payment request (e.g. from a prior agent run)."""
        rid = str(record.get("id") or record.get("payment_request_id") or "")
        oid = str(record.get("order_id") or "")
        if not rid:
            return
        req = dict(record)
        req.setdefault("id", rid)
        self._requests[rid] = req
        if oid:
            self._by_order[oid] = req

    def create_payment_request(
        self, order_id: str, amount: int, description: str
    ) -> dict[str, Any]:
        if order_id in self._by_order:
            existing = dict(self._by_order[order_id])
            existing["reused"] = True
            return existing
        rid = f"mock-req-{order_id}"
        req = {
            "id": rid,
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "status": "PENDING",
            "reused": False,
        }
        self._by_order[order_id] = req
        self._requests[rid] = req
        return req

    def check_payment_status(self, request_id: str) -> dict[str, Any]:
        r = self._requests.get(request_id, {"status": "UNKNOWN"})
        if r.get("status") == "PENDING":
            r["status"] = "COMPLETED"
        return {"request_id": request_id, **r}

    def list_transactions(self) -> list[dict[str, Any]]:
        return []

    def simulate_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"received": True, "mode": "mock", "echo_keys": list(payload.keys())}
