"""Dashboard-style analytics for the Reports navigation page."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from config import RuntimeConfig
from dashboard import (
    EXPORT_LABELS,
    build_action_recommendations,
    human_status,
    human_tool,
    page_stack_close_html,
    page_stack_open_html,
    recommendations_html,
    section_header_html,
    section_heading_html,
)
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


def _kpi_card(
    label: str, value: str, delta: str | None = None, *, delta_class: str = "wf-kpi-delta-neutral"
) -> str:
    delta_html = (
        f'<p class="wf-kpi-delta {delta_class}">{html.escape(delta)}</p>' if delta else ""
    )
    return f"""
  <div class="wf-kpi-card">
    <p class="wf-kpi-label">{html.escape(label)}</p>
    <p class="wf-kpi-value">{html.escape(value)}</p>
    {delta_html}
  </div>"""


def _reports_kpi_row_html(
    *,
    expected: int,
    collected: int,
    expenses: int,
    net: int,
    health_i: int,
    coll_rate: float,
    issues_count: int,
    unpaid_cnt: int,
) -> str:
    cards = [
        _kpi_card("Pendapatan diharapkan", _idr(expected)),
        _kpi_card(
            "Terkumpul",
            _idr(collected),
            delta=f"Penagihan {coll_rate:.0f}% dari target",
            delta_class="wf-kpi-delta-positive" if coll_rate >= 50 else "wf-kpi-delta-neutral",
        ),
        _kpi_card("Pengeluaran", _idr(expenses)),
        _kpi_card(
            "Laba bersih",
            _idr(net),
            delta="Laba positif" if net >= 0 else "Laba negatif",
            delta_class="wf-kpi-delta-positive" if net >= 0 else "wf-kpi-delta-warn",
        ),
        _kpi_card(
            "Skor kesehatan",
            f"{health_i}/100",
            delta=_health_label(health_i),
            delta_class=(
                "wf-kpi-delta-positive"
                if health_i >= 60
                else "wf-kpi-delta-warn"
            ),
        ),
        _kpi_card(
            "Isu pembayaran",
            str(issues_count),
            delta=f"{unpaid_cnt} pesanan belum lunas",
            delta_class="wf-kpi-delta-warn" if unpaid_cnt else "wf-kpi-delta-positive",
        ),
    ]
    return f'<div class="wf-kpi-grid">{"".join(cards)}</div>'


def _health_label(score: int) -> str:
    if score >= 80:
        return "Sangat sehat"
    if score >= 60:
        return "Cukup stabil"
    if score >= 40:
        return "Perlu ditinjau"
    return "Risiko tinggi"


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
            {"metric": "Diharapkan", "amount": int(cs.get("expected_revenue") or 0)},
            {"metric": "Terkumpul", "amount": int(cs.get("collected_revenue") or 0)},
            {"metric": "Pengeluaran", "amount": int(cs.get("expenses") or 0)},
            {"metric": "Laba bersih", "amount": int(cs.get("net_cash_position") or 0)},
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

    merchant_name = merchant.get("merchant_name") or merchant.get("name") or "Warung"
    status_human = {
        "COMPLETE": "Selesai",
        "NEEDS_REVIEW": "Perlu ditinjau",
        "ERROR": "Gagal",
    }.get(str(state.final_status or ""), state.final_status or "—")
    st.markdown(
        section_heading_html(
            "Laporan analitik harian",
            f"{merchant_name} · {merchant.get('city', '')} · Status analisis: {status_human}",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    st.markdown(
        _reports_kpi_row_html(
            expected=expected,
            collected=collected,
            expenses=expenses,
            net=net,
            health_i=health_i,
            coll_rate=coll_rate,
            issues_count=len(issues),
            unpaid_cnt=unpaid_cnt,
        ),
        unsafe_allow_html=True,
    )

    cfg = RuntimeConfig.load()
    recommendations = build_action_recommendations(state, cfg)
    if recommendations:
        st.markdown(
            section_header_html(
                "Langkah yang disarankan",
                "Prioritas perbaikan untuk isu pembayaran, skor kesehatan, dan peringatan.",
                icon="checklist",
                variant="accent",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown(recommendations_html(recommendations), unsafe_allow_html=True)

    c_left, c_right = st.columns((1, 1))

    with c_left:
        st.markdown(
            section_header_html(
                "Distribusi status pembayaran",
                "Berapa pesanan lunas, belum lunas, atau lebih bayar.",
                icon="donut_large",
                variant="default",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            sdf = _status_chart_df(reco)
            sdf["status_label"] = sdf["status"].map(
                lambda s: human_status(str(s)) if s != "No data" else s
            )
            color_scale = alt.Scale(
                domain=sdf["status_label"].tolist(),
                range=[
                    _STATUS_COLORS.get(d, "#94a3b8") for d in sdf["status"].tolist()
                ],
            )
            chart_status = (
                alt.Chart(sdf)
                .mark_arc(innerRadius=52, outerRadius=95)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color(
                        "status_label:N",
                        scale=color_scale,
                        legend=alt.Legend(title="Status"),
                    ),
                    tooltip=["status_label", "count"],
                )
                .properties(height=280)
            )
            st.altair_chart(chart_status, use_container_width=True)

    with c_right:
        st.markdown(
            section_header_html(
                "Ringkasan arus kas",
                "Omzet diharapkan, terkumpul, pengeluaran, dan laba bersih.",
                icon="account_balance",
                variant="default",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
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
                            domain=[
                                "Diharapkan",
                                "Terkumpul",
                                "Pengeluaran",
                                "Laba bersih",
                            ],
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
        st.markdown(
            section_header_html(
                "Pengeluaran per kategori",
                "Biaya operasional warung hari ini.",
                icon="shopping_cart",
                variant="muted",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
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
        st.markdown(
            section_header_html(
                "Progress operasional",
                "Penagihan, kesehatan kas, dan kelengkapan laporan.",
                icon="trending_up",
                variant="muted",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.caption("Tingkat penagihan")
            st.progress(min(1.0, coll_rate / 100.0))
            st.caption(f"{coll_rate:.1f}% dari pendapatan yang diharapkan")

            st.caption("Skor kesehatan kas")
            st.progress(min(1.0, health_i / 100.0))

            val_ok = val.get("ok", False)
            checks = val.get("checks") or []
            passed = sum(1 for c in checks if c.get("passed"))
            total = len(checks) or 1
            st.caption("Kelengkapan validasi output")
            st.progress(passed / total)
            st.caption(f"{passed}/{total} pemeriksaan lulus")

    v_col, f_col = st.columns((1, 1))

    with v_col:
        st.markdown(
            section_header_html(
                "Validasi laporan",
                "Apakah file siap diunduh dan dibagikan.",
                icon="fact_check",
                variant="default",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            if checks:
                vdf = pd.DataFrame(
                    [
                        {
                            "Pemeriksaan": str(c.get("check", ""))
                            .replace("_", " ")
                            .title(),
                            "Hasil": "Lulus" if c.get("passed") else "Gagal",
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
        st.markdown(
            section_header_html(
                "Kesiapan pembiayaan",
                "Narasi singkat untuk diskusi dengan bank.",
                icon="account_balance_wallet",
                variant="accent",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
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

    st.markdown(
        section_header_html(
            "Pengingat pembayaran",
            "Draft pesan WhatsApp untuk pelanggan yang belum lunas.",
            icon="notifications",
            variant="default",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        reminders = state.reminders or []
        if reminders:
            by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
            rdf = pd.DataFrame(
                [
                    {
                        "Pelanggan": (
                            by_order.get(str(r.get("order_id")), {}).get("customer_name")
                            or r.get("order_id")
                        ),
                        "Pesan": (r.get("text") or "")[:200],
                    }
                    for r in reminders
                ]
            )
            st.dataframe(rdf, use_container_width=True, hide_index=True, height=220)
        else:
            st.success("Tidak ada pengingat — semua pesanan sudah lunas.")

    if state.execution_trace:
        with st.expander("Ringkasan aktivitas agen (opsional)", expanded=False):
            tdf = pd.DataFrame(
                [
                    {
                        "Langkah": t.step_number,
                        "Aksi": human_tool(t.tool_called),
                        "Hasil": {"ok": "OK", "warn": "Peringatan", "error": "Gagal"}.get(
                            t.status, t.status
                        ),
                    }
                    for t in state.execution_trace[-20:]
                ]
            )
            st.dataframe(tdf, hide_index=True, use_container_width=True)

    st.markdown(
        section_header_html(
            "Unduh laporan",
            "File Markdown dan CSV siap dibagikan ke bank atau pembukuan.",
            icon="download",
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
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

    st.markdown(page_stack_close_html(), unsafe_allow_html=True)
