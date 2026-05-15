"""FastAPI WhatsApp webhook + mock payment simulator for WarungFlow."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from tools import event_store
from tools.bot_service import process_inbound_message, simulate_mock_payment

app = FastAPI(title="WarungFlow Bot", version="1.0")


class SimulateMessageBody(BaseModel):
    from_phone: str = "+628123456789"
    customer_name: str = "Kevin"
    message_text: str = "nasi goreng 2 es teh 1"


class MockPayBody(BaseModel):
    order_id: str
    amount: int | None = None
    payer_name: str | None = None
    payment_method: str = "QRIS"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "warungflow-bot"}


@app.get("/whatsapp/webhook")
def whatsapp_verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Any:
    token = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "").strip()
    if hub_mode == "subscribe" and hub_verify_token == token and hub_challenge:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="verification failed")


def _verify_signature(body: bytes, signature: str | None) -> bool:
    secret = (os.getenv("WHATSAPP_APP_SECRET") or "").strip()
    if not secret:
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, str]:
    body = await request.body()
    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = await request.json()
    entries = payload.get("entry") or []
    for entry in entries:
        for change in entry.get("changes") or []:
            val = change.get("value") or {}
            for msg in val.get("messages") or []:
                if msg.get("type") != "text":
                    continue
                text = (msg.get("text") or {}).get("body", "")
                from_phone = msg.get("from", "")
                mid = msg.get("id", "")
                profile = (val.get("contacts") or [{}])[0]
                name = (profile.get("profile") or {}).get("name")
                process_inbound_message(
                    from_phone=f"+{from_phone}" if from_phone and not str(from_phone).startswith("+") else from_phone,
                    message_text=text,
                    customer_name=name,
                    message_id=mid,
                    source="whatsapp_cloud",
                )
    return {"status": "ok"}


@app.post("/simulate/whatsapp-message")
def simulate_whatsapp_message(body: SimulateMessageBody) -> dict[str, Any]:
    return process_inbound_message(
        from_phone=body.from_phone,
        message_text=body.message_text,
        customer_name=body.customer_name,
        source="simulator",
    )


@app.post("/mock-payment/pay")
def mock_payment_pay(body: MockPayBody) -> dict[str, Any]:
    return simulate_mock_payment(
        order_id=body.order_id,
        amount=body.amount,
        payer_name=body.payer_name,
        payment_method=body.payment_method,
    )


@app.get("/mock-payment/pay")
def mock_payment_pay_get(
    order_id: str = Query(...),
    amount: int | None = Query(None),
    payer_name: str | None = Query(None),
) -> dict[str, Any]:
    return simulate_mock_payment(
        order_id=order_id,
        amount=amount,
        payer_name=payer_name,
    )


@app.post("/mock-payment/webhook")
def mock_payment_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    oid = str(payload.get("order_id") or "")
    if not oid:
        raise HTTPException(status_code=400, detail="order_id required")
    return simulate_mock_payment(
        order_id=oid,
        amount=payload.get("amount"),
        payer_name=payload.get("payer_name"),
        payment_method=str(payload.get("payment_method") or "QRIS"),
    )


@app.get("/events")
def list_recent_events(limit: int = 100) -> dict[str, Any]:
    return {
        "events": event_store.list_events(limit),
        "orders": event_store.get_recent_bot_orders(limit),
        "payments": event_store.get_recent_payments(limit),
        "inbound": event_store.get_unprocessed_inbound_messages(),
    }
