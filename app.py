"""
WarungFlow — dashboard UI aligned to the Tailwind reference (Plus Jakarta Sans, Material Symbols, M3-style tokens).
Reactive agent: auto-load sample data, auto-run on first open, refresh on input hash change.
"""

from __future__ import annotations

import html
import logging
import os
from pathlib import Path

import pandas as pd
import streamlit as st

logging.getLogger("streamlit").setLevel(logging.WARNING)
logging.getLogger("streamlit.watcher").setLevel(logging.ERROR)

from agents.orchestrator import decide_next_action
from config import RuntimeConfig
from dashboard import (
    EXPORT_LABELS,
    collect_review_items,
    dashboard_css,
    dashboard_font_links,
    human_status,
    human_tool,
    hint_box_html,
    page_intro_html,
    page_stack_close_html,
    page_stack_open_html,
    section_header_html,
    reconciliation_rows_from_state,
    reconciliation_summary_html,
    reconciliation_table_html,
    payment_issues_rows_from_state,
    payment_issues_table_html,
    build_action_recommendations,
    recommendations_html,
    review_guidance_html,
    section_heading_html,
    stat_cards_html,
    system_status_banner_html,
    trace_timeline_html,
)
from dashboard_reports import render_reports_analytics
from dashboard_catalogue import render_product_catalogue_page
from dashboard_doku_checkout import handle_doku_return, render_doku_checkout_page
from dashboard_simulator import render_simulator_page
from tools.parsers import strip_internal_meta
from session_runtime import (
    get_agent_state,
    init_session_defaults,
    load_sample_data_into_session,
    mark_data_changed,
    process_pending_agent_run,
    reset_bot_demo_history,
    save_ui_session_snapshot,
    schedule_initial_run,
)
from tools.bot_service import simulate_mock_payment

st.set_page_config(
    page_title="WarungFlow - Main Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _is_production_ui() -> bool:
    return os.getenv("WARUNGFLOW_ENV", "").strip().lower() in {"production", "prod"}


def _handle_mock_payment_deep_link() -> None:
    """Process ?mock_pay=ORD-BOT-xxx from WhatsApp mock payment links (works on Streamlit deploy)."""
    oid = (st.query_params.get("mock_pay") or "").strip()
    if not oid:
        return
    done_key = f"_mock_pay_handled_{oid}"
    if st.session_state.get(done_key):
        return

    res = simulate_mock_payment(order_id=oid)
    st.session_state[done_key] = True
    st.session_state.ui_nav = "simulator"
    st.session_state._mock_pay_flash = {**res, "order_id": oid}

    if res.get("status") == "ok":
        mark_data_changed("mock_pay_deep_link")
        if st.session_state.get("auto_refresh_enabled", True):
            st.session_state._pending_agent_run = True
            st.session_state._pending_trigger = "mock_payment"

    try:
        del st.query_params["mock_pay"]
    except Exception:
        pass


def _inject_assets() -> None:
    st.markdown(
        dashboard_font_links() + dashboard_css(),
        unsafe_allow_html=True,
    )


init_session_defaults()
load_sample_data_into_session()
_handle_mock_payment_deep_link()

_doku_pay_oid = (st.query_params.get("doku_pay") or "").strip()
if _doku_pay_oid:
    _inject_assets()
    if render_doku_checkout_page(_doku_pay_oid):
        st.stop()

_doku_return_oid = (st.query_params.get("doku_return") or "").strip()
if _doku_return_oid:
    handle_doku_return(_doku_return_oid)

schedule_initial_run()

if "_bootstrapped" not in st.session_state or not st.session_state._bootstrapped:
    st.session_state._bootstrapped = True
    st.session_state._last_payment_mode_choice = st.session_state.payment_mode_choice

prod_ui = _is_production_ui()
_inject_assets()

cfg = RuntimeConfig.load(
    payment_mode_choice=st.session_state.get("payment_mode_choice", "mock")
)

# ----- Sidebar -----
with st.sidebar:
    st.markdown(
        """
<div class="wf-nav-brand" style="padding:0 0.25rem 1rem 0.25rem;">
  <div class="wf-logo"><span class="wf-ms" style="color:#fff;font-size:18px;">storefront</span></div>
  <div>
    <p class="wf-brand-title">WarungFlow</p>
    <p class="wf-brand-sub">Partner keuangan UMKM</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    nav = st.session_state.ui_nav
    for key, label in (
        ("dashboard", "Beranda"),
        ("simulator", "Simulasi"),
        ("catalogue", "Katalog"),
        ("trace", "Jejak agen"),
        ("reconciliation", "Rekonsiliasi"),
        ("reports", "Laporan"),
    ):
        if st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if nav == key else "secondary",
        ):
            st.session_state.ui_nav = key
            save_ui_session_snapshot()
            st.rerun()

    st.markdown("---")
    if st.button(
        "Reset riwayat demo",
        key="sidebar_reset_bot_history",
        use_container_width=True,
        help="Hapus chat WhatsApp simulasi, pesanan bot, dan pembayaran mock di runtime/.",
    ):
        reset_bot_demo_history()
        save_ui_session_snapshot()
        st.rerun()


# Reactive agent run (initial load, data change, manual refresh)
if st.session_state.get("_pending_agent_run"):
    trigger = str(st.session_state.get("_pending_trigger") or "refresh")

    def _on_step(step: object) -> None:
        icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(getattr(step, "status", ""), "•")
        tool_label = human_tool(str(getattr(step, "tool_called", "") or ""))
        st.write(
            f"{icon} Langkah {getattr(step, 'step_number', '?')} · "
            f"**{tool_label}** — {getattr(step, 'output_summary', '')}"
        )

    with st.status(f"WarungFlow analyzing · {trigger}", expanded=True) as agent_status:
        ran = process_pending_agent_run(cfg, on_step=_on_step)
        if ran:
            final = get_agent_state()
            run_id = int(st.session_state.get("run_id") or 0)
            label = (final.final_status if final else None) or "COMPLETE"
            agent_status.update(label=f"Run {run_id} complete · {label}", state="complete")

state = get_agent_state()
ui_status = str(st.session_state.get("ui_status") or "Fresh")
ui_detail = str(st.session_state.get("ui_status_detail") or "")
pending_run = bool(st.session_state.get("_pending_agent_run"))
data_stale = bool(st.session_state.get("data_stale")) and not pending_run

h_left, h_mid, h_right = st.columns([2, 2, 2])
with h_left:
    st.markdown('<p class="wf-top-title">WarungFlow</p>', unsafe_allow_html=True)
with h_mid:
    if st.session_state.get("_pending_agent_run"):
        status_label = "Sedang berjalan"
    elif state:
        status_label = {
            "COMPLETE": "Selesai",
            "NEEDS_REVIEW": "Perlu ditinjau",
            "ERROR": "Gagal",
        }.get(str(state.final_status or ""), state.final_status or "Aktif")
    else:
        status_label = ui_status
    st.markdown(
        f"""
<div class="wf-pill"><span class="wf-pill-dot"></span>
<span>Status agen: {html.escape(status_label)}</span></div>
""",
        unsafe_allow_html=True,
    )
with h_right:
    run_n = int(st.session_state.get("run_id") or 0)
    st.caption(f"Analisis ke-{run_n}" if run_n else "Menunggu analisis pertama")

st.markdown(
    """
<div style="display:flex;justify-content:flex-end;gap:0.5rem;align-items:center;padding-bottom:0.65rem;margin-bottom:0.75rem;border-bottom:1px solid #bdcac0;">
<span class="wf-ms" style="color:#3e4942;">account_tree</span>
<span class="wf-ms" style="color:#3e4942;">payments</span>
</div>
""",
    unsafe_allow_html=True,
)

if cfg.warnings:
    for w in cfg.warnings:
        st.warning(w, icon="⚠️")

if cfg.warungflow_env == "production":
    st.info(
        "Demo live · OpenClaw2026_MuhammadAldoFahrezy — "
        "data contoh dimuat dan analisis berjalan otomatis.",
        icon="🌐",
    )

_mock_flash = st.session_state.pop("_mock_pay_flash", None)
if _mock_flash:
    status = _mock_flash.get("status")
    oid = _mock_flash.get("order_id") or "pesanan"
    if status == "ok":
        ps = _mock_flash.get("payment_status", "PAID")
        st.success(
            f"Pembayaran simulasi berhasil untuk order terkait — status **{ps}**. "
            "Rekonsiliasi di Beranda akan diperbarui.",
            icon="✅",
        )
    elif status == "idempotent_skip":
        st.info("Pembayaran ini sudah pernah dicatat.", icon="ℹ️")
    else:
        st.warning(
            f"Pembayaran gagal: {_mock_flash.get('detail', status)}",
            icon="⚠️",
        )

st.markdown(
    system_status_banner_html(
        cfg, state, ui_status=ui_status, ui_detail=ui_detail, data_stale=data_stale
    ),
    unsafe_allow_html=True,
)

if state and (
    state.final_status in {"NEEDS_REVIEW", "ERROR"}
    or state.errors
):
    st.markdown(review_guidance_html(state), unsafe_allow_html=True)
    review = collect_review_items(state)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Refresh analisis", key="review_refresh", use_container_width=True):
            st.session_state._pending_agent_run = True
            st.session_state._pending_trigger = "review_refresh"
            st.rerun()
    with c2:
        if st.button("Buka Simulasi", key="review_simulator", use_container_width=True):
            st.session_state.ui_nav = "simulator"
            st.rerun()
    with c3:
        if st.button("Buka Katalog", key="review_catalogue", use_container_width=True):
            st.session_state.ui_nav = "catalogue"
            st.rerun()
    if review.get("reasons"):
        st.caption("Ringkasan: " + " · ".join(review["reasons"][:2]))

if data_stale and not st.session_state.get("auto_refresh_enabled", True):
    st.warning(
        "Data berubah tetapi perbarui otomatis dimatikan. Aktifkan toggle di **Simulasi** "
        "atau klik **Paksa refresh analisis**.",
        icon="🔄",
    )

if state is None:
    st.markdown(
        stat_cards_html(health_score=0, collection_rate=0.0),
        unsafe_allow_html=True,
    )
    empty_stack = f"""
<div class="wf-dashboard-stack">
  <div class="wf-panel">
    <div class="wf-panel-head"><h3 class="wf-panel-title">Rekonsiliasi pembayaran</h3></div>
    {reconciliation_table_html([])}
  </div>
  <div class="wf-panel wf-panel-trace">
    <div class="wf-panel-head"><h3 class="wf-panel-title">Jejak eksekusi agen</h3></div>
    {trace_timeline_html([])}
  </div>
</div>
"""
    st.markdown(empty_stack, unsafe_allow_html=True)
    if not st.session_state.get("has_run") and not st.session_state.get("_pending_agent_run"):
        st.info("Memulai analisis otomatis dengan data contoh Warung Bu Sari…")
    st.stop()

if state.errors:
    st.error(
        "Analisis berhenti lebih awal — lihat kotak **Apa yang perlu Anda lakukan?** di atas, "
        "lalu klik **Refresh analisis**."
    )

cs = state.cashflow_summary or {}
hs = state.health_score or {}
reco = state.reconciliation_results or []
issues = state.payment_issues or []
health_i = int(hs.get("score") or 0)
coll_pct = float(cs.get("collection_rate") or 0.0)

nav = st.session_state.ui_nav

if nav == "dashboard":
    st.markdown(
        page_intro_html(
            "Ringkasan hari ini",
            "Status pembayaran pelanggan Warung Bu Sari — sisa tagihan dan kelebihan bayar ditampilkan per pesanan.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    st.markdown(stat_cards_html(health_i, coll_pct), unsafe_allow_html=True)
    recs = build_action_recommendations(state, cfg)
    if recs and (issues or health_i < 80 or cfg.warnings):
        st.markdown(
            section_header_html(
                "Langkah yang disarankan",
                "Tindakan untuk meningkatkan skor atau menyelesaikan isu pembayaran.",
                icon="checklist",
                variant="accent",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="wf-panel" style="border-radius:0 0 12px 12px;margin-bottom:0;">{recommendations_html(recs)}</div>',
            unsafe_allow_html=True,
        )
    rows = reconciliation_rows_from_state(state)
    reco_html = reconciliation_table_html(rows)
    trace_html = trace_timeline_html(state.execution_trace)

    st.markdown(
        section_header_html(
            "Rekonsiliasi pembayaran",
            "Tagihan vs pembayaran masuk hari ini.",
            icon="payments",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="wf-panel" style="border-radius:0 0 12px 12px;margin-bottom:0;">{reco_html}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        section_header_html(
            "Unduh laporan",
            "File siap dibagikan ke bank atau pembukuan.",
            icon="download",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    paths = state.exported_files or {}
    cards = []
    for fname, (title, icon) in EXPORT_LABELS.items():
        p = paths.get(fname)
        cards.append((fname, title, icon, p))
    with st.container(border=True):
        ec1, ec2, ec3 = st.columns(3)
        cols = [ec1, ec2, ec3]
        for i, (fname, title, icon, pth) in enumerate(cards):
            with cols[i % 3]:
                st.markdown(
                    f"""
<div class="wf-export-card">
  <div class="wf-export-head">
    <span class="wf-ms text-primary" style="color:#006b47;">{html.escape(icon)}</span>
    <h4>{html.escape(title)}</h4>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )
                path = Path(pth) if pth else None
                if path and path.is_file():
                    mime = (
                        "text/csv"
                        if fname.endswith(".csv")
                        else "text/markdown"
                        if fname.endswith(".md")
                        else "application/octet-stream"
                    )
                    ext = "CSV" if fname.endswith(".csv") else "MD"
                    st.download_button(
                        f"Unduh .{ext}",
                        data=path.read_bytes(),
                        file_name=fname,
                        mime=mime,
                        key=f"ex-{fname}-{st.session_state.run_token}",
                        use_container_width=True,
                    )
                else:
                    st.caption("Belum dibuat")

    st.markdown(
        section_header_html(
            "Jejak eksekusi agen",
            "Langkah otomatis pada analisis terakhir (ringkasan).",
            icon="timeline",
            variant="muted",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="wf-panel wf-panel-trace" style="border-radius:0 0 12px 12px;">{trace_html}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(page_stack_close_html(), unsafe_allow_html=True)

elif nav == "trace":
    st.markdown(
        page_intro_html(
            "Jejak eksekusi agen",
            "Ringkasan langkah yang dijalankan WarungFlow — tanpa istilah teknis.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    st.markdown(
        section_header_html(
            "Riwayat langkah",
            "Urutan keputusan agen pada setiap analisis.",
            icon="timeline",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        df_trace = pd.DataFrame(
            [
                {
                    "Analisis": t.run_id,
                    "Langkah": t.step_number,
                    "Aksi": human_tool(t.tool_called),
                    "Ringkasan": (t.output_summary or "")[:120],
                    "Hasil": {"ok": "OK", "warn": "Peringatan", "error": "Gagal"}.get(
                        t.status, t.status
                    ),
                }
                for t in state.execution_trace
            ]
        )
        st.dataframe(df_trace, use_container_width=True, height=560, hide_index=True)
    st.markdown(page_stack_close_html(), unsafe_allow_html=True)

elif nav == "reconciliation":
    st.markdown(
        page_intro_html(
            "Rekonsiliasi pembayaran",
            "Cocokkan pesanan WhatsApp dengan mutasi QRIS/transfer — tanpa ID teknis, fokus nama pelanggan dan nominal.",
        ),
        unsafe_allow_html=True,
    )
    if reco:
        st.markdown(page_stack_open_html(), unsafe_allow_html=True)
        st.markdown(reconciliation_summary_html(state), unsafe_allow_html=True)
        recs_reco = build_action_recommendations(state, cfg)
        if recs_reco:
            st.markdown(
                section_header_html(
                    "Langkah yang disarankan",
                    "Cara menyelesaikan isu dan meningkatkan skor.",
                    icon="checklist",
                    variant="accent",
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="wf-panel" style="border-radius:0 0 12px 12px;margin-bottom:1rem;">{recommendations_html(recs_reco)}</div>',
                unsafe_allow_html=True,
            )
        all_rows = reconciliation_rows_from_state(state)
        st.markdown(
            section_header_html(
                "Semua pesanan",
                "Tagihan vs pembayaran masuk; sisa atau kelebihan ditampilkan otomatis.",
                icon="table_chart",
                variant="accent",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="wf-panel" style="border-radius:0 0 12px 12px;">{reconciliation_table_html(all_rows, show_order_id=False)}</div>',
            unsafe_allow_html=True,
        )
        issue_rows = payment_issues_rows_from_state(state)
        st.markdown(
            section_header_html(
                "Perlu perhatian",
                f"{len(issue_rows)} pesanan butuh tindak lanjut.",
                icon="warning",
                variant="default",
            ),
            unsafe_allow_html=True,
        )
        if issue_rows:
            st.markdown(
                f'<div class="wf-panel" style="border-radius:0 0 12px 12px;">{payment_issues_table_html(issue_rows)}</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.container(border=True):
                st.success("Semua pesanan sudah lunas — tidak ada masalah pembayaran.")
        st.markdown(page_stack_close_html(), unsafe_allow_html=True)
        with st.expander("Detail teknis (opsional)", expanded=False):
            st.caption("Untuk debugging: ID sistem dan skor mentah.")
            tech_reco = []
            by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
            for r in reco:
                oid = str(r.get("order_id"))
                o = by_order.get(oid, {})
                tech_reco.append(
                    {
                        "Pelanggan": strip_internal_meta(
                            str(o.get("customer_name") or "—")
                        ),
                        "Order ID": oid,
                        "Status": human_status(str(r.get("status") or "")),
                        "Terbayar (Rp)": r.get("matched_amount"),
                        "ID mutasi": ", ".join(r.get("matched_payment_ids") or [])
                        or "—",
                        "Keyakinan (%)": r.get("confidence"),
                        "Catatan sistem": r.get("notes") or "—",
                    }
                )
            st.dataframe(pd.DataFrame(tech_reco), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada hasil rekonsiliasi. Jalankan analisis dari Dashboard terlebih dahulu.")

elif nav == "catalogue":
    render_product_catalogue_page()

elif nav == "simulator":
    render_simulator_page(cfg, prod_ui)

elif nav == "reports":
    render_reports_analytics(state)
