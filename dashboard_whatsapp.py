"""Streamlit UI for WhatsApp bot mode + mock payments."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from dashboard import (
    hint_box_html,
    human_bot_status,
    page_intro_html,
    page_stack_close_html,
    page_stack_open_html,
    section_header_html,
    status_pills_html,
)
from session_runtime import mark_data_changed
from tools import event_store
from tools.bot_service import process_inbound_message, simulate_mock_payment
from tools.whatsapp_provider import get_whatsapp_provider, mask_token


def _fmt_rp(n: Any) -> str:
    try:
        return f"Rp {int(n):,}"
    except (TypeError, ValueError):
        return "—"


def _orders_display(orders: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Pelanggan": o.get("customer_name") or "—",
                "Total": _fmt_rp(o.get("amount_expected")),
                "Status": human_bot_status(o.get("payment_status")),
            }
            for o in orders
        ]
    )


def render_whatsapp_bot_page() -> None:
    mode = (os.getenv("WHATSAPP_MODE") or "mock").strip().lower()
    is_mock = mode != "cloud"

    st.markdown(
        page_intro_html(
            "WhatsApp Bot",
            "Terima pesanan seperti chat WhatsApp — cukup ketik menu dan jumlah, total dihitung otomatis dari katalog.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    st.markdown(
        status_pills_html(
            [
                ("Mode demo aman" if is_mock else "WhatsApp Cloud aktif", "ok"),
                ("Tanpa setup teknis" if is_mock else "Webhook terhubung", "muted"),
            ]
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        hint_box_html(
            "Coba kirim pesanan contoh di bawah. Setelah bayar (simulasi), "
            "WarungFlow otomatis memperbarui rekonsiliasi di Beranda."
        ),
        unsafe_allow_html=True,
    )

    # --- Simulate order ---
    st.markdown(
        section_header_html(
            "Simulasi pesanan",
            "Seolah-olah pelanggan mengirim chat ke warung Anda.",
            icon="chat",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            customer_name = st.text_input("Nama pelanggan", value="Kevin", key="bot_cust")
            from_phone = st.text_input("No. HP (opsional)", value="+628123456789", key="bot_phone")
        with c2:
            message_text = st.text_area(
                "Isi pesan",
                value="nasi goreng 2 es teh 1",
                height=88,
                key="bot_msg",
                help="Format: nama produk + jumlah, mis. pisgor 3 teh manis 2",
            )
        if st.button("Kirim pesanan simulasi", type="primary", use_container_width=True):
            cat = st.session_state.get("product_catalogue")
            result = process_inbound_message(
                from_phone=from_phone,
                message_text=message_text,
                customer_name=customer_name,
                source="streamlit_simulator",
                catalogue=cat,
            )
            if result.get("auto_refresh"):
                mark_data_changed("whatsapp_bot_order")
            intent = result.get("intent") or "—"
            if result.get("status") == "ok" and result.get("order"):
                order = result["order"]
                st.success(
                    f"Pesanan diterima · total {_fmt_rp(order.get('amount_expected'))} · "
                    f"{human_bot_status(order.get('payment_status'))}"
                )
            else:
                st.info(f"Balasan bot: {intent}")
            st.rerun()

    orders = event_store.get_recent_bot_orders(30)

    # --- Active orders ---
    st.markdown(
        section_header_html(
            "Pesanan dari bot",
            "Daftar pesanan WhatsApp terbaru dan status pembayarannya.",
            icon="receipt_long",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if orders:
            st.dataframe(
                _orders_display(orders),
                use_container_width=True,
                hide_index=True,
                height=min(120 + 42 * len(orders), 360),
            )
        else:
            st.caption("Belum ada pesanan — kirim simulasi di atas.")

    unpaid = [o for o in orders if o.get("payment_status") == "AWAITING_PAYMENT"]
    if unpaid:
        st.markdown(
            section_header_html(
                "Simulasi pembayaran",
                "Uji alur bayar tanpa QRIS sungguhan — cocok untuk demo hakim.",
                icon="payments",
                variant="muted",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            labels = {
                o["order_id"]: f"{o.get('customer_name')} · {_fmt_rp(o.get('amount_expected'))}"
                for o in unpaid
            }
            pick = st.selectbox(
                "Pilih pesanan",
                options=list(labels.keys()),
                format_func=lambda k: labels[k],
                key="bot_pay_pick",
            )
            partial = st.checkbox("Bayar setengah (50%)", key="bot_partial")
            if st.button("Tandai sudah bayar", key="bot_sim_pay", type="primary"):
                order = event_store.get_bot_order(pick) or {}
                amt = int(order.get("amount_expected") or 0)
                if partial:
                    amt = max(1, amt // 2)
                res = simulate_mock_payment(
                    order_id=pick,
                    amount=amt,
                    payer_name=order.get("customer_name"),
                )
                mark_data_changed("whatsapp_bot_payment")
                if res.get("status") == "ok":
                    st.success("Pembayaran tercatat — cek Beranda untuk rekonsiliasi.")
                else:
                    st.warning(str(res.get("detail") or res))
                st.rerun()

    # --- Activity ---
    st.markdown(
        section_header_html(
            "Aktivitas chat",
            "Pesan masuk dan balasan warung (demo).",
            icon="forum",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            section_header_html("Pesan masuk", "", icon="inbox", variant="muted"),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            in_rows = event_store.list_inbound_messages(12)
            if in_rows:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Pelanggan": r.get("customer_name") or "—",
                                "Pesan": (r.get("text") or "")[:80],
                                "Waktu": (r.get("timestamp") or "")[:16],
                            }
                            for r in in_rows
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Belum ada pesan masuk.")
    with col_b:
        st.markdown(
            section_header_html("Balasan warung", "", icon="send", variant="muted"),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            outbox = event_store.list_outbound_messages(12)
            if outbox:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Isi": (r.get("text") or "")[:100],
                                "Waktu": (r.get("timestamp") or "")[:16],
                            }
                            for r in outbox
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Belum ada balasan.")

    st.markdown(
        section_header_html(
            "Pembersihan demo",
            "Hapus riwayat simulasi bot di perangkat ini.",
            icon="restart_alt",
            variant="muted",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if st.button("Reset riwayat bot demo", key="bot_reset_events", use_container_width=True):
            event_store.reset_runtime_events()
            mark_data_changed("bot_events_reset")
            st.rerun()

    st.markdown(page_stack_close_html(), unsafe_allow_html=True)

    with st.expander("Pengaturan teknis (opsional)", expanded=False):
        bot_url = (os.getenv("BOT_SERVER_URL") or "http://localhost:8000").rstrip("/")
        st.caption("Hanya diperlukan jika menjalankan server webhook terpisah.")
        st.markdown(f"**Mode:** {'Mock' if is_mock else 'Cloud API'}")
        st.markdown(f"**URL server:** `{bot_url}`")
        st.markdown(f"**Token:** {mask_token(os.getenv('WHATSAPP_ACCESS_TOKEN'))}")
        st.markdown(f"**Verify token:** {mask_token(os.getenv('WHATSAPP_VERIFY_TOKEN'))}")
        st.code("python -m uvicorn bot_server:app --reload --port 8000", language="bash")
        _ = get_whatsapp_provider()
