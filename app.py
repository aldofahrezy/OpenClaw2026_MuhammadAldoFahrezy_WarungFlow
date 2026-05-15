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
    dashboard_css,
    dashboard_font_links,
    reconciliation_rows_from_state,
    reconciliation_table_html,
    stat_cards_html,
    system_status_banner_html,
    trace_timeline_html,
)
from dashboard_reports import render_reports_analytics
from live_sandbox import (
    add_matching_payment_demo,
    add_partial_payment_demo,
    add_unpaid_order_demo,
    append_payment_transaction,
    append_whatsapp_order,
    simulate_doku_payment_success,
)
from session_runtime import (
    get_agent_state,
    init_session_defaults,
    load_sample_data_into_session,
    mark_data_changed,
    process_pending_agent_run,
    reset_demo_session,
    schedule_initial_run,
)

st.set_page_config(
    page_title="WarungFlow - Main Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _is_production_ui() -> bool:
    return os.getenv("WARUNGFLOW_ENV", "").strip().lower() in {"production", "prod"}


def _inject_assets() -> None:
    st.markdown(
        dashboard_font_links() + dashboard_css(),
        unsafe_allow_html=True,
    )


init_session_defaults()
load_sample_data_into_session()
schedule_initial_run()

if "_bootstrapped" not in st.session_state or not st.session_state._bootstrapped:
    st.session_state._bootstrapped = True
    st.session_state._last_payment_mode_choice = st.session_state.payment_mode_choice

prod_ui = _is_production_ui()
_inject_assets()

cfg = RuntimeConfig.load()
os.environ["PAYMENT_MODE"] = st.session_state.payment_mode_choice

# ----- Sidebar -----
with st.sidebar:
    st.markdown(
        """
<div class="wf-nav-brand" style="padding:0 0.25rem 1rem 0.25rem;">
  <div class="wf-logo"><span class="wf-ms" style="color:#fff;font-size:18px;">storefront</span></div>
  <div>
    <p class="wf-brand-title">WarungFlow</p>
    <p class="wf-brand-sub">Reliable Partner</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    nav = st.session_state.ui_nav
    for key, label in (
        ("dashboard", "Dashboard"),
        ("trace", "Agent Trace"),
        ("reconciliation", "Reconciliation"),
        ("reports", "Reports"),
    ):
        if st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if nav == key else "secondary",
        ):
            st.session_state.ui_nav = key
            st.rerun()

    st.markdown("---")
    st.session_state.auto_refresh_enabled = st.toggle(
        "Auto-refresh on data change",
        value=bool(st.session_state.get("auto_refresh_enabled", True)),
        key="wf_auto_refresh",
    )
    if st.button("Force Refresh Analysis", use_container_width=True, key="wf_force_refresh"):
        st.session_state._pending_agent_run = True
        st.session_state._pending_trigger = "manual_refresh"
        st.session_state.ui_status = "Auto-refreshing"
        st.session_state.ui_status_detail = "Manual refresh"
        st.rerun()
    if st.button("Reset Demo", use_container_width=True, key="wf_reset_demo"):
        reset_demo_session()
        st.rerun()

    st.markdown('<div class="wf-help-btn-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
<a href="#" style="display:flex;align-items:center;justify-content:center;gap:0.35rem;
padding:0.45rem 0.75rem;border:1px solid #bdcac0;border-radius:0.125rem;text-decoration:none;
color:#006b47;font-size:0.75rem;font-weight:600;">Help Center</a>
""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    agent_preview = get_agent_state()
    with st.expander("Merchant Profile", expanded=False):
        profile = None
        if agent_preview and agent_preview.merchant_profile:
            profile = agent_preview.merchant_profile
        elif st.session_state.merchant_profile:
            profile = st.session_state.merchant_profile
        if profile:
            st.markdown(f"**Store:** {profile.get('merchant_name', 'N/A')}")
            st.markdown(f"**Owner:** {profile.get('owner_name', 'N/A')}")
            st.markdown(f"**Location:** {profile.get('city', 'N/A')}")
            st.markdown(f"**Category:** {profile.get('business_type', 'N/A')}")
            methods = ", ".join(profile.get("payment_methods", []))
            st.markdown(f"**Payments:** {methods}")
            st.markdown(f"**Goal:** {profile.get('financing_goal', 'N/A')}")
        else:
            st.caption("Sample data loads automatically on first open.")

    st.markdown("**Payment mode**")
    pay_choice = st.selectbox(
        "Payment mode",
        options=["mock", "doku_sandbox"],
        index=0 if st.session_state.payment_mode_choice == "mock" else 1,
        format_func=lambda x: "Mock Mode" if x == "mock" else "DOKU Sandbox Mode",
        label_visibility="collapsed",
        key="wf_payment_mode_select",
    )
    prev_pay = st.session_state.get("_last_payment_mode_choice")
    st.session_state.payment_mode_choice = pay_choice
    os.environ["PAYMENT_MODE"] = pay_choice
    if prev_pay is not None and pay_choice != prev_pay:
        st.session_state._last_payment_mode_choice = pay_choice
        mark_data_changed("payment_mode_change")
    else:
        st.session_state._last_payment_mode_choice = pay_choice

    cfg = RuntimeConfig.load()
    if prod_ui:
        st.caption(
            f"{cfg.warungflow_env} · LLM {cfg.llm_mode} · Pay {cfg.payment_mode}"
        )
    else:
        with st.expander("Environment (masked)", expanded=False):
            for line in cfg.env_summary_masked():
                st.code(line, language="text")
            if cfg.warnings:
                for w in cfg.warnings:
                    st.warning(w)

    with st.expander("Live Data Sandbox", expanded=False):
        st.caption("Add data — agent re-runs when auto-refresh is on.")
        wa_msg = st.text_area(
            "WhatsApp order",
            placeholder="Mbak, nasi goreng 2 total 44000, bayar nanti malam - Kevin",
            height=72,
            key="sandbox_wa_order",
        )
        if st.button("Add order", key="sandbox_add_order", use_container_width=True):
            if append_whatsapp_order(wa_msg):
                st.success("Order added.")
            else:
                st.warning("Empty or duplicate order.")
            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            pay_name = st.text_input("Payer", value="Kevin", key="sandbox_payer")
            pay_amt = st.number_input(
                "Amount (IDR)", min_value=0, value=44000, step=1000, key="sandbox_amt"
            )
        with c2:
            pay_method = st.selectbox(
                "Method", ["QRIS", "transfer", "cash"], key="sandbox_method"
            )
            pay_ref = st.text_input(
                "Reference", value="nasi goreng Kevin", key="sandbox_ref"
            )
        if st.button("Add payment", key="sandbox_add_pay", use_container_width=True):
            if append_payment_transaction(
                pay_name, int(pay_amt), pay_method, pay_ref
            ):
                st.success("Payment added.")
            else:
                st.warning("Duplicate payment skipped.")
            st.rerun()

        st.markdown("**Quick demo**")
        if st.button("Kevin unpaid order", key="demo_kevin_order", use_container_width=True):
            add_unpaid_order_demo()
            st.rerun()
        if st.button("Kevin matching payment", key="demo_kevin_pay", use_container_width=True):
            add_matching_payment_demo()
            st.rerun()
        if st.button("Partial payment", key="demo_partial", use_container_width=True):
            add_partial_payment_demo()
            st.rerun()
        if st.button("Simulate DOKU webhook", key="demo_webhook", use_container_width=True):
            result = simulate_doku_payment_success()
            st.caption(result)
            st.rerun()

cfg = RuntimeConfig.load()

# Reactive agent run (initial load, data change, manual refresh)
if st.session_state.get("_pending_agent_run"):
    trigger = str(st.session_state.get("_pending_trigger") or "refresh")

    def _on_step(step: object) -> None:
        icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(getattr(step, "status", ""), "•")
        st.write(
            f"{icon} **Run {getattr(step, 'run_id', '?')} · Step {getattr(step, 'step_number', '?')}** · "
            f"`{getattr(step, 'tool_called', '')}` — {getattr(step, 'output_summary', '')}"
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
data_stale = bool(st.session_state.get("data_stale"))

h_left, h_mid, h_right = st.columns([2, 2, 2])
with h_left:
    st.markdown('<p class="wf-top-title">WarungFlow</p>', unsafe_allow_html=True)
with h_mid:
    if st.session_state.get("_pending_agent_run"):
        status_label = "Running"
    elif state:
        status_label = state.final_status or "Active"
    else:
        status_label = ui_status
    st.markdown(
        f"""
<div class="wf-pill"><span class="wf-pill-dot"></span>
<span>Agent Status: {html.escape(status_label)}</span></div>
""",
        unsafe_allow_html=True,
    )
with h_right:
    run_n = int(st.session_state.get("run_id") or 0)
    st.caption(f"Run #{run_n}" if run_n else "Run pending")

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
        "Live demo · OpenClaw2026_MuhammadAldoFahrezy — "
        "sample data loads and analysis runs automatically.",
        icon="🌐",
    )

st.markdown(
    system_status_banner_html(
        cfg, state, ui_status=ui_status, ui_detail=ui_detail, data_stale=data_stale
    ),
    unsafe_allow_html=True,
)

if data_stale and not st.session_state.get("_pending_agent_run"):
    st.warning(
        "Input data changed with auto-refresh off. Use **Force Refresh Analysis** in the sidebar.",
        icon="🔄",
    )

if state is None:
    st.markdown(
        stat_cards_html(health_score=0, collection_rate=0.0),
        unsafe_allow_html=True,
    )
    empty_grid = f"""
<div class="wf-main-grid">
  <div class="wf-panel">
    <div class="wf-panel-head"><h3 class="wf-panel-title">Payment Reconciliation</h3></div>
    {reconciliation_table_html([])}
  </div>
  <div class="wf-panel">
    <div class="wf-panel-head"><h3 class="wf-panel-title">Agent Execution Trace</h3></div>
    {trace_timeline_html([])}
  </div>
</div>
"""
    st.markdown(empty_grid, unsafe_allow_html=True)
    if not st.session_state.get("has_run") and not st.session_state.get("_pending_agent_run"):
        st.info("Starting autonomous analysis with sample Warung Bu Sari data…")
    st.stop()

if state.errors:
    st.error("Some steps completed with warnings — review before trusting exports.")
    for err in state.errors[:10]:
        st.text((err[:400] + "…") if len(err) > 400 else err)

cs = state.cashflow_summary or {}
hs = state.health_score or {}
reco = state.reconciliation_results or []
issues = state.payment_issues or []
health_i = int(hs.get("score") or 0)
coll_pct = float(cs.get("collection_rate") or 0.0)

nav = st.session_state.ui_nav

if nav == "dashboard":
    st.markdown(stat_cards_html(health_i, coll_pct), unsafe_allow_html=True)
    rows = reconciliation_rows_from_state(state)
    reco_html = reconciliation_table_html(rows)
    trace_html = trace_timeline_html(state.execution_trace)
    st.markdown(
        f"""
<div class="wf-main-grid">
  <div class="wf-panel">
    <div class="wf-panel-head">
      <h3 class="wf-panel-title">Payment Reconciliation</h3>
    </div>
    {reco_html}
  </div>
  <div class="wf-panel">
    <div class="wf-panel-head">
      <h3 class="wf-panel-title">Agent Execution Trace</h3>
    </div>
    {trace_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<h3 class="wf-export-title">Export Reports</h3>', unsafe_allow_html=True)
    paths = state.exported_files or {}
    cards = []
    for fname, (title, icon) in EXPORT_LABELS.items():
        p = paths.get(fname)
        cards.append((fname, title, icon, p))
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
                    f"Download .{ext}",
                    data=path.read_bytes(),
                    file_name=fname,
                    mime=mime,
                    key=f"ex-{fname}-{st.session_state.run_token}",
                    use_container_width=True,
                )
            else:
                st.caption("Not generated")

elif nav == "trace":
    st.subheader("Full agent trace")
    df_trace = pd.DataFrame(
        [
            {
                "Run": t.run_id,
                "Step": t.step_number,
                "Decision": t.agent_decision,
                "Tool": t.tool_called,
                "Input": t.input_summary,
                "Output": t.output_summary,
                "Status": t.status,
                "Time (UTC)": t.timestamp,
            }
            for t in state.execution_trace
        ]
    )
    st.dataframe(df_trace, use_container_width=True, height=560, hide_index=True)
    nxt = decide_next_action(state)
    with st.expander("Planner state (technical)", expanded=False):
        st.code(f"decide_next_action → {nxt or 'FINISH'}")

elif nav == "reconciliation":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Reconciliation")
        if reco:
            st.dataframe(pd.DataFrame(reco), use_container_width=True, height=420, hide_index=True)
        else:
            st.write("—")
    with c2:
        st.subheader("Payment issues")
        if issues:
            st.dataframe(pd.DataFrame(issues), use_container_width=True, height=420, hide_index=True)
        else:
            st.success("No payment issues flagged.")

elif nav == "reports":
    render_reports_analytics(state)
