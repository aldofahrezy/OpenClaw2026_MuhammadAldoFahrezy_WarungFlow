"""
WarungFlow — dashboard UI aligned to the Tailwind reference (Plus Jakarta Sans, Material Symbols, M3-style tokens).
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

from agents.orchestrator import decide_next_action, run_agent
from config import RuntimeConfig
from dashboard import (
    EXPORT_LABELS,
    dashboard_css,
    dashboard_font_links,
    mock_mode_banner_html,
    reconciliation_rows_from_state,
    reconciliation_table_html,
    stat_cards_html,
    trace_timeline_html,
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


# --- session ---
if "state" not in st.session_state:
    st.session_state.state = None
if "run_token" not in st.session_state:
    st.session_state.run_token = 0
if "ui_nav" not in st.session_state:
    st.session_state.ui_nav = "dashboard"

cfg = RuntimeConfig.load()
prod_ui = _is_production_ui()
state = st.session_state.state

_inject_assets()

# ----- Sidebar (matches reference left rail) -----
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
    if st.button(
        "Dashboard",
        key="nav_dashboard",
        use_container_width=True,
        type="primary" if nav == "dashboard" else "secondary",
    ):
        st.session_state.ui_nav = "dashboard"
        st.rerun()
    if st.button(
        "Agent Trace",
        key="nav_trace",
        use_container_width=True,
        type="primary" if nav == "trace" else "secondary",
    ):
        st.session_state.ui_nav = "trace"
        st.rerun()
    if st.button(
        "Reconciliation",
        key="nav_reco",
        use_container_width=True,
        type="primary" if nav == "reconciliation" else "secondary",
    ):
        st.session_state.ui_nav = "reconciliation"
        st.rerun()
    if st.button(
        "Reports",
        key="nav_reports",
        use_container_width=True,
        type="primary" if nav == "reports" else "secondary",
    ):
        st.session_state.ui_nav = "reports"
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

    with st.expander("Merchant Profile", expanded=False):
        if state and state.merchant_profile:
            st.json(state.merchant_profile)
        else:
            st.caption("Run the agent to load `data/merchant_profile.json`.")

    if prod_ui:
        st.caption(
            f"{cfg.warungflow_env} · LLM {cfg.llm_mode} · Pay {cfg.payment_mode}"
        )
    else:
        with st.expander("Environment (masked)", expanded=False):
            for line in cfg.env_summary_masked():
                st.code(line, language="text")

# ----- Main: top app bar -----
h_left, h_mid, h_right = st.columns([2, 2, 2])
with h_left:
    st.markdown('<p class="wf-top-title">WarungFlow</p>', unsafe_allow_html=True)
with h_mid:
    status_label = "Active" if state else "Idle"
    st.markdown(
        f"""
<div class="wf-pill"><span class="wf-pill-dot"></span>
<span>Agent Status: {html.escape(status_label)}</span></div>
""",
        unsafe_allow_html=True,
    )
with h_right:
    run = st.button("Run Agent", type="primary", use_container_width=True, key="wf_run_agent")
    if run:
        with st.spinner("Running planner and tools…"):
            st.session_state.state = run_agent(cfg)
            st.session_state.run_token += 1
        st.rerun()

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

# ----- Dashboard body -----
st.markdown(mock_mode_banner_html(cfg), unsafe_allow_html=True)

if state is None:
    st.markdown(
        stat_cards_html(health_score=0, collection_rate=0.0),
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="wf-main-grid">
<div class="wf-panel">
  <div class="wf-panel-head"><h3 class="wf-panel-title">Payment Reconciliation</h3></div>
"""
        + reconciliation_table_html([])
        + """</div>
<div class="wf-panel">
  <div class="wf-panel-head"><h3 class="wf-panel-title">Agent Execution Trace</h3></div>
"""
        + trace_timeline_html([])
        + """</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info("Click **Run Agent** in the header to execute the autonomous workflow and populate this dashboard.")
    st.stop()

# Errors
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
    fr = state.financing_readiness or {}
    st.markdown("### Financing readiness")
    st.markdown(fr.get("narrative") or "_—_")
    st.markdown("### Daily report")
    st.markdown(state.daily_report or "_—_")
    st.markdown("### Validation")
    st.json(state.validation_report or {})
    st.markdown("### Downloads")
    paths = state.exported_files or {}
    if not paths:
        st.info("No exports.")
    else:
        n = 0
        for label in sorted(paths.keys()):
            path = Path(paths[label])
            if not path.is_file():
                continue
            mime = (
                "text/csv"
                if label.endswith(".csv")
                else "text/markdown"
                if label.endswith(".md")
                else "application/octet-stream"
            )
            st.download_button(
                label=f"Download {label}",
                data=path.read_bytes(),
                file_name=label,
                mime=mime,
                key=f"rpt-{label}-{st.session_state.run_token}",
            )
            n += 1
