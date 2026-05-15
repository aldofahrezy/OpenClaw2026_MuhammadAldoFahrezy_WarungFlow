"""WhatsApp bot order intake — intent, catalogue pricing, mock payments."""

from __future__ import annotations

import os
import re
import uuid
from typing import Any

from tools import event_store
from tools.catalogue_tools import (
    calculate_order_total_from_catalogue,
    extract_order_items,
    load_product_catalogue_from_csv,
    normalize_catalogue_tool,
)
from tools.whatsapp_provider import get_whatsapp_provider

ITEM_QTY_RE = re.compile(
    r"([a-z0-9\s]+?)\s+(\d+)\b",
    re.IGNORECASE,
)


def classify_intent(text: str) -> str:
    tl = text.lower().strip()
    if re.search(r"\b(menu|daftar|catalog|katalog)\b", tl):
        return "MENU"
    if re.search(r"\b(status|cek\s*pesanan|order\s*id)\b", tl) or re.search(
        r"ORD-BOT-\d+", text, re.I
    ):
        return "STATUS"
    if re.search(r"\b(help|bantuan|info)\b", tl):
        return "HELP"
    if _looks_like_order(tl):
        return "ORDER"
    return "UNKNOWN"


def _looks_like_order(text: str) -> bool:
    if ITEM_QTY_RE.search(text):
        return True
    catalogue = load_product_catalogue_from_csv()
    idx: set[str] = set()
    for row in catalogue:
        if not row.get("is_active", True):
            continue
        for a in row.get("aliases") or []:
            idx.add(a.lower())
    return any(a in text for a in idx if len(a) > 2)


def build_menu_text(catalogue: list[dict[str, Any]]) -> str:
    lines = ["*Menu Warung Bu Sari* (harga per unit):"]
    for row in [r for r in catalogue if r.get("is_active", True)]:
        lines.append(
            f"- {row['product_name']}: Rp {int(row['unit_price']):,} / {row.get('unit', 'porsi')}"
        )
    lines.append("\nContoh pesan: nasi goreng 2 es teh 1")
    return "\n".join(lines)


def process_inbound_message(
    *,
    from_phone: str,
    message_text: str,
    customer_name: str | None = None,
    message_id: str | None = None,
    source: str = "simulator",
    catalogue: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full bot pipeline for one inbound message."""
    mid = message_id or f"sim-{uuid.uuid4().hex[:12]}"
    stored = event_store.append_inbound_message(
        message_id=mid,
        from_phone=from_phone,
        text=message_text,
        customer_name=customer_name,
        source=source,
    )
    if stored is None:
        return {"status": "duplicate", "message_id": mid}

    catalogue = normalize_catalogue_tool(catalogue or load_product_catalogue_from_csv())
    intent = classify_intent(message_text)
    provider = get_whatsapp_provider()
    base_url = (os.getenv("PUBLIC_BASE_URL") or os.getenv("BOT_SERVER_URL") or "http://localhost:8000").rstrip("/")
    name = customer_name or "Pelanggan"

    if intent == "MENU":
        reply = build_menu_text(catalogue)
        provider.send_text(from_phone, reply)
        event_store.mark_message_processed(mid)
        return {"status": "ok", "intent": "MENU", "message_id": mid}

    if intent == "HELP":
        reply = (
            "Halo! Kirim pesanan dengan format:\n"
            "nasi goreng 2, es teh 1\n\n"
            "Ketik *menu* untuk daftar harga.\n"
            "Ketik *status ORD-BOT-0001* untuk cek pembayaran."
        )
        provider.send_text(from_phone, reply)
        event_store.mark_message_processed(mid)
        return {"status": "ok", "intent": "HELP", "message_id": mid}

    if intent == "STATUS":
        m = re.search(r"(ORD-BOT-\d+)", message_text, re.I)
        oid = m.group(1).upper() if m else ""
        order = event_store.get_bot_order(oid) if oid else None
        if not order:
            reply = "Order tidak ditemukan. Kirim ID seperti ORD-BOT-0001."
        else:
            reply = (
                f"Order {order['order_id']}: {order.get('payment_status', 'AWAITING_PAYMENT')}\n"
                f"Total: Rp {int(order.get('amount_expected') or 0):,}"
            )
        provider.send_text(from_phone, reply)
        event_store.mark_message_processed(mid)
        return {"status": "ok", "intent": "STATUS", "message_id": mid}

    if intent == "ORDER":
        items = extract_order_items(message_text, catalogue)
        calc = calculate_order_total_from_catalogue(items, catalogue)
        unknown = calc.get("unknown_products") or []
        catalogue_total = calc.get("catalogue_total")

        explicit_m = re.search(
            r"total\s*(?:rp\.?|idr)?\s*([\d\.\,]+)", message_text, re.I
        )
        explicit_total = None
        if explicit_m:
            explicit_total = int(
                explicit_m.group(1).replace(".", "").replace(",", "")
            )

        amount_expected = explicit_total if explicit_total is not None else catalogue_total
        discrepancy = bool(
            explicit_total is not None
            and catalogue_total is not None
            and explicit_total != catalogue_total
        )
        parser_status = "NEEDS_REVIEW" if unknown or amount_expected is None else "READY_FOR_RECONCILIATION"
        if discrepancy:
            parser_status = "NEEDS_REVIEW"

        order_id = event_store.next_bot_order_id()
        pay_id = f"mock-pay-{order_id}"
        pay_url = f"{base_url}/mock-payment/pay?order_id={order_id}"

        lines = [f"Halo {name}! Pesanan kamu:"]
        for it in calc.get("items") or []:
            if it.get("status") == "MATCHED":
                lines.append(
                    f"- {it.get('product_name')} x{it.get('quantity')} = Rp {int(it.get('line_total') or 0):,}"
                )
            else:
                lines.append(f"- {it.get('raw_text')} (produk tidak dikenal)")
        if unknown:
            lines.append(f"\n⚠ Produk tidak di katalog: {', '.join(unknown)}")
        lines.append(f"\nTotal: Rp {int(amount_expected or 0):,}")
        lines.append(f"Order ID: {order_id}")
        lines.append(f"\nSilakan bayar lewat mock payment:\n{pay_url}")
        lines.append("\nSetelah pembayaran masuk, WarungFlow akan otomatis update status. Terima kasih 🙏")
        reply = "\n".join(lines)

        raw_line = f"{message_text.strip()} - {name}"
        order_rec = {
            "order_id": order_id,
            "customer_name": name,
            "customer_phone": from_phone,
            "raw_message": message_text,
            "raw_whatsapp_line": raw_line,
            "items": calc.get("items"),
            "amount_expected": amount_expected,
            "catalogue_total": catalogue_total,
            "explicit_total": explicit_total,
            "amount_source": "explicit_total" if explicit_total else "catalogue",
            "unknown_products": unknown,
            "discrepancy": discrepancy,
            "parser_status": parser_status,
            "payment_status": "AWAITING_PAYMENT",
            "payment_request": {
                "payment_request_id": pay_id,
                "order_id": order_id,
                "amount": amount_expected,
                "customer_name": name,
                "customer_phone": from_phone,
                "status": "PENDING",
                "payment_url": pay_url,
            },
        }
        event_store.append_bot_order(order_rec)
        provider.send_text(from_phone, reply, order_id=order_id)
        event_store.mark_message_processed(mid)
        return {
            "status": "ok",
            "intent": "ORDER",
            "message_id": mid,
            "order": order_rec,
            "auto_refresh": True,
        }

    reply = (
        "Maaf, format belum dikenali. Coba:\n"
        "nasi goreng 2, es teh 1\n\n"
        "Atau ketik *menu* untuk daftar harga."
    )
    provider.send_text(from_phone, reply)
    event_store.mark_message_processed(mid)
    return {"status": "ok", "intent": "UNKNOWN", "message_id": mid}


def simulate_mock_payment(
    *,
    order_id: str,
    amount: int | None = None,
    payer_name: str | None = None,
    payment_method: str = "QRIS",
) -> dict[str, Any]:
    order = event_store.get_bot_order(order_id)
    if not order:
        return {"status": "error", "detail": "order_not_found"}

    amt = amount if amount is not None else int(order.get("amount_expected") or 0)
    payer = payer_name or order.get("customer_name") or "Customer"
    expected = int(order.get("amount_expected") or 0)
    event_id = f"wh-{order_id}-{amt}-{payer}"

    existing = {e.get("event_id") for e in event_store.get_recent_payments(500)}
    if event_id in existing:
        return {"status": "idempotent_skip", "event_id": event_id}

    txn = {
        "transaction_id": f"bot-{event_id}",
        "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "payer_name": payer,
        "amount": str(amt),
        "payment_method": payment_method,
        "reference_note": f"DOKU webhook {order_id} {payer} bot payment",
    }

    if amt >= expected and expected > 0:
        pay_status = "PAID"
    elif amt > 0:
        pay_status = "PARTIALLY_PAID"
    else:
        pay_status = "PENDING"

    event_store.append_payment_event(
        {
            "event_id": event_id,
            "order_id": order_id,
            "amount": amt,
            "payer_name": payer,
            "payment_method": payment_method,
            "transaction": txn,
            "payment_status": pay_status,
        }
    )

    pr = order.get("payment_request") or {}
    pr["status"] = pay_status
    event_store.update_bot_order(
        order_id,
        {"payment_status": pay_status, "payment_request": pr, "matched_amount": amt},
    )

    phone = order.get("customer_phone") or ""
    if phone:
        get_whatsapp_provider().send_text(
            phone,
            f"Pembayaran untuk Order {order_id} sebesar Rp {amt:,} sudah diterima ({pay_status}). Terima kasih 🙏",
            order_id=order_id,
        )

    return {
        "status": "ok",
        "event_id": event_id,
        "payment_status": pay_status,
        "transaction": txn,
        "auto_refresh": True,
    }


def merge_bot_into_agent_inputs(
    raw_orders: list[str] | None,
    payment_transactions: list[dict[str, Any]] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Merge bot orders/payments into session lists for the autonomous loop."""
    orders_out = list(raw_orders or [])
    txns_out = [dict(t) for t in (payment_transactions or [])]
    seen_lines = set(orders_out)
    seen_txn = {t.get("transaction_id") for t in txns_out}

    for bo in event_store.get_recent_bot_orders(200):
        line = bo.get("raw_whatsapp_line") or bo.get("raw_message", "")
        if line and line not in seen_lines:
            orders_out.append(line)
            seen_lines.add(line)

    for pe in event_store.get_recent_payments(200):
        txn = pe.get("transaction")
        if isinstance(txn, dict):
            tid = txn.get("transaction_id")
            if tid and tid not in seen_txn:
                txns_out.append(dict(txn))
                seen_txn.add(tid)
    return orders_out, txns_out
