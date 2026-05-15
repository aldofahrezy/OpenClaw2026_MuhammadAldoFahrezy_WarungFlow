"""Backward-compatible shim — WhatsApp UI lives on halaman Simulasi."""

from __future__ import annotations

from config import RuntimeConfig
from dashboard_simulator import render_simulator_page


def render_whatsapp_bot_page() -> None:
    """Deprecated: use halaman Simulasi."""
    cfg = RuntimeConfig.load()
    prod = __import__("os").getenv("WARUNGFLOW_ENV", "").strip().lower() in {
        "production",
        "prod",
    }
    render_simulator_page(cfg, prod)
