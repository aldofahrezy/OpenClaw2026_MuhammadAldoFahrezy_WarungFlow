from __future__ import annotations

import logging
import uuid
from typing import Any

from .payment_adapter import PaymentProvider

logger = logging.getLogger(__name__)


class MockPaymentProvider(PaymentProvider):
    def __init__(self) -> None:
        self._requests: dict[str, dict[str, Any]] = {}

    def create_payment_request(
        self, order_id: str, amount: int, description: str
    ) -> dict[str, Any]:
        rid = f"mock-req-{uuid.uuid4().hex[:10]}"
        self._requests[rid] = {
            "id": rid,
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "status": "PENDING",
        }
        return self._requests[rid]

    def check_payment_status(self, request_id: str) -> dict[str, Any]:
        r = self._requests.get(request_id, {"status": "UNKNOWN"})
        if r.get("status") == "PENDING":
            r["status"] = "COMPLETED"
        return {"request_id": request_id, **r}

    def list_transactions(self) -> list[dict[str, Any]]:
        return []

    def simulate_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"received": True, "mode": "mock", "echo_keys": list(payload.keys())}
