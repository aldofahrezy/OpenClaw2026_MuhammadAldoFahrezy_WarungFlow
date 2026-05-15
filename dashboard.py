"""WarungFlow dashboard: design tokens + HTML fragments."""

from __future__ import annotations

import html
from typing import Any

from config import RuntimeConfig
from state import AgentState, ExecutionStep


def dashboard_font_links() -> str:
    return """
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/>
"""


def dashboard_css() -> str:
    return """
<style>
:root {
  --wf-primary: #006b47;
  --wf-on-primary: #ffffff;
  --wf-bg: #f8f9ff;
  --wf-surface: #ffffff;
  --wf-surface-low: #eff4ff;
  --wf-surface-container: #e5eeff;
  --wf-on-surface: #0b1c30;
  --wf-on-surface-variant: #3e4942;
  --wf-outline-variant: #bdcac0;
  --wf-secondary: #515f78;
  --wf-error: #ba1a1a;
  --wf-error-container: #ffdad6;
  --wf-on-error-container: #93000a;
  --wf-warn-container: #fef3c7;
  --wf-on-warn: #92400e;
  --wf-ok-container: #d1fae5;
  --wf-on-ok: #065f46;
  --wf-primary-container: #00875a;
  --wf-radius: 0.25rem;
  --wf-radius-lg: 0.5rem;
}
html, body, [data-testid="stAppViewContainer"] {
  font-family: "Inter", system-ui, sans-serif;
  color: var(--wf-on-surface);
}
[data-testid="stAppViewContainer"] > .main { background: var(--wf-bg); }
[data-testid="stHeader"] { background: var(--wf-surface); }
[data-testid="stSidebar"] {
  background-color: #ffffff !important;
  border-right: 1px solid var(--wf-outline-variant) !important;
}
.main .block-container {
  padding-top: 0.5rem !important;
  padding-bottom: 2rem !important;
  max-width: 1440px !important;
}
.wf-ms {
  font-family: "Material Symbols Outlined";
  font-weight: normal;
  font-style: normal;
  font-size: 20px;
  line-height: 1;
  vertical-align: middle;
}
.wf-brand-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--wf-primary);
  margin: 0;
}
.wf-brand-sub {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--wf-on-surface-variant);
  margin: 0.15rem 0 0 0;
}
.wf-top-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--wf-primary);
  margin: 0;
}
.wf-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: var(--wf-surface-container);
  font-size: 0.8rem;
}
.wf-pill-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--wf-primary); }
.wf-status-bar {
  border-radius: var(--wf-radius-lg);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  border: 1px solid var(--wf-outline-variant);
}
.wf-status-ok { background: var(--wf-ok-container); color: var(--wf-on-ok); }
.wf-status-warn { background: var(--wf-warn-container); color: var(--wf-on-warn); }
.wf-status-error { background: var(--wf-error-container); color: var(--wf-on-error-container); }
.wf-status-title { font-weight: 700; margin: 0 0 0.2rem 0; font-size: 0.95rem; }
.wf-status-body { margin: 0; font-size: 0.85rem; opacity: 0.95; }
.wf-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}
@media (min-width: 900px) { .wf-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.wf-stat-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  padding: 1rem 1.1rem;
}
.wf-stat-label { font-size: 0.75rem; color: var(--wf-secondary); margin: 0 0 0.35rem 0; }
.wf-stat-value { font-family: "Plus Jakarta Sans", sans-serif; font-size: 1.6rem; font-weight: 700; }
.wf-main-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 1100px) { .wf-main-grid { grid-template-columns: 1fr 1fr; } }
.wf-panel {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  overflow: hidden;
}
.wf-panel-head {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--wf-outline-variant);
  background: var(--wf-surface-low);
}
.wf-panel-title { margin: 0; font-size: 1rem; font-weight: 700; color: var(--wf-on-surface); }
.wf-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.wf-table th, .wf-table td { padding: 0.65rem 0.75rem; border-bottom: 1px solid var(--wf-outline-variant); }
.wf-badge { display: inline-block; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.72rem; font-weight: 700; }
.wf-badge-paid { background: #d1fae5; color: #065f46; }
.wf-badge-partial { background: #fef3c7; color: #92400e; }
.wf-badge-unpaid { background: #fee2e2; color: #991b1b; }
.wf-badge-other { background: #e2e8f0; color: #334155; }
.wf-timeline { border-left: 2px solid var(--wf-outline-variant); margin-left: 0.35rem; padding-left: 0.85rem; }
.wf-tl-item { margin-bottom: 0.85rem; }
.wf-tl-step { font-size: 0.7rem; color: var(--wf-secondary); margin: 0; }
.wf-tl-tool { font-size: 0.85rem; font-weight: 700; margin: 0.1rem 0; }
.wf-tl-out { font-size: 0.75rem; margin: 0; }
.wf-export-title { font-size: 1rem; font-weight: 700; margin: 1.25rem 0 0.75rem 0; }
.wf-mono { font-family: ui-monospace, monospace; }
</style>
"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def system_status_banner_html(
    cfg: RuntimeConfig,
    agent: AgentState | None,
    *,
    ui_status: str,
    ui_detail: str,
    data_stale: bool,
) -> str:
    if agent is None and ui_status == "Fresh":
        css = "wf-status-warn"
        title = "System Ready — awaiting first analysis"
        parts = ["Loading sample Warung Bu Sari data…"]
    elif data_stale:
        css = "wf-status-warn"
        title = "Data changed — refresh needed"
        parts = [ui_detail or "Input data changed. Click Force Refresh Analysis."]
    elif ui_status.startswith("Error") or (agent and agent.errors):
        css = "wf-status-error"
        title = "Critical Error"
        parts = list(agent.errors[:2]) if agent and agent.errors else [ui_detail]
    elif ui_status.startswith("Last run needs"):
        css = "wf-status-warn"
        title = "Needs Review"
        parts = [ui_detail or "Validation or workflow needs review."]
    elif ui_status.startswith("Auto-refresh"):
        css = "wf-status-ok"
        title = "Auto-refreshing"
        parts = [ui_detail or "Recomputing analysis for updated data."]
    elif agent and agent.final_status == "COMPLETE":
        css = "wf-status-ok"
        title = "System Ready"
        parts = []
        if cfg.payment_mode == "mock":
            parts.append("Running in Mock Payment Mode")
        if cfg.llm_mode == "mock":
            parts.append("LLM optional (mock templates active)")
        else:
            parts.append("LLM live (Groq)")
        parts.append(ui_detail or f"Last run {agent.current_run_id} complete")
    else:
        css = "wf-status-ok"
        title = ui_status or "System Ready"
        parts = [ui_detail] if ui_detail else []

    inner = " · ".join(_esc(p) for p in parts if p)
    return f"""
<div class="wf-status-bar {css}">
  <span class="wf-ms">monitoring</span>
  <div>
    <p class="wf-status-title">{_esc(title)}</p>
    <p class="wf-status-body">{inner}</p>
  </div>
</div>
"""


def mock_mode_banner_html(cfg: RuntimeConfig) -> str:
    """Deprecated alias — use system_status_banner_html from app."""
    return system_status_banner_html(cfg, None, ui_status="Fresh", ui_detail="", data_stale=False)


def stat_cards_html(health_score: int, collection_rate: float) -> str:
    return f"""
<div class="wf-stat-grid">
  <div class="wf-stat-card">
    <p class="wf-stat-label">Cashflow Health</p>
    <span class="wf-stat-value">{health_score}/100</span>
  </div>
  <div class="wf-stat-card">
    <p class="wf-stat-label">Collection Rate</p>
    <span class="wf-stat-value">{collection_rate:.0f}%</span>
  </div>
</div>
"""


def _badge_class(status: str | None) -> str:
    if status == "PAID":
        return "wf-badge wf-badge-paid"
    if status in ("PARTIALLY_PAID", "OVERPAID"):
        return "wf-badge wf-badge-partial"
    if status in ("UNPAID", "UNKNOWN", "NEEDS_REVIEW"):
        return "wf-badge wf-badge-unpaid"
    return "wf-badge wf-badge-other"


def _fmt_amount_table(n: Any) -> str:
    if n is None:
        return "—"
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def reconciliation_table_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="wf-panel-body"><p style="padding:1rem;">No rows yet.</p></div>'
    body = ""
    for r in rows:
        stt = r.get("status") or ""
        body += f"""<tr>
<td class="wf-mono">{_esc(r.get("customer"))}</td>
<td class="wf-mono" style="text-align:right">{_esc(_fmt_amount_table(r.get("amount")))}</td>
<td style="text-align:center"><span class="{_badge_class(stt)}">{_esc(stt)}</span></td>
<td class="wf-mono" style="text-align:right;font-size:0.8rem;">{_esc(r.get("order_id",""))}</td>
</tr>"""
    return f"""
<div class="wf-panel-body">
<table class="wf-table">
<thead><tr><th>Customer</th><th style="text-align:right">Amount</th><th>Status</th><th style="text-align:right">Order</th></tr></thead>
<tbody>{body}</tbody>
</table>
</div>
"""


def reconciliation_rows_from_state(state: AgentState) -> list[dict[str, Any]]:
    by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
    out: list[dict[str, Any]] = []
    for r in state.reconciliation_results or []:
        oid = str(r.get("order_id"))
        o = by_order.get(oid, {})
        customer = o.get("customer_name") or oid
        amt = r.get("matched_amount")
        if amt in (None, 0) and o.get("amount_expected") is not None:
            amt = o.get("amount_expected")
        out.append(
            {
                "customer": customer,
                "amount": amt,
                "status": str(r.get("status") or ""),
                "order_id": oid,
            }
        )
    return out


def trace_timeline_html(steps: list[ExecutionStep], max_items: int = 24) -> str:
    if not steps:
        return '<div class="wf-panel-body"><p style="padding:1rem;">No trace yet.</p></div>'
    recent = steps[-max_items:]
    lines: list[str] = []
    cur_run: int | None = None
    for t in recent:
        if cur_run != t.run_id:
            cur_run = t.run_id
            lines.append(
                f'<p style="font-weight:700;font-size:0.8rem;margin:0.75rem 0 0.35rem 0;">Run {t.run_id}</p>'
            )
        color = {"ok": "#10b981", "warn": "#f59e0b", "error": "#ef4444"}.get(t.status, "#64748b")
        extra = _esc(t.output_summary[:80])
        lines.append(f"""
<div class="wf-tl-item">
  <div class="wf-tl-dot" style="background:{color};width:8px;height:8px;border-radius:50%;display:inline-block;"></div>
  <p class="wf-tl-step">Step {t.step_number}</p>
  <h4 class="wf-tl-tool">{_esc(t.tool_called)}</h4>
  <p class="wf-tl-out">{extra}</p>
</div>""")
    return f'<div class="wf-panel-body" style="padding:1rem;"><div class="wf-timeline">{"".join(lines)}</div></div>'


EXPORT_LABELS: dict[str, tuple[str, str]] = {
    "daily_report.md": ("Daily Business Report", "assessment"),
    "payment_reminders.md": ("Payment Reminders", "notifications_active"),
    "financing_readiness.md": ("Financing Readiness", "account_balance"),
    "validation_report.md": ("Validation Report", "fact_check"),
    "reconciliation_result.csv": ("Reconciliation CSV", "table_chart"),
    "execution_trace.csv": ("Execution Trace CSV", "timeline"),
}
