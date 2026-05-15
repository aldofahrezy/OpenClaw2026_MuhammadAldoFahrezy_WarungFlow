"""DOKU Checkout (Jokul) request signature — non-SNAP header style."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any


def minify_json_body(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def build_digest(request_body: str) -> str:
    raw = hashlib.sha256(request_body.encode("utf-8")).digest()
    return base64.b64encode(raw).decode("ascii")


def build_checkout_signature(
    *,
    client_id: str,
    secret_key: str,
    request_id: str,
    request_timestamp: str,
    request_target: str,
    request_body: str,
) -> str:
    """
    Signature for POST /checkout/v1/payment per DOKU docs.

    Components joined with newlines, then HMAC-SHA256 with secret, base64, prefixed.
    """
    digest = build_digest(request_body)
    components = (
        f"Client-Id:{client_id}\n"
        f"Request-Id:{request_id}\n"
        f"Request-Timestamp:{request_timestamp}\n"
        f"Request-Target:{request_target}\n"
        f"Digest:{digest}"
    )
    mac = hmac.new(
        secret_key.encode("utf-8"),
        components.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"HMACSHA256={base64.b64encode(mac).decode('ascii')}"


def build_get_signature(
    *,
    client_id: str,
    secret_key: str,
    request_id: str,
    request_timestamp: str,
    request_target: str,
) -> str:
    """Signature for GET requests (no Digest component)."""
    components = (
        f"Client-Id:{client_id}\n"
        f"Request-Id:{request_id}\n"
        f"Request-Timestamp:{request_timestamp}\n"
        f"Request-Target:{request_target}"
    )
    mac = hmac.new(
        secret_key.encode("utf-8"),
        components.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"HMACSHA256={base64.b64encode(mac).decode('ascii')}"
