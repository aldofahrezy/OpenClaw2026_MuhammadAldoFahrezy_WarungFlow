"""Halaman Simulasi — chat WhatsApp, pembayaran QRIS, pengeluaran, dan kontrol demo."""

from __future__ import annotations

import html
import os
import re
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from config import RuntimeConfig, has_doku_credentials
from dashboard import (
    hint_box_html,
    human_bot_status,
    page_intro_html,
    page_stack_close_html,
    page_stack_open_html,
    section_header_html,
    status_pills_html,
    whatsapp_reply_hero_html,
    whatsapp_thread_html,
)
from live_sandbox import (
    EXPENSE_CATEGORIES,
    append_expense,
    append_payment_transaction,
)
from session_runtime import (
    get_agent_state,
    mark_data_changed,
    reset_bot_demo_history,
    reset_demo_session,
    save_ui_session_snapshot,
)
from tools import event_store
from tools.bot_service import process_inbound_message, simulate_mock_payment
from tools.whatsapp_provider import get_whatsapp_provider, mask_token


def _fmt_rp(n: Any) -> str:
    try:
        return f"Rp {int(n):,}"
    except (TypeError, ValueError):
        return "—"


def _set_active_chat_phone(phone: str) -> None:
    key = event_store.normalize_phone(phone) or (phone or "").strip()
    st.session_state.active_chat_phone = key


def _chat_room_button_label(th: dict[str, Any]) -> str:
    """Nama + nomor telepon saja (sidebar ruangan chat)."""
    name = th.get("customer_name") or "Pelanggan"
    phone = event_store.display_phone(th.get("phone"), th.get("phone_key"))
    return f"{name}\n{phone}"


def _validate_whatsapp_phone(phone: str) -> tuple[str | None, str | None]:
    """Return (formatted phone, error message)."""
    raw = (phone or "").strip()
    if not raw:
        return None, (
            "Nomor WhatsApp wajib diisi — bot mengelompokkan chat dan balasan per nomor HP."
        )
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 9:
        return None, "Nomor tidak valid. Gunakan format internasional, mis. +628123456789."
    formatted = raw if raw.startswith("+") else f"+{digits}"
    return formatted, None


def _render_chat_rooms() -> None:
    threads = event_store.build_chat_threads()
    if not threads:
        st.caption("Belum ada percakapan — kirim pesanan simulasi untuk memulai ruangan chat.")
        return

    phone_keys = [t["phone_key"] for t in threads]
    active_key = event_store.normalize_phone(st.session_state.get("active_chat_phone"))
    if not active_key or active_key not in phone_keys:
        active_key = phone_keys[0]
        st.session_state.active_chat_phone = active_key

    room_col, thread_col = st.columns([1, 2.3], gap="medium")
    with room_col:
        st.markdown('<p class="wf-subsection-title">Ruangan chat</p>', unsafe_allow_html=True)
        st.markdown('<div class="wf-chat-rooms-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
        for th in threads:
            pk = th["phone_key"]
            is_active = pk == active_key
            if st.button(
                _chat_room_button_label(th),
                key=f"wa_room_{pk}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if pk != active_key:
                    _set_active_chat_phone(pk)
                    save_ui_session_snapshot()
                    st.rerun()

    active = next((t for t in threads if t["phone_key"] == active_key), threads[0])

    with thread_col:
        name = active.get("customer_name") or "Pelanggan"
        phone = event_store.display_phone(active.get("phone"), active.get("phone_key"))
        orders = active.get("order_ids") or []
        order_txt = ", ".join(orders) if orders else "belum ada order"
        st.markdown(
            f"""
<div class="wf-chat-thread-head">
  <h4>{html.escape(name)}</h4>
  <p>{html.escape(phone)} · Order: {html.escape(order_txt)}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        out_msgs = [m for m in active.get("messages") or [] if m.get("direction") == "out"]
        if out_msgs:
            st.markdown(
                whatsapp_reply_hero_html(out_msgs[-1]),
                unsafe_allow_html=True,
            )
        st.markdown(
            whatsapp_thread_html(active.get("messages") or []),
            unsafe_allow_html=True,
        )

        pending = event_store.get_pending_order(active.get("phone_key") or phone)
        if pending:
            st.info(
                "Bot menunggu konfirmasi — balas di kotak bawah: **ya** untuk proses pesanan, "
                "**batal** untuk batalkan, atau kirim **nama** (mis. `Aldo`).",
                icon="💬",
            )

        st.markdown('<p class="wf-subsection-title">Balas chat</p>', unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("ya", key=f"chat_quick_ya_{active_key}", use_container_width=True):
                _submit_whatsapp_order(
                    from_phone=phone,
                    message_text="ya",
                    customer_name=None,
                    source="streamlit_chat_reply",
                )
        with q2:
            if st.button("batal", key=f"chat_quick_no_{active_key}", use_container_width=True):
                _submit_whatsapp_order(
                    from_phone=phone,
                    message_text="batal",
                    customer_name=None,
                    source="streamlit_chat_reply",
                )
        with q3:
            if st.button("menu", key=f"chat_quick_menu_{active_key}", use_container_width=True):
                _submit_whatsapp_order(
                    from_phone=phone,
                    message_text="menu",
                    customer_name=None,
                    source="streamlit_chat_reply",
                )
        reply_row1, reply_row2 = st.columns([5, 1])
        with reply_row1:
            reply_text = st.text_input(
                "Tulis balasan",
                key=f"chat_reply_{active_key}",
                placeholder="Ketik balasan bebas, mis. Aldo atau nasi goreng 2 - Kevin",
                label_visibility="collapsed",
            )
        with reply_row2:
            if st.button(
                "Kirim",
                key=f"chat_send_{active_key}",
                type="primary",
                use_container_width=True,
            ):
                _submit_whatsapp_order(
                    from_phone=phone,
                    message_text=reply_text,
                    customer_name=None,
                    source="streamlit_chat_reply",
                )


def _submit_whatsapp_order(
    *,
    from_phone: str,
    message_text: str,
    customer_name: str | None,
    source: str,
) -> None:
    phone_ok, phone_err = _validate_whatsapp_phone(from_phone)
    if phone_err:
        st.warning(phone_err)
        return
    if not message_text.strip():
        st.warning("Isi pesan tidak boleh kosong.")
        return
    cat = st.session_state.get("product_catalogue")
    result = process_inbound_message(
        from_phone=phone_ok or from_phone,
        message_text=message_text,
        customer_name=customer_name,
        source=source,
        catalogue=cat,
        payment_mode_choice=st.session_state.get("payment_mode_choice", "mock"),
    )
    if result.get("auto_refresh"):
        mark_data_changed("whatsapp_bot_order")
    _set_active_chat_phone(phone_ok or from_phone)
    _show_bot_result(result)
    st.rerun()


def _show_bot_result(result: dict[str, Any]) -> None:
    intent = result.get("intent") or "—"
    if result.get("status") == "ok" and result.get("order"):
        order = result["order"]
        st.success(
            f"Pesanan dikonfirmasi · total {_fmt_rp(order.get('amount_expected'))} · "
            f"{human_bot_status(order.get('payment_status'))}"
        )
    elif intent == "CONFIRM_PENDING":
        gaps = result.get("gaps") or []
        st.warning(
            "Bot meminta konfirmasi dulu — cek balasan hijau di bawah, lalu balas *ya* "
            "dengan pesan berikutnya (atau lengkapi nama lalu *ya*).",
            icon="⏳",
        )
        if gaps:
            st.caption("Belum lengkap: " + " · ".join(gaps))
    elif intent == "CONFIRM_CANCELLED":
        st.info("Pesanan dibatalkan.")
    elif result.get("status") == "duplicate":
        st.warning("Pesan duplikat — tidak diproses lagi.")
    elif result.get("detail") == "phone_required" or result.get("intent") == "VALIDATION":
        st.warning(result.get("message") or "Nomor WhatsApp wajib diisi.")
    else:
        st.info(f"Balasan bot: {intent}")


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


def _render_analysis_controls() -> None:
    st.markdown(
        section_header_html(
            "Kontrol analisis",
            "Aktifkan perbarui otomatis agar agen menghitung ulang setelah Anda mengubah data simulasi.",
            icon="sync",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            auto_on = st.toggle(
                "Perbarui otomatis saat data berubah",
                value=bool(st.session_state.get("auto_refresh_enabled", True)),
                key="sim_auto_refresh",
            )
            st.session_state.auto_refresh_enabled = auto_on
            if auto_on and st.session_state.get("data_stale"):
                from session_runtime import reconcile_session_freshness

                reconcile_session_freshness()
        with c2:
            if st.button(
                "Paksa refresh analisis",
                use_container_width=True,
                type="primary",
                key="sim_force_refresh",
            ):
                st.session_state._pending_agent_run = True
                st.session_state._pending_trigger = "manual_refresh"
                st.session_state.ui_status = "Auto-refreshing"
                st.session_state.ui_status_detail = "Manual refresh"
                st.rerun()
        with c3:
            if st.button("Reset demo", use_container_width=True, key="sim_reset_demo"):
                reset_demo_session()
                st.rerun()


def _render_demo_settings(cfg: RuntimeConfig, prod_ui: bool) -> None:
    st.markdown(
        section_header_html(
            "Pengaturan demo",
            "Profil warung contoh dan mode pembayaran untuk sesi ini.",
            icon="tune",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    agent_preview = get_agent_state()
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**Profil warung**")
            profile = None
            if agent_preview and agent_preview.merchant_profile:
                profile = agent_preview.merchant_profile
            elif st.session_state.merchant_profile:
                profile = st.session_state.merchant_profile
            if profile:
                st.markdown(f"**Nama:** {profile.get('merchant_name', 'N/A')}")
                st.markdown(f"**Pemilik:** {profile.get('owner_name', 'N/A')}")
                st.markdown(f"**Kota:** {profile.get('city', 'N/A')}")
                methods = ", ".join(profile.get("payment_methods", []))
                st.markdown(f"**Metode bayar:** {methods}")
            else:
                st.caption("Data contoh dimuat otomatis saat pertama kali dibuka.")
    with c2:
        with st.container(border=True):
            st.markdown("**Mode pembayaran**")
            prev_pay = st.session_state.get("_last_payment_mode_choice")
            pay_choice = st.selectbox(
                "Mode pembayaran",
                options=["mock", "doku_sandbox"],
                format_func=lambda x: "Mock (demo aman)" if x == "mock" else "DOKU Sandbox",
                label_visibility="collapsed",
                key="payment_mode_choice",
            )
            if prev_pay is not None and pay_choice != prev_pay:
                st.session_state._last_payment_mode_choice = pay_choice
                save_ui_session_snapshot()
                mark_data_changed("payment_mode_change")
                st.rerun()
            else:
                st.session_state._last_payment_mode_choice = pay_choice
            ui_mode = st.session_state.get("payment_mode_choice", "mock")
            effective = cfg.payment_mode
            doku_ready = has_doku_credentials()
            if ui_mode == "doku_sandbox" and not doku_ready:
                st.warning(
                    "DOKU Sandbox dipilih tetapi kredensial DOKU belum lengkap di .env. "
                    "Agen memakai Mock sampai DOKU_CLIENT_ID dan DOKU_SECRET_KEY terisi.",
                    icon="⚠️",
                )
            mode_line = (
                f"UI: {ui_mode} · agen: {effective}"
                if ui_mode != effective
                else f"Mode aktif: {effective}"
            )
            doku_note = "kredensial DOKU OK" if doku_ready else "kredensial DOKU belum lengkap"
            if prod_ui:
                st.caption(
                    f"{cfg.warungflow_env} · LLM {cfg.llm_mode} · {mode_line} · {doku_note}"
                )
            else:
                st.caption(f"{mode_line} · {doku_note}")
            if cfg.warnings:
                for w in cfg.warnings:
                    st.warning(w)

    if not prod_ui:
        with st.expander("Environment (masked)", expanded=False):
            for line in cfg.env_summary_masked():
                st.code(line, language="text")


def _render_tab_whatsapp() -> None:
    mode = (os.getenv("WHATSAPP_MODE") or "mock").strip().lower()
    is_mock = mode != "cloud"
    st.markdown(
        status_pills_html(
            [
                ("Mode demo aman" if is_mock else "WhatsApp Cloud aktif", "ok"),
                ("Pesan masuk & balasan bot" if is_mock else "Webhook terhubung", "muted"),
            ]
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        section_header_html(
            "Kirim pesanan WhatsApp",
            "Satu tempat untuk simulasi bot — pilih form terstruktur atau tempel teks chat seperti WhatsApp asli.",
            icon="chat",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        from_phone = st.text_input(
            "No. WhatsApp (wajib)",
            value="+628123456789",
            key="bot_phone",
            placeholder="+628123456789",
            help="Satu nomor = satu ruangan chat. Dipakai untuk form maupun teks plain.",
        )
        tab_form, tab_plain = st.tabs(["Form terstruktur", "Teks chat (plain)"])

        with tab_form:
            st.caption("Isi menu dan jumlah per kolom — cocok untuk demo terstruktur.")
            c1, c2 = st.columns(2)
            with c1:
                customer_name = st.text_input(
                    "Nama pelanggan (opsional)",
                    value="",
                    key="bot_cust",
                    placeholder="Kosongkan jika sudah ada di pesan, mis. - Kevin",
                )
            with c2:
                message_text = st.text_area(
                    "Isi pesan",
                    value="nasi goreng 2 es teh 1",
                    height=88,
                    key="bot_msg",
                    help="Format: nama produk + jumlah, mis. pisgor 3 teh manis 2",
                )
            if st.button("Kirim pesanan", type="primary", use_container_width=True, key="bot_send_form"):
                _submit_whatsapp_order(
                    from_phone=from_phone,
                    message_text=message_text,
                    customer_name=customer_name.strip() or None,
                    source="streamlit_simulator",
                )

        with tab_plain:
            st.caption(
                "Simulasikan pesanan melalui teks whatsapp tanpa format form — "
                "tempel satu baris chat lengkap (nama bisa di akhir pesan)."
            )
            wa_msg = st.text_area(
                "Pesanan WhatsApp",
                placeholder="Mbak, nasi goreng 2 total 44000, bayar nanti malam - Kevin",
                height=96,
                key="sandbox_wa_order",
            )
            if st.button("Kirim pesanan", type="primary", use_container_width=True, key="bot_send_plain"):
                _submit_whatsapp_order(
                    from_phone=from_phone,
                    message_text=wa_msg,
                    customer_name=None,
                    source="streamlit_manual_text",
                )

    orders = event_store.get_recent_bot_orders(30)
    st.markdown("**Pesanan dari bot**")
    with st.container(border=True):
        if orders:
            st.dataframe(
                _orders_display(orders),
                use_container_width=True,
                hide_index=True,
                height=min(120 + 42 * len(orders), 280),
            )
        else:
            st.caption("Belum ada pesanan — kirim simulasi di atas.")

    unpaid = [o for o in orders if o.get("payment_status") == "AWAITING_PAYMENT"]
    if unpaid:
        st.markdown("**Bayar pesanan bot (simulasi)**")
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
                    st.success("Pembayaran tercatat — cek Beranda.")
                else:
                    st.warning(str(res.get("detail") or res))
                st.rerun()

    st.markdown('<div class="wf-spacer-md"></div>', unsafe_allow_html=True)
    st.markdown(
        section_header_html(
            "Aktivitas chat",
            "Satu ruangan per nomor WhatsApp — pilih pelanggan untuk lihat percakapan lengkap.",
            icon="forum",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        _render_chat_rooms()

    if st.button("Reset riwayat bot demo", key="bot_reset_events", use_container_width=True):
        reset_bot_demo_history()
        st.rerun()


def _render_tab_payment() -> None:
    st.markdown(
        hint_box_html(
            "Simulasikan mutasi QRIS / transfer masuk ke rekening warung. "
            "Agen akan mencocokkan nama dan catatan bank dengan pesanan."
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            pay_name = st.text_input("Nama pembayar", value="Kevin", key="sandbox_payer")
            pay_amt = st.number_input(
                "Nominal (Rp)", min_value=0, value=44000, step=1000, key="sandbox_amt"
            )
        with c2:
            pay_method = st.selectbox(
                "Metode", ["QRIS", "transfer", "cash"], key="sandbox_method"
            )
            pay_ref = st.text_input(
                "Catatan / referensi bank",
                value="nasi goreng Kevin",
                key="sandbox_ref",
                help="Wajib sertakan ORD-BOT-xxxx atau nama pelanggan + nominal yang sama "
                "agar pesanan bot ter-update.",
            )
        if st.button("Tambah pembayaran", key="sandbox_add_pay", type="primary", use_container_width=True):
            if append_payment_transaction(pay_name, int(pay_amt), pay_method, pay_ref):
                linked = st.session_state.pop("_last_linked_bot_order", None)
                if linked:
                    st.success(
                        f"Pembayaran ditambahkan dan {linked} ditandai PAID. "
                        "Analisis agen berjalan otomatis — cek Beranda / Rekonsiliasi."
                    )
                else:
                    st.success(
                        "Pembayaran ditambahkan. Analisis agen berjalan otomatis — "
                        "pastikan catatan berisi ORD-BOT-xxxx atau nama + nominal cocok."
                    )
            else:
                st.warning(
                    "Duplikat — pembayaran tidak ditambahkan lagi. "
                    "Klik **Refresh analisis** jika sudah pernah menambahkan."
                )
            st.rerun()


def _render_tab_expense() -> None:
    st.markdown(
        hint_box_html(
            "Catat pengeluaran harian warung. Net profit dan skor kesehatan di Beranda akan berubah."
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        ex1, ex2 = st.columns(2)
        with ex1:
            exp_date = st.date_input("Tanggal", value=date.today(), key="sandbox_exp_date")
            exp_category = st.selectbox(
                "Kategori",
                options=list(EXPENSE_CATEGORIES),
                index=0,
                key="sandbox_exp_cat",
            )
        with ex2:
            exp_amount = st.number_input(
                "Nominal (Rp)",
                min_value=0,
                value=75_000,
                step=5000,
                key="sandbox_exp_amt",
            )
            exp_desc = st.text_input(
                "Keterangan",
                value="Tambahan belanja ayam",
                key="sandbox_exp_desc",
            )
        if st.button("Tambah pengeluaran", key="sandbox_add_expense", type="primary", use_container_width=True):
            if append_expense(exp_category, exp_desc, int(exp_amount), exp_date.isoformat()):
                st.success("Pengeluaran ditambahkan.")
            else:
                st.warning("Duplikat — pengeluaran tidak ditambahkan lagi.")
            st.rerun()


def render_simulator_page(cfg: RuntimeConfig, prod_ui: bool) -> None:
    st.markdown(
        page_intro_html(
            "Simulasi",
            "Uji skenario lewat form manual: chat WhatsApp, mutasi pembayaran QRIS, dan pengeluaran.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    _render_analysis_controls()
    _render_demo_settings(cfg, prod_ui)

    st.markdown(
        section_header_html(
            "Laboratorium data",
            "Pilih jenis simulasi — perubahan langsung memengaruhi analisis di Beranda.",
            icon="science",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )

    tab_wa, tab_pay, tab_exp = st.tabs(
        ["Chat WhatsApp", "Pembayaran QRIS", "Pengeluaran"]
    )
    with tab_wa:
        _render_tab_whatsapp()
    with tab_pay:
        _render_tab_payment()
    with tab_exp:
        _render_tab_expense()

    st.markdown(page_stack_close_html(), unsafe_allow_html=True)

    with st.expander("Pengaturan teknis WhatsApp (opsional)", expanded=False):
        mode = (os.getenv("WHATSAPP_MODE") or "mock").strip().lower()
        is_mock = mode != "cloud"
        bot_url = (os.getenv("BOT_SERVER_URL") or "http://localhost:8000").rstrip("/")
        st.caption("Hanya jika menjalankan server webhook terpisah.")
        st.markdown(f"**Mode:** {'Mock' if is_mock else 'Cloud API'}")
        st.markdown(f"**URL server:** `{bot_url}`")
        st.markdown(f"**Token:** {mask_token(os.getenv('WHATSAPP_ACCESS_TOKEN'))}")
        st.code("python -m uvicorn bot_server:app --reload --port 8000", language="bash")
        _ = get_whatsapp_provider()
