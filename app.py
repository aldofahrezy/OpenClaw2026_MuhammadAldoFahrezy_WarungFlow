"""
WarungFlow — Streamlit demo: state-driven agent, execution trace, exports.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from warungflow.agent_loop import decide_next_action, run_agent
from warungflow.config import RuntimeConfig

st.set_page_config(page_title="WarungFlow", layout="wide")
st.title("WarungFlow")
st.caption(
    "From messy notes to bankable reports, autonomously. "
    "WarungFlow bridges messy digital commerce and formal financial readiness for Indonesian UMKM."
)

if "state" not in st.session_state:
    st.session_state.state = None
    st.session_state.cfg = None

cfg = RuntimeConfig.load()
st.session_state.cfg = cfg

if cfg.warnings:
    for w in cfg.warnings:
        st.warning(w, icon="⚠️")

with st.sidebar:
    st.subheader("Runtime (masked)")
    for line in cfg.env_summary_masked():
        st.text(line)
    st.divider()
    if st.button("Run autonomous agent", type="primary"):
        with st.spinner("Planner + tools running…"):
            st.session_state.state = run_agent(cfg)

state = st.session_state.state

if state is None:
    st.info("Click **Run autonomous agent** in the sidebar to start the deterministic-first loop.")
    st.stop()

st.success(f"Final status: **{state.final_status}**")

st.subheader("Agent Execution Trace")
trace_rows = [
    {
        "Step": t.step_number,
        "Decision": t.agent_decision,
        "Tool": t.tool_called,
        "Input": t.input_summary,
        "Output": t.output_summary,
        "Status": t.status,
        "Time": t.timestamp,
    }
    for t in state.execution_trace
]
st.dataframe(pd.DataFrame(trace_rows), use_container_width=True, height=400)

next_act = decide_next_action(state)
st.caption(
    f"Planner `decide_next_action` → `{next_act or 'FINISH'}` "
    "(state-driven; not a fixed script)."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Reconciliation")
    if state.reconciliation_results:
        st.dataframe(pd.DataFrame(state.reconciliation_results), use_container_width=True)
    else:
        st.write("—")
with col2:
    st.subheader("Payment issues")
    if state.payment_issues:
        st.dataframe(pd.DataFrame(state.payment_issues), use_container_width=True)
    else:
        st.write("No issues detected.")

st.subheader("Cashflow & health")
c1, c2 = st.columns(2)
with c1:
    st.json(state.cashflow_summary or {})
with c2:
    st.json(state.health_score or {})

st.subheader("Exported files")
paths = state.exported_files or {}
for label, p in paths.items():
    path = Path(p)
    if path.is_file():
        st.download_button(
            label=f"Download {label}",
            data=path.read_bytes(),
            file_name=label,
            key=f"dl-{label}",
        )

st.subheader("Daily report preview")
st.markdown(state.daily_report or "_empty_", unsafe_allow_html=False)
