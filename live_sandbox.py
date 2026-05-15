"""Live Data Sandbox helpers — add orders/payments/expenses with idempotency."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from session_runtime import mark_data_changed, save_ui_session_snapshot
from tools import event_store

EXPENSE_CATEGORIES = (
    "bahan_baku",
    "gas",
    "listrik",
    "packaging",
    "transport",
    "other",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _order_fingerprint(message: str) -> str:
    return hashlib.sha256(message.strip().lower().encode()).hexdigest()[:16]


def append_whatsapp_order(message: str) -> bool:
    msg = message.strip()
    if not msg:
        return False
    fp = _order_fingerprint(msg)
    seen = st.session_state.setdefault("_order_fingerprints", set())
    if fp in seen:
        return False
    seen.add(fp)
    orders = list(st.session_state.raw_orders or [])
    meta = f"<!-- id:{fp} created:{_now_iso()} -->"
    orders.append(f"{msg} {meta}" if "<!--" not in msg else msg)
    st.session_state.raw_orders = orders
    mark_data_changed("new_whatsapp_order")
    return True


def _payment_fingerprint(payer: str, amount: int, ref: str, ts: str) -> str:
    raw = f"{payer}|{amount}|{ref}|{ts}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def link_manual_payment_to_bot_order(
    payer_name: str,
    amount: int,
    reference_note: str,
) -> str | None:
    """
    When a manual QRIS row matches a bot order, update runtime bot order status
    so Simulasi / chat reflect PAID without requiring mock-pay link only.
    """
    oid: str | None = None
    m = re.search(r"(ORD-BOT-\d+)", reference_note or "", re.I)
    if m:
        oid = m.group(1).upper()

    payer_l = payer_name.strip().lower()
    if not oid:
        for o in event_store.get_recent_bot_orders(100):
            status = str(o.get("payment_status") or "").upper()
            if status not in {"AWAITING_PAYMENT", "PENDING", ""}:
                continue
            if str(o.get("customer_name") or "").strip().lower() != payer_l:
                continue
            expected = int(o.get("amount_expected") or 0)
            if expected > 0 and amount == expected:
                oid = str(o.get("order_id") or "")
                break

    if not oid:
        return None

    order = event_store.get_bot_order(oid)
    if not order:
        return None

    expected = int(order.get("amount_expected") or 0)
    if expected > 0 and amount >= expected:
        pay_status = "PAID"
    elif amount > 0:
        pay_status = "PARTIALLY_PAID"
    else:
        return oid

    pr = dict(order.get("payment_request") or {})
    pr["status"] = pay_status
    event_store.update_bot_order(
        oid,
        {
            "payment_status": pay_status,
            "matched_amount": amount,
            "payment_request": pr,
        },
    )

    phone = str(order.get("customer_phone") or "").strip()
    if phone and pay_status == "PAID":
        from tools.whatsapp_provider import get_whatsapp_provider

        get_whatsapp_provider().send_text(
            phone,
            f"Pembayaran untuk Order {oid} sebesar Rp {amount:,} sudah diterima "
            f"({pay_status}). Terima kasih 🙏",
            order_id=oid,
        )
    return oid


def append_payment_transaction(
    payer_name: str,
    amount: int,
    payment_method: str,
    reference_note: str,
    timestamp: str | None = None,
) -> bool:
    ts = timestamp or _now_iso()
    ref = reference_note.strip()
    payer = payer_name.strip()
    fp = _payment_fingerprint(payer, amount, ref, ts)
    seen = st.session_state.setdefault("_payment_fingerprints", set())
    if fp in seen:
        return False
    seen.add(fp)
    txns = list(st.session_state.payment_transactions or [])
    txns.append(
        {
            "transaction_id": f"p-{fp}",
            "timestamp": ts,
            "payer_name": payer,
            "amount": str(amount),
            "payment_method": payment_method,
            "reference_note": ref,
        }
    )
    st.session_state.payment_transactions = txns
    linked_oid = link_manual_payment_to_bot_order(payer, amount, ref)
    mark_data_changed("new_payment_transaction")
    save_ui_session_snapshot()
    if linked_oid:
        st.session_state._last_linked_bot_order = linked_oid
    return True


def append_expense(category: str, description: str, amount: int, date: str) -> bool:
    fp = hashlib.sha256(f"{category}|{description}|{amount}|{date}".encode()).hexdigest()[
        :16
    ]
    seen = st.session_state.setdefault("_expense_fingerprints", set())
    if fp in seen:
        return False
    seen.add(fp)
    rows = list(st.session_state.expenses or [])
    rows.append(
        {
            "date": date,
            "category": category,
            "description": description,
            "amount": str(amount),
        }
    )
    st.session_state.expenses = rows
    mark_data_changed("new_expense")
    return True


def add_unpaid_order_demo() -> None:
    append_whatsapp_order(
        "Mbak, nasi goreng 2 total 44000, bayar nanti malam - Kevin"
    )


def add_expense_shock_demo() -> bool:
    return append_expense(
        category="bahan_baku",
        description="Kenaikan harga bahan baku",
        amount=125_000,
        date=datetime.now(timezone.utc).date().isoformat(),
    )


def add_matching_payment_demo() -> None:
    append_payment_transaction(
        payer_name="Kevin",
        amount=44000,
        payment_method="QRIS",
        reference_note="nasi goreng Kevin",
    )


def add_partial_payment_demo() -> None:
    agent = st.session_state.get("agent_state")
    target_amt = 25000
    payer = "Partial Demo"
    ref = "partial payment demo"
    if agent and agent.parsed_orders:
        for o in reversed(agent.parsed_orders):
            if o.get("customer_name"):
                payer = str(o["customer_name"])
                exp = o.get("amount_expected")
                if isinstance(exp, int) and exp > 5000:
                    target_amt = max(5000, exp // 2)
                    ref = f"partial {o.get('order_id')} {payer}"
                break
    append_payment_transaction(
        payer_name=payer,
        amount=target_amt,
        payment_method="transfer",
        reference_note=ref,
    )


def simulate_doku_payment_success() -> str:
    """Idempotent mock webhook: add completed payment for latest unpaid order."""
    agent = st.session_state.get("agent_state")
    if not agent or not agent.reconciliation_results:
        return "no_agent_state"

    unpaid = [
        r
        for r in agent.reconciliation_results
        if r.get("status") in {"UNPAID", "PARTIALLY_PAID"}
    ]
    if not unpaid:
        return "no_unpaid_orders"

    target = unpaid[0]
    oid = str(target.get("order_id"))
    order = next(
        (o for o in (agent.parsed_orders or []) if str(o.get("order_id")) == oid),
        None,
    )
    amt = int(order.get("amount_expected") or 0) if order else 0
    remaining = max(0, amt - int(target.get("matched_amount") or 0))
    if remaining <= 0 and amt > 0:
        remaining = amt
    if remaining <= 0:
        remaining = 44000

    cust = (order or {}).get("customer_name") or "Customer"
    event_id = f"wh-{oid}-{remaining}"
    seen: set[str] = st.session_state.webhook_events_seen
    if event_id in seen:
        mark_data_changed("webhook_replay_idempotent")
        return f"idempotent_skip:{event_id}"
    seen.add(event_id)

    append_payment_transaction(
        payer_name=str(cust),
        amount=remaining,
        payment_method="QRIS",
        reference_note=f"DOKU webhook {oid} {cust}",
    )
    return f"webhook_applied:{event_id}"
