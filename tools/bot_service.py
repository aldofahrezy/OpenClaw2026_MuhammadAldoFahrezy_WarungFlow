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
from tools.parsers import _extract_customer_and_payer
from tools.payment_links import build_bot_payment_links, format_payment_message_lines
from tools.whatsapp_provider import get_whatsapp_provider

GENERIC_CUSTOMER_NAMES = frozenset(
    {"pelanggan", "customer", "guest", "tamu", "anon", "anonymous"}
)

CONFIRM_YES_RE = re.compile(
    r"^(ya|yes|ok|oke|okay|benar|betul|setuju|konfirmasi|sip|gas|yoi|mantap)\b",
    re.I,
)
CONFIRM_NO_RE = re.compile(
    r"^(batal|tidak|nggak|gak|no|salah|ulang|cancel)\b",
    re.I,
)

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


def _is_generic_name(name: str | None) -> bool:
    if not name or not str(name).strip():
        return True
    return str(name).strip().lower() in GENERIC_CUSTOMER_NAMES


def _resolve_customer_name(message_text: str, form_name: str | None) -> str | None:
    from_msg, _, _ = _extract_customer_and_payer(message_text)
    if from_msg and not _is_generic_name(from_msg):
        return from_msg.strip()
    if form_name and not _is_generic_name(form_name):
        return form_name.strip()
    return None


def _parse_name_only_reply(text: str) -> str | None:
    t = text.strip()
    if not t or len(t) > 40:
        return None
    if CONFIRM_YES_RE.match(t) or CONFIRM_NO_RE.match(t):
        return None
    if re.search(r"\d{2,}", t):
        return None
    if _looks_like_order(t.lower()):
        return None
    m = re.match(r"^(?:nama|name)\s*[:\-]?\s*(.+)$", t, re.I)
    if m:
        return m.group(1).strip()
    if re.match(r"^[\w\s.'-]{2,30}$", t, re.UNICODE):
        return t.strip()
    return None


def _analyze_order_gaps(
    *,
    message_text: str,
    customer_name: str | None,
    calc: dict[str, Any],
    unknown: list[str],
    amount_expected: int | None,
) -> list[str]:
    gaps: list[str] = []
    if not (calc.get("items") or []):
        gaps.append("belum ada item pesanan yang dikenali (contoh: nasi goreng 2)")
    elif not any(it.get("status") == "MATCHED" for it in (calc.get("items") or [])):
        gaps.append("produk belum cocok dengan katalog — cek ejaan atau ketik *menu*")
    if unknown:
        gaps.append(f"produk tidak ada di katalog: {', '.join(unknown)}")
    if amount_expected is None or amount_expected <= 0:
        gaps.append("total pesanan belum bisa dihitung")
    if not customer_name:
        gaps.append("nama pelanggan belum jelas (tambahkan di akhir pesan, contoh: - Kevin)")
    return gaps


def _build_confirm_reply(
    *,
    customer_name: str | None,
    calc: dict[str, Any],
    unknown: list[str],
    amount_expected: int | None,
    gaps: list[str],
) -> str:
    lines = ["Mohon konfirmasi pesanan Anda:\n"]
    matched = False
    for it in calc.get("items") or []:
        if it.get("status") == "MATCHED":
            matched = True
            lines.append(
                f"• {it.get('product_name')} x{it.get('quantity')} = "
                f"Rp {int(it.get('line_total') or 0):,}"
            )
        else:
            lines.append(f"• {it.get('raw_text')} (belum dikenali)")
    if not matched:
        lines.append("• (belum ada item dikenali)")
    lines.append(f"\n*Total sementara:* Rp {int(amount_expected or 0):,}")
    if customer_name:
        lines.append(f"*Nama:* {customer_name}")
    if gaps:
        lines.append("\n⚠ Perlu dilengkapi:")
        for g in gaps:
            lines.append(f"• {g}")
    lines.append(
        "\nJika sudah benar, balas *ya* untuk memproses pesanan.\n"
        "Jika ada yang salah, balas *batal* atau kirim pesanan lengkap lagi."
    )
    return "\n".join(lines)


def _finalize_bot_order(
    *,
    from_phone: str,
    message_text: str,
    customer_name: str,
    catalogue: list[dict[str, Any]],
    calc: dict[str, Any],
    unknown: list[str],
    amount_expected: int | None,
    explicit_total: int | None,
    catalogue_total: int | None,
    discrepancy: bool,
    payment_mode_choice: str = "mock",
) -> dict[str, Any]:
    parser_status = (
        "NEEDS_REVIEW" if unknown or amount_expected is None else "READY_FOR_RECONCILIATION"
    )
    if discrepancy:
        parser_status = "NEEDS_REVIEW"

    order_id = event_store.next_bot_order_id()
    pay_req = build_bot_payment_links(
        order_id=order_id,
        amount=int(amount_expected or 0),
        description=f"WarungFlow {order_id}",
        payment_mode_choice=payment_mode_choice,
        customer_name=customer_name,
        customer_phone=from_phone,
    )
    pay_url = str(pay_req.get("payment_url") or "")

    lines = [f"Halo {customer_name}! Pesanan kamu:"]
    for it in calc.get("items") or []:
        if it.get("status") == "MATCHED":
            lines.append(
                f"- {it.get('product_name')} x{it.get('quantity')} = "
                f"Rp {int(it.get('line_total') or 0):,}"
            )
        else:
            lines.append(f"- {it.get('raw_text')} (produk tidak dikenal)")
    if unknown:
        lines.append(f"\n⚠ Produk tidak di katalog: {', '.join(unknown)}")
    lines.append(f"\nTotal: Rp {int(amount_expected or 0):,}")
    lines.append(f"Order ID: {order_id}")
    lines.extend(format_payment_message_lines(pay_req, payment_mode_choice=payment_mode_choice))
    lines.append(
        "\nSetelah pembayaran masuk, WarungFlow akan otomatis update status. Terima kasih 🙏"
    )
    reply = "\n".join(lines)

    raw_line = f"{message_text.strip()} - {customer_name}"
    order_rec = {
        "order_id": order_id,
        "customer_name": customer_name,
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
            **pay_req,
            "payment_request_id": pay_req.get("id") or pay_req.get("payment_request_id"),
            "order_id": order_id,
            "amount": amount_expected,
            "customer_name": customer_name,
            "customer_phone": from_phone,
            "status": "PENDING",
            "payment_url": pay_url,
        },
    }
    event_store.append_bot_order(order_rec)
    get_whatsapp_provider().send_text(from_phone, reply, order_id=order_id)
    return order_rec


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
    payment_mode_choice: str = "mock",
) -> dict[str, Any]:
    """Full bot pipeline for one inbound message."""
    phone_raw = (from_phone or "").strip()
    phone_digits = re.sub(r"\D", "", phone_raw)
    if len(phone_digits) < 9:
        return {
            "status": "error",
            "intent": "VALIDATION",
            "detail": "phone_required",
            "message": "Nomor WhatsApp wajib (minimal 9 digit).",
        }

    mid = message_id or f"sim-{uuid.uuid4().hex[:12]}"
    formatted_phone = phone_raw if phone_raw.startswith("+") else f"+{phone_digits}"
    stored = event_store.append_inbound_message(
        message_id=mid,
        from_phone=formatted_phone,
        text=message_text,
        customer_name=customer_name,
        source=source,
    )
    if stored is None:
        return {"status": "duplicate", "message_id": mid}

    from_phone = formatted_phone
    catalogue = normalize_catalogue_tool(catalogue or load_product_catalogue_from_csv())
    provider = get_whatsapp_provider()
    pending = event_store.get_pending_order(from_phone)

    if pending:
        if CONFIRM_NO_RE.match(message_text.strip()):
            event_store.clear_pending_order(from_phone)
            reply = "Pesanan dibatalkan. Silakan kirim pesanan baru kapan saja."
            provider.send_text(from_phone, reply)
            event_store.mark_message_processed(mid)
            return {"status": "ok", "intent": "CONFIRM_CANCELLED", "message_id": mid}

        if CONFIRM_YES_RE.match(message_text.strip()):
            gaps = pending.get("gaps") or []
            if gaps:
                reply = (
                    "Masih ada data yang belum lengkap:\n"
                    + "\n".join(f"• {g}" for g in gaps)
                    + "\n\nLengkapi dulu, lalu balas *ya* lagi."
                )
                provider.send_text(from_phone, reply)
                event_store.mark_message_processed(mid)
                return {
                    "status": "ok",
                    "intent": "CONFIRM_PENDING",
                    "message_id": mid,
                    "gaps": gaps,
                }
            name = str(pending.get("customer_name") or "Pelanggan")
            order_rec = _finalize_bot_order(
                from_phone=from_phone,
                message_text=str(pending.get("message_text") or message_text),
                customer_name=name,
                catalogue=catalogue,
                calc={"items": pending.get("items") or []},
                unknown=list(pending.get("unknown_products") or []),
                amount_expected=pending.get("amount_expected"),
                explicit_total=pending.get("explicit_total"),
                catalogue_total=pending.get("catalogue_total"),
                discrepancy=bool(pending.get("discrepancy")),
                payment_mode_choice=payment_mode_choice,
            )
            event_store.clear_pending_order(from_phone)
            event_store.mark_message_processed(mid)
            return {
                "status": "ok",
                "intent": "ORDER",
                "message_id": mid,
                "order": order_rec,
                "auto_refresh": True,
                "confirmed": True,
            }

        name_hint = _parse_name_only_reply(message_text)
        if name_hint:
            pending["customer_name"] = name_hint
            pending["gaps"] = _analyze_order_gaps(
                message_text=str(pending.get("message_text") or ""),
                customer_name=name_hint,
                calc={"items": pending.get("items") or []},
                unknown=list(pending.get("unknown_products") or []),
                amount_expected=pending.get("amount_expected"),
            )
            event_store.set_pending_order(from_phone, pending)
            reply = _build_confirm_reply(
                customer_name=name_hint,
                calc={"items": pending.get("items") or []},
                unknown=list(pending.get("unknown_products") or []),
                amount_expected=pending.get("amount_expected"),
                gaps=pending["gaps"],
            )
            provider.send_text(from_phone, reply)
            event_store.mark_message_processed(mid)
            return {
                "status": "ok",
                "intent": "CONFIRM_PENDING",
                "message_id": mid,
                "gaps": pending["gaps"],
            }

        reply = (
            "Masih menunggu konfirmasi pesanan sebelumnya.\n"
            "Balas *ya* jika sudah benar, *batal* untuk membatalkan, "
            "atau kirim nama pelanggan (contoh: Kevin)."
        )
        provider.send_text(from_phone, reply)
        event_store.mark_message_processed(mid)
        return {"status": "ok", "intent": "CONFIRM_PENDING", "message_id": mid}

    intent = classify_intent(message_text)

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
        unknown = list(calc.get("unknown_products") or [])
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
        resolved_name = _resolve_customer_name(message_text, customer_name)
        gaps = _analyze_order_gaps(
            message_text=message_text,
            customer_name=resolved_name,
            calc=calc,
            unknown=unknown,
            amount_expected=amount_expected,
        )

        if gaps:
            draft = {
                "message_text": message_text,
                "customer_name": resolved_name,
                "items": calc.get("items"),
                "unknown_products": unknown,
                "amount_expected": amount_expected,
                "catalogue_total": catalogue_total,
                "explicit_total": explicit_total,
                "discrepancy": discrepancy,
                "gaps": gaps,
            }
            event_store.set_pending_order(from_phone, draft)
            reply = _build_confirm_reply(
                customer_name=resolved_name,
                calc=calc,
                unknown=unknown,
                amount_expected=amount_expected,
                gaps=gaps,
            )
            provider.send_text(from_phone, reply)
            event_store.mark_message_processed(mid)
            return {
                "status": "ok",
                "intent": "CONFIRM_PENDING",
                "message_id": mid,
                "gaps": gaps,
                "needs_confirmation": True,
            }

        name = resolved_name or "Pelanggan"
        order_rec = _finalize_bot_order(
            from_phone=from_phone,
            message_text=message_text,
            customer_name=name,
            catalogue=catalogue,
            calc=calc,
            unknown=unknown,
            amount_expected=amount_expected,
            explicit_total=explicit_total,
            catalogue_total=catalogue_total,
            discrepancy=discrepancy,
            payment_mode_choice=payment_mode_choice,
        )
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
