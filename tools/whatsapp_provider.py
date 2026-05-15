"""WhatsApp provider abstraction — mock default, Cloud API optional."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from tools import event_store

logger = logging.getLogger(__name__)


class WhatsAppProvider:
    def send_text(self, to_phone: str, text: str, *, order_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def mark_typing(self, to_phone: str) -> dict[str, Any] | None:
        return None


class MockWhatsAppProvider(WhatsAppProvider):
  def send_text(self, to_phone: str, text: str, *, order_id: str | None = None) -> dict[str, Any]:
        rec = event_store.append_outbound_message(to_phone, text, order_id=order_id)
        return {"mode": "mock", "status": "queued", "outbox": rec}


class WhatsAppCloudProvider(WhatsAppProvider):
    def __init__(self) -> None:
        self.token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
        self.phone_id = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        ver = (os.getenv("WHATSAPP_API_VERSION") or "v21.0").strip()
        base = (os.getenv("WHATSAPP_GRAPH_BASE_URL") or "https://graph.facebook.com").rstrip("/")
        self.url = f"{base}/{ver}/{self.phone_id}/messages"

    def send_text(self, to_phone: str, text: str, *, order_id: str | None = None) -> dict[str, Any]:
        if not self.token or not self.phone_id:
            return MockWhatsAppProvider().send_text(to_phone, text, order_id=order_id)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone.lstrip("+"),
            "type": "text",
            "text": {"body": text[:4096]},
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
            event_store.append_outbound_message(to_phone, text, order_id=order_id)
            return {"mode": "cloud", "status": "sent", "response": body}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning("WhatsApp Cloud send failed: %s", type(e).__name__)
            return MockWhatsAppProvider().send_text(to_phone, text, order_id=order_id)


def get_whatsapp_provider() -> WhatsAppProvider:
    mode = (os.getenv("WHATSAPP_MODE") or "mock").strip().lower()
    if mode == "cloud" and (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip():
        return WhatsAppCloudProvider()
    return MockWhatsAppProvider()


def mask_token(value: str | None) -> str:
    if not value or not value.strip():
        return "(not set)"
    v = value.strip()
    if len(v) <= 8:
        return "********"
    return f"{v[:4]}****{v[-4:]}"
