"""DOKU Checkout sandbox — create hosted payment URL + WarungFlow simulator fallback."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from tools.doku_signature import (
    build_checkout_signature,
    build_get_signature,
    minify_json_body,
)
from tools.public_url import doku_checkout_page_url, doku_return_url

logger = logging.getLogger(__name__)

_REQUEST_TARGET = "/checkout/v1/payment"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_invoice(order_id: str) -> str:
    """DOKU invoice_number: alphanumeric + hyphen, max 64."""
    inv = re.sub(r"[^A-Za-z0-9-]", "", str(order_id).strip())[:64]
    return inv or f"INV-{uuid.uuid4().hex[:12]}"


class DokuSandboxProvider:
    """DOKU Checkout sandbox adapter with hosted URL + local simulator page."""

    def __init__(self, client_id: str, secret_key: str, base_url: str | None) -> None:
        self.client_id = client_id
        self.secret_key = secret_key
        self.base_url = (base_url or "https://api-sandbox.doku.com").rstrip("/")

    def create_payment_request(
        self,
        order_id: str,
        amount: int,
        description: str,
        *,
        customer_name: str | None = None,
        customer_phone: str | None = None,
    ) -> dict[str, Any]:
        simulator_url = doku_checkout_page_url(order_id)
        hosted_url: str | None = None
        session_id: str | None = None
        api_error: str | None = None

        if self.client_id and self.secret_key:
            try:
                hosted_url, session_id = self._create_hosted_checkout(
                    order_id=order_id,
                    amount=amount,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                )
            except Exception as exc:  # noqa: BLE001
                api_error = str(exc)
                logger.warning("DOKU checkout API failed: %s", type(exc).__name__)

        invoice = _sanitize_invoice(order_id)
        return {
            "id": f"doku-{order_id}",
            "payment_request_id": f"doku-{order_id}",
            "order_id": order_id,
            "amount": amount,
            "description": description,
            "status": "PENDING",
            "payment_url": simulator_url,
            "hosted_checkout_url": hosted_url,
            "doku_session_id": session_id,
            "doku_invoice_number": invoice,
            "provider": "doku_sandbox",
            "api_error": api_error,
            "reused": False,
        }

    def _create_hosted_checkout(
        self,
        *,
        order_id: str,
        amount: int,
        customer_name: str | None,
        customer_phone: str | None,
    ) -> tuple[str | None, str | None]:
        invoice = _sanitize_invoice(order_id)
        body: dict[str, Any] = {
            "order": {
                "amount": int(amount),
                "invoice_number": invoice,
                "currency": "IDR",
                "callback_url": doku_return_url(order_id),
                "callback_url_result": doku_return_url(order_id),
                "auto_redirect": True,
            },
            "payment": {"payment_due_date": 60},
        }
        phone = re.sub(r"\D", "", str(customer_phone or ""))
        if customer_name or phone:
            body["customer"] = {
                "name": (customer_name or "Customer")[:255],
                "phone": phone[:16] if phone else "628000000000",
            }

        raw_body = minify_json_body(body)
        request_id = str(uuid.uuid4())
        timestamp = _utc_timestamp()
        signature = build_checkout_signature(
            client_id=self.client_id,
            secret_key=self.secret_key,
            request_id=request_id,
            request_timestamp=timestamp,
            request_target=_REQUEST_TARGET,
            request_body=raw_body,
        )

        url = f"{self.base_url}{_REQUEST_TARGET}"
        req = urlrequest.Request(
            url,
            data=raw_body.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Client-Id": self.client_id,
                "Request-Id": request_id,
                "Request-Timestamp": timestamp,
                "Signature": signature,
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        response = payload.get("response") or payload
        payment = response.get("payment") if isinstance(response, dict) else {}
        if not isinstance(payment, dict):
            payment = {}
        hosted = payment.get("url") or payment.get("checkout_url")
        session_id = None
        order_block = response.get("order") if isinstance(response, dict) else {}
        if isinstance(order_block, dict):
            session_id = order_block.get("session_id")
        if not hosted:
            raise ValueError(f"DOKU response missing payment.url: {payload!r:.200}")
        return str(hosted), str(session_id) if session_id else None

    def check_payment_status(self, request_id: str) -> dict[str, Any]:
        """request_id is treated as WarungFlow order_id (ORD-BOT-xxxx)."""
        return self.check_order_payment_status(request_id)

    def check_order_payment_status(self, order_id: str) -> dict[str, Any]:
        """GET /orders/v1/status/{invoice} — poll after customer pays on DOKU checkout."""
        invoice = _sanitize_invoice(order_id)
        request_target = f"/orders/v1/status/{invoice}"
        request_id = str(uuid.uuid4())
        timestamp = _utc_timestamp()
        signature = build_get_signature(
            client_id=self.client_id,
            secret_key=self.secret_key,
            request_id=request_id,
            request_timestamp=timestamp,
            request_target=request_target,
        )
        url = f"{self.base_url}{request_target}"
        req = urlrequest.Request(
            url,
            headers={
                "Client-Id": self.client_id,
                "Request-Id": request_id,
                "Request-Timestamp": timestamp,
                "Signature": signature,
            },
            method="GET",
        )
        with urlrequest.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        txn_status = _extract_transaction_status(payload)
        return {
            "order_id": order_id,
            "invoice_number": invoice,
            "transaction_status": txn_status,
            "raw": payload,
            "status": txn_status or "UNKNOWN",
        }

    def list_transactions(self) -> list[dict[str, Any]]:
        return []

    def simulate_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"received": True, "mode": "doku_sandbox", "keys": list(payload.keys())}


def _extract_transaction_status(payload: dict[str, Any]) -> str:
    """Normalize DOKU check-status / notification payloads."""
    if not isinstance(payload, dict):
        return ""
    txn = payload.get("transaction")
    if isinstance(txn, dict) and txn.get("status"):
        return str(txn["status"]).upper()
    for key in ("latest_transaction_status", "transaction_status", "status"):
        if payload.get(key):
            return str(payload[key]).upper()
    resp = payload.get("response")
    if isinstance(resp, dict):
        inner = _extract_transaction_status(resp)
        if inner:
            return inner
    for block in payload.values():
        if isinstance(block, dict):
            inner = _extract_transaction_status(block)
            if inner:
                return inner
    return ""
