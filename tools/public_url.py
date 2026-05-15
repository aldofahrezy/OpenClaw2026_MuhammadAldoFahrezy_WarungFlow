"""Resolve public URLs for mock payment links (Streamlit deploy vs local bot server)."""

from __future__ import annotations

import os
import re
from urllib.parse import quote, urlparse

# Default live demo (VPS Streamlit) — used when not running on developer laptop.
_LIVE_DEFAULT = "http://43.157.208.68:8501"

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", ""})


def _is_loopback(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in _LOOPBACK_HOSTS


def resolve_public_base_url() -> str:
    """
    Base URL customers/judges can open in a browser.

    Loopback values in env are ignored so a stale .env cannot break production.
    """
    for key in ("WARUNGFLOW_LIVE_URL", "PUBLIC_BASE_URL", "WARUNGFLOW_PUBLIC_URL"):
        raw = (os.getenv(key) or "").strip()
        if raw and not _is_loopback(raw):
            return raw.rstrip("/")

    env = (os.getenv("WARUNGFLOW_ENV") or "").strip().lower()
    if env in {"production", "prod"}:
        return _LIVE_DEFAULT

    bot = (os.getenv("BOT_SERVER_URL") or "").strip()
    if bot and not _is_loopback(bot):
        return bot.rstrip("/")

    # Streamlit on VPS (--server.address=0.0.0.0) should not emit localhost links.
    bind = (os.getenv("STREAMLIT_SERVER_ADDRESS") or "").strip()
    headless = (os.getenv("STREAMLIT_SERVER_HEADLESS") or "").strip().lower()
    if bind in {"0.0.0.0", "::"} or headless == "true":
        return _LIVE_DEFAULT

    port = (os.getenv("STREAMLIT_SERVER_PORT") or "8501").strip()
    return f"http://localhost:{port}".rstrip("/")


def uses_streamlit_mock_pay(base: str | None = None) -> bool:
    """True when mock pay is handled via ?mock_pay= on the Streamlit app."""
    base = (base or resolve_public_base_url()).rstrip("/")
    if ":8501" in base and not _is_loopback(base):
        return True
    if os.getenv("MOCK_PAY_VIA_STREAMLIT", "").strip().lower() in {"1", "true", "yes"}:
        return True
    env = (os.getenv("WARUNGFLOW_ENV") or "").strip().lower()
    if env in {"production", "prod"}:
        return True
    bot = (os.getenv("BOT_SERVER_URL") or "").strip()
    if not bot or _is_loopback(bot):
        return True
    return False


def mock_payment_page_url(order_id: str) -> str:
    """Browser-openable URL to simulate paying a bot order."""
    oid = quote(str(order_id).strip(), safe="")
    base = resolve_public_base_url()
    if uses_streamlit_mock_pay(base):
        return f"{base}/?mock_pay={oid}"
    return f"{base}/mock-payment/pay?order_id={oid}"


def doku_checkout_page_url(order_id: str) -> str:
    """WarungFlow DOKU sandbox simulator page (Midtrans-style test UI)."""
    oid = quote(str(order_id).strip(), safe="")
    return f"{resolve_public_base_url()}/?doku_pay={oid}"


def doku_return_url(order_id: str) -> str:
    """Callback after customer pays on hosted DOKU checkout."""
    oid = quote(str(order_id).strip(), safe="")
    return f"{resolve_public_base_url()}/?doku_return={oid}"


def rewrite_localhost_urls(text: str) -> str:
    """Replace localhost payment links in stored bot messages when displaying."""
    if not text or "localhost" not in text:
        return text
    base = resolve_public_base_url()
    return re.sub(
        r"https?://localhost(?::\d+)?",
        base,
        text,
        flags=re.IGNORECASE,
    )
