"""Build customer-facing payment URLs (mock vs DOKU sandbox simulator)."""

from __future__ import annotations

import os
from typing import Any

from config import has_doku_credentials, resolve_payment_mode
from tools.public_url import doku_checkout_page_url, mock_payment_page_url


def build_bot_payment_links(
    *,
    order_id: str,
    amount: int,
    description: str,
    payment_mode_choice: str,
    customer_name: str | None = None,
    customer_phone: str | None = None,
) -> dict[str, Any]:
    """
    Return payment_request dict for bot orders.

    mock → Streamlit ?mock_pay=
    doku_sandbox → DOKU hosted URL (if API ok) + WarungFlow simulator page (?doku_pay=)
    """
    mode = resolve_payment_mode(payment_mode_choice)
    if mode == "doku_sandbox" and has_doku_credentials():
        from tools.doku_sandbox_provider import DokuSandboxProvider

        prov = DokuSandboxProvider(
            (os.getenv("DOKU_CLIENT_ID") or "").strip(),
            (os.getenv("DOKU_SECRET_KEY") or "").strip(),
            (os.getenv("DOKU_SANDBOX_BASE_URL") or "").strip() or None,
        )
        pr = prov.create_payment_request(
            order_id,
            amount,
            description,
            customer_name=customer_name,
            customer_phone=customer_phone,
        )
        pr.setdefault("payment_mode", "doku_sandbox")
        return pr

    url = mock_payment_page_url(order_id)
    return {
        "id": f"mock-pay-{order_id}",
        "order_id": order_id,
        "amount": amount,
        "status": "PENDING",
        "payment_url": url,
        "hosted_checkout_url": None,
        "provider": "mock",
        "payment_mode": "mock",
    }


def format_payment_message_lines(
    pay_req: dict[str, Any], *, payment_mode_choice: str
) -> list[str]:
    """WhatsApp lines for how to pay."""
    mode = resolve_payment_mode(payment_mode_choice)
    primary = str(pay_req.get("payment_url") or "")
    hosted = str(pay_req.get("hosted_checkout_url") or "").strip()

    if mode == "doku_sandbox":
        lines = [
            "\n*Bayar pesanan (DOKU Sandbox)*",
            f"1. Buka simulator pembayaran (seperti Midtrans Sandbox):\n{primary}",
        ]
        if hosted and hosted != primary:
            lines.append(
                f"\n2. Atau checkout resmi DOKU Sandbox:\n{hosted}"
            )
        lines.append(
            "\nSetelah bayar di halaman DOKU, kembali ke simulator dan klik "
            "*Cek status pembayaran DOKU* (atau *Bayar berhasil* untuk uji cepat)."
        )
        return lines

    return [f"\nSilakan bayar lewat mock payment:\n{primary}"]
