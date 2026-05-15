from __future__ import annotations

import logging
from typing import Any

from .base import PaymentProvider

logger = logging.getLogger(__name__)


class DokuSandboxProvider(PaymentProvider):
    """
    DOKU sandbox adapter. Real signing and endpoints vary; failures should trigger mock fallback.
    """

    def __init__(self, client_id: str, secret_key: str, base_url: str | None) -> None:
        self.client_id = client_id
        self.secret_key = secret_key
        self.base_url = (base_url or "https://api-sandbox.doku.com").rstrip("/")

    def create_payment_request(
        self, order_id: str, amount: int, description: str
    ) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        url = f"{self.base_url}/checkout/v1/payment"
        body = str(
            {"order": {"invoice_number": order_id, "amount": amount, "line_items": []}}
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Client-Id": self.client_id[:3] + "****",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                _ = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning("DOKU create_payment_request failed: %s", type(e).__name__)
            raise
        return {"id": "doku-placeholder", "status": "PENDING", "order_id": order_id}

    def check_payment_status(self, request_id: str) -> dict[str, Any]:
        return {"request_id": request_id, "status": "UNKNOWN"}

    def list_transactions(self) -> list[dict[str, Any]]:
        return []

    def simulate_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"received": True, "mode": "doku_sandbox", "keys": list(payload.keys())}
