"""Dashboard-style analytics for the Reports navigation page."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from dashboard import EXPORT_LABELS
from state import AgentState

_WF_PRIMARY = "#006b47"
_WF_SECONDARY = "#515f78"
_STATUS_COLORS = {
    "PAID": "#006b47",
    "PARTIALLY_PAID": "#f59e0b",
    "OVERPAID": "#0d9488",
    "UNPAID": "#ba1a1a",
    "UNKNOWN": "#64748b",
    "NEEDS_REVIEW": "#7c3aed",
}


def _idr(n: Any) -> str:
    try:
        return f"Rp {int(n):,}"
    except (TypeError, ValueError):
        return "—"


def _health_label(score: int) -> str:
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Stable"
    if score >= 40:
        return "Needs review"
    return "High risk"


def _status_chart_df(reco: list[dict[str, Any]]) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for r in reco:
        stt = str(r.get("status") or "OTHER")
        counts[stt] = counts.get(stt, 0) + 1
    if not counts:
        return pd.DataFrame({"status": ["No data"], "count": [0]})
    return pd.DataFrame(
        [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    )


def _cashflow_chart_df(cs: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metric": "Expected", "amount": int(cs.get("expected_revenue") or 0)},
            {"metric": "Collected", "amount": int(cs.get("collected_revenue") or 0)},
            {"metric": "Expenses", "amount": int(cs.get("expenses") or 0)},
            {"metric": "Net", "amount": int(cs.get("net_cash_position") or 0)},
        ]
    )


def _expense_chart_df(expenses: list[dict[str, Any]]) -> pd.DataFrame:
    if not expenses:
        return pd.DataFrame({"category": ["none"], "amount": [0]})
    agg: dict[str, int] = {}
    for e in expenses:
        cat = str(e.get("category") or "other")
        agg[cat] = agg.get(cat, 0) + int(e.get("amount") or 0)
    return pd.DataFrame(
        [{"category": k.replace("_", " ").title(), "amount": v} for k, v in agg.items()]
    )


def render_reports_analytics(state: AgentState) -> None:
    """Render full-width report analytics dashboard (Streamlit native + Altair)."""
    cs = state.cashflow_summary or {}
    hs = state.health_score or {}
    reco = state.reconciliation_results or []
    issues = state.payment_issues or []
    fr = state.financing_readiness or {}
    val = state.validation_report or {}
    merchant = state.merchant_profile or {}

    health_i = int(hs.get("score") or 0)
    coll_rate = float(cs.get("collection_rate") or 0)
    expected = int(cs.get("expected_revenue") or 0)
    collected = int(cs.get("collected_revenue") or 0)
    expenses = int(cs.get("expenses") or 0)
    net = int(cs.get("net_cash_position") or 0)
    unpaid_cnt = sum(1 for r in reco if r.get("status") in {"UNPAID", "PARTIALLY_PAID"})

    st.markdown(
        f"""
<div style="margin-bottom:1.25rem;">
  <p style="font-family:'Plus Jakarta Sans',sans-serif;font-size:1.5rem;font-weight:700;
    color:#006b47;margin:0;">Laporan Analitik Harian</p>
  <p style="color:#3e4942;margin:0.35rem 0 0 0;font-size:0.9rem;">
    {merchant.get('merchant_name', 'Warung')} · {merchant.get('city', '')} ·
    Status agen: <strong>{state.final_status or '—'}</strong>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # KPI row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Pendapatan diharapkan", _idr(expected))
    k2.metric("Terkumpul", _idr(collected), delta=f"{coll_rate:.0f}% collection")
    k3.metric("Pengeluaran", _idr(expenses))
    k4.metric("Laba bersih", _idr(net), delta="positif" if net >= 0 else "negatif")
    k5.metric("Skor kesehatan", f"{health_i}/100", delta=_health_label(health_i))
    k6.metric("Isu pembayaran", str(len(issues)), delta=f"{unpaid_cnt} order terbuka")

    st.markdown("---")

    # Charts row
    c_left, c_right = st.columns((1, 1))

    with c_left:
        st.markdown("##### Distribusi status pembayaran")
        sdf = _status_chart_df(reco)
        color_scale = alt.Scale(
            domain=sdf["status"].tolist(),
            range=[_STATUS_COLORS.get(d, "#94a3b8") for d in sdf["status"]],
        )
        chart_status = (
            alt.Chart(sdf)
            .mark_arc(innerRadius=52, outerRadius=95)
            .encode(
                theta=alt.Theta("count:Q"),
                color=alt.Color("status:N", scale=color_scale, legend=alt.Legend(title="Status")),
                tooltip=["status", "count"],
            )
            .properties(height=280)
        )
        st.altair_chart(chart_status, use_container_width=True)

    with c_right:
        st.markdown("##### Ringkasan arus kas")
        cdf = _cashflow_chart_df(cs)
        chart_cash = (
            alt.Chart(cdf)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("metric:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("amount:Q", title="IDR"),
                color=alt.Color(
                    "metric:N",
                    scale=alt.Scale(
                        domain=["Expected", "Collected", "Expenses", "Net"],
                        range=["#94a3b8", _WF_PRIMARY, "#ba1a1a", "#0d9488"],
                    ),
                    legend=None,
                ),
                tooltip=[alt.Tooltip("metric"), alt.Tooltip("amount", format=",")],
            )
            .properties(height=280)
        )
        st.altair_chart(chart_cash, use_container_width=True)

    c_exp, c_prog = st.columns((1, 1))

    with c_exp:
        st.markdown("##### Pengeluaran per kategori")
        edf = _expense_chart_df(state.expenses or [])
        chart_exp = (
            alt.Chart(edf)
            .mark_bar(color=_WF_SECONDARY)
            .encode(
                y=alt.Y("category:N", sort="-x", title=None),
                x=alt.X("amount:Q", title="IDR"),
                tooltip=["category", alt.Tooltip("amount", format=",")],
            )
            .properties(height=240)
        )
        st.altair_chart(chart_exp, use_container_width=True)

    with c_prog:
        st.markdown("##### Progress operasional")
        st.caption("Tingkat penagihan (collection rate)")
        st.progress(min(1.0, coll_rate / 100.0))
        st.caption(f"{coll_rate:.1f}% dari pendapatan yang diharapkan")

        st.caption("Skor kesehatan kasflow")
        st.progress(min(1.0, health_i / 100.0))

        val_ok = val.get("ok", False)
        checks = val.get("checks") or []
        passed = sum(1 for c in checks if c.get("passed"))
        total = len(checks) or 1
        st.caption("Kelengkapan validasi output")
        st.progress(passed / total)
        st.caption(f"{passed}/{total} pemeriksaan lulus")

    st.markdown("---")

    # Validation + financing cards
    v_col, f_col = st.columns((1, 1))

    with v_col:
        st.markdown("##### Validasi output agen")
        if checks:
            vdf = pd.DataFrame(
                [
                    {
                        "Check": str(c.get("check", "")).replace("_", " ").title(),
                        "Status": "Lulus" if c.get("passed") else "Gagal",
                    }
                    for c in checks
                ]
            )
            st.dataframe(
                vdf,
                use_container_width=True,
                hide_index=True,
                height=min(35 * len(vdf) + 38, 280),
            )
            st.metric("Validasi keseluruhan", "Lulus" if val_ok else "Perlu review")
        else:
            st.info("Jalankan agen untuk menghasilkan laporan validasi.")

    with f_col:
        st.markdown("##### Kesiapan pembiayaan")
        fin_score = int(fr.get("score") or health_i)
        st.metric("Skor kesiapan", f"{fin_score}/100", delta=_health_label(fin_score))
        narrative = fr.get("narrative") or "Narasi belum tersedia."
        st.markdown(
            f"""
<div style="background:#ecfdf5;border:1px solid #bdcac0;border-radius:8px;
padding:1rem 1.1rem;font-size:0.9rem;line-height:1.55;color:#0b1c30;">
{html.escape(narrative)}
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Reminders table
    st.markdown("##### Pengingat pembayaran (WhatsApp)")
    reminders = state.reminders or []
    if reminders:
        rdf = pd.DataFrame(
            [
                {
                    "Order": r.get("order_id"),
                    "Channel": r.get("channel", "whatsapp"),
                    "Pesan": (r.get("text") or "")[:200],
                }
                for r in reminders
            ]
        )
        st.dataframe(rdf, use_container_width=True, hide_index=True, height=220)
    else:
        st.success("Tidak ada pengingat — semua order sudah lunas atau belum dijalankan.")

    # Agent tools summary
    if state.execution_trace:
        st.markdown("##### Aktivitas agen (ringkas)")
        tdf = pd.DataFrame(
            [
                {
                    "Step": t.step_number,
                    "Tool": t.tool_called,
                    "Status": t.status.upper(),
                }
                for t in state.execution_trace
            ]
        )
        tool_counts = (
            tdf.groupby("Tool", as_index=False)
            .size()
            .rename(columns={"size": "Calls"})
            .sort_values("Calls", ascending=False)
        )
        tc1, tc2 = st.columns((1, 1))
        with tc1:
            st.dataframe(tool_counts.head(10), hide_index=True, use_container_width=True)
        with tc2:
            status_tools = (
                alt.Chart(tdf)
                .mark_bar()
                .encode(
                    x=alt.X("Status:N", title=None),
                    y=alt.Y("count():Q", title="Tool calls"),
                    color=alt.Color("Status:N", legend=None),
                )
                .properties(height=200)
            )
            st.altair_chart(status_tools, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Unduh laporan")
    paths = state.exported_files or {}
    if not paths:
        st.info("Ekspor belum tersedia — jalankan agen hingga selesai.")
    else:
        dl_cols = st.columns(3)
        idx = 0
        for fname, (title, _icon) in EXPORT_LABELS.items():
            pth = paths.get(fname)
            if not pth or not Path(pth).is_file():
                continue
            with dl_cols[idx % 3]:
                mime = (
                    "text/csv"
                    if fname.endswith(".csv")
                    else "text/markdown"
                    if fname.endswith(".md")
                    else "application/octet-stream"
                )
                st.download_button(
                    title,
                    data=Path(pth).read_bytes(),
                    file_name=fname,
                    mime=mime,
                    key=f"rpt-dash-{fname}-{id(state)}",
                    use_container_width=True,
                )
            idx += 1
