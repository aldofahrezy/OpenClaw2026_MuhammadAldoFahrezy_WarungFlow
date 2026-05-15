"""DOKU Sandbox payment simulator page (Midtrans-style) inside Streamlit."""

from __future__ import annotations

import html

import streamlit as st

from tools import event_store
from tools.bot_service import simulate_mock_payment
from tools.doku_payment_sync import sync_doku_order_payment


def _fmt_rp(amount: int | None) -> str:
    if amount is None:
        return "—"
    return f"Rp {int(amount):,}"


def render_doku_checkout_page(order_id: str) -> bool:
    """
    Render ?doku_pay= handler. Returns True if page was shown (caller should stop main UI).
    """
    oid = (order_id or "").strip()
    if not oid:
        return False

    order = event_store.get_bot_order(oid)
    if not order:
        st.error(f"Pesanan {html.escape(oid)} tidak ditemukan.")
        return True

    pr = order.get("payment_request") or {}
    hosted = str(pr.get("hosted_checkout_url") or "").strip()
    simulator = str(pr.get("payment_url") or "").strip()
    amount = int(order.get("amount_expected") or 0)
    name = html.escape(str(order.get("customer_name") or "Pelanggan"))
    status = str(order.get("payment_status") or "AWAITING_PAYMENT")

    if status != "PAID" and pr.get("hosted_checkout_url"):
        auto_key = f"_doku_auto_sync_{oid}"
        if not st.session_state.get(auto_key):
            st.session_state[auto_key] = True
            sync_res = sync_doku_order_payment(oid)
            if sync_res.get("status") == "ok":
                status = "PAID"
                order = event_store.get_bot_order(oid) or order
            elif sync_res.get("status") == "already_paid":
                status = "PAID"

    st.markdown(
        f"""
<div style="max-width:520px;margin:0 auto;padding:1rem 0;">
  <div style="background:linear-gradient(135deg,#1a3a5c,#2d6a9f);color:#fff;padding:1.25rem;border-radius:12px 12px 0 0;">
    <p style="margin:0;font-size:0.75rem;opacity:0.9;">DOKU Sandbox · Simulator</p>
    <h2 style="margin:0.35rem 0 0 0;font-size:1.35rem;">Checkout Pembayaran</h2>
  </div>
  <div style="background:#fff;border:1px solid #d0d7de;border-top:none;padding:1.25rem;border-radius:0 0 12px 12px;">
    <p style="margin:0 0 0.5rem 0;color:#64748b;font-size:0.85rem;">Merchant</p>
    <p style="margin:0 0 1rem 0;font-weight:700;">Warung Bu Sari / WarungFlow</p>
    <p style="margin:0;color:#64748b;font-size:0.85rem;">Pelanggan</p>
    <p style="margin:0 0 0.75rem 0;font-weight:600;">{name}</p>
    <p style="margin:0;color:#64748b;font-size:0.85rem;">Order ID</p>
    <p style="margin:0 0 0.75rem 0;font-family:monospace;">{html.escape(oid)}</p>
    <p style="margin:0;color:#64748b;font-size:0.85rem;">Total</p>
    <p style="margin:0 0 1rem 0;font-size:1.5rem;font-weight:800;color:#006b47;">{_fmt_rp(amount)}</p>
    <p style="margin:0;color:#64748b;font-size:0.85rem;">Status</p>
    <p style="margin:0 0 1rem 0;">{html.escape(status)}</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.caption(
        "Alur uji seperti Midtrans Sandbox: buka checkout DOKU resmi (opsional), "
        "lalu konfirmasi hasil di sini."
    )

    if hosted:
        st.link_button("Buka checkout DOKU Sandbox (resmi)", hosted, use_container_width=True)
    elif pr.get("api_error"):
        st.warning(f"API DOKU: {pr.get('api_error')}")

    if status != "PAID" and pr.get("hosted_checkout_url"):
        if st.button(
            "↻ Cek status pembayaran DOKU",
            use_container_width=True,
            key=f"doku_poll_{oid}",
        ):
            sync_res = sync_doku_order_payment(oid)
            if sync_res.get("status") == "ok":
                st.success("Pembayaran terdeteksi dari DOKU. Status pesanan sudah diperbarui.")
                from session_runtime import mark_data_changed

                mark_data_changed("doku_status_sync")
                if st.session_state.get("auto_refresh_enabled", True):
                    st.session_state._pending_agent_run = True
                    st.session_state._pending_trigger = "doku_status_sync"
                st.rerun()
            elif sync_res.get("status") == "pending":
                st.warning(str(sync_res.get("detail") or "Masih menunggu pembayaran di DOKU."))
            elif sync_res.get("status") == "already_paid":
                st.info("Pesanan sudah lunas.")
                st.rerun()
            else:
                st.warning(str(sync_res.get("detail") or sync_res))

    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button(
            "✓ Bayar berhasil (simulator)",
            type="primary",
            use_container_width=True,
            key=f"doku_sim_ok_{oid}",
            disabled=status == "PAID",
        ):
            res = simulate_mock_payment(
                order_id=oid,
                amount=amount,
                payer_name=order.get("customer_name"),
            )
            if res.get("status") == "ok":
                st.success("Pembayaran tercatat. Kembali ke Simulasi untuk lihat rekonsiliasi.")
                st.session_state.ui_nav = "simulator"
                from session_runtime import mark_data_changed

                mark_data_changed("doku_simulator_paid")
                if st.session_state.get("auto_refresh_enabled", True):
                    st.session_state._pending_agent_run = True
                    st.session_state._pending_trigger = "doku_simulator_paid"
                try:
                    del st.query_params["doku_pay"]
                except Exception:
                    pass
                st.rerun()
            else:
                st.warning(str(res.get("detail") or res))
    with col_cancel:
        if st.button("Batal", use_container_width=True, key=f"doku_sim_cancel_{oid}"):
            try:
                del st.query_params["doku_pay"]
            except Exception:
                pass
            st.session_state.ui_nav = "simulator"
            st.rerun()

    if simulator and simulator != hosted:
        st.caption(f"URL simulator: `{simulator}`")

    return True


def handle_doku_return(order_id: str) -> None:
    """After redirect from hosted DOKU checkout (?doku_return=)."""
    oid = (order_id or "").strip()
    if not oid:
        return

    sync_res = sync_doku_order_payment(oid)
    if sync_res.get("status") == "ok":
        st.success(
            f"Pembayaran untuk **{oid}** terdeteksi dari DOKU. Dashboard akan menampilkan status terbaru."
        )
    elif sync_res.get("status") == "already_paid":
        st.success(f"Pesanan **{oid}** sudah lunas.")
    elif sync_res.get("status") == "pending":
        st.warning(
            f"Anda kembali dari DOKU untuk order **{oid}**. "
            f"{sync_res.get('detail', 'Pembayaran belum terkonfirmasi.')} "
            "Buka link simulator dan klik **Cek status pembayaran DOKU**."
        )
    else:
        st.info(
            f"Anda kembali dari halaman DOKU untuk order **{oid}**. "
            "Jika sudah bayar, buka simulator (`?doku_pay=`) dan klik **Cek status pembayaran DOKU**."
        )

    st.session_state.ui_nav = "simulator"
    from session_runtime import mark_data_changed

    mark_data_changed("doku_return")
    if sync_res.get("status") == "ok" and st.session_state.get("auto_refresh_enabled", True):
        st.session_state._pending_agent_run = True
        st.session_state._pending_trigger = "doku_return_sync"
    try:
        del st.query_params["doku_return"]
    except Exception:
        pass
