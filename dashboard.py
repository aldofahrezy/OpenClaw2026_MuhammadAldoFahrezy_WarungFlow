"""WarungFlow dashboard: design tokens + HTML fragments matching the Tailwind reference UI."""

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
  --wf-primary-container: #00875a;
  --wf-radius: 0.25rem;
  --wf-radius-lg: 0.5rem;
}
html, body, [data-testid="stAppViewContainer"] {
  font-family: "Inter", system-ui, sans-serif;
  color: var(--wf-on-surface);
}
[data-testid="stAppViewContainer"] > .main {
  background: var(--wf-bg);
}
[data-testid="stHeader"] { background: var(--wf-surface); }
[data-testid="stSidebar"] {
  background-color: #ffffff !important;
  border-right: 1px solid var(--wf-outline-variant) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 0.5rem;
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
.wf-ms-sm { font-size: 18px; }
.wf-brand-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--wf-primary);
  margin: 0;
  line-height: 1.2;
}
.wf-brand-sub {
  font-family: "Inter", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--wf-on-surface-variant);
  margin: 0.15rem 0 0 0;
}
.wf-nav-wrap {
  background: var(--wf-surface);
  border-right: 1px solid var(--wf-outline-variant);
  border-radius: 0;
  padding: 1.25rem 0.75rem 1rem 0.75rem;
  min-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
}
.wf-nav-brand { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1.75rem; padding: 0 0.25rem; }
.wf-logo {
  width: 2rem; height: 2rem; border-radius: 9999px;
  background: var(--wf-primary); color: var(--wf-on-primary);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.wf-banner-mock {
  background: var(--wf-error-container);
  border: 1px solid rgba(186, 26, 26, 0.2);
  border-radius: var(--wf-radius-lg);
  padding: 1rem 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.wf-banner-icon {
  width: 2.5rem; height: 2.5rem; border-radius: 9999px;
  background: rgba(186, 26, 26, 0.1); color: var(--wf-error);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.wf-banner-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--wf-on-error-container);
  margin: 0 0 0.25rem 0;
}
.wf-banner-body {
  font-size: 0.875rem;
  color: rgba(147, 0, 10, 0.85);
  margin: 0;
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem;
}
.wf-dot { width: 4px; height: 4px; border-radius: 9999px; background: rgba(186,26,26,0.5); }
.wf-stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem; }
@media (max-width: 768px) { .wf-stat-grid { grid-template-columns: 1fr; } }
.wf-stat-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
}
.wf-stat-card::after {
  content: ""; position: absolute; right: 0; top: 0;
  width: 8rem; height: 8rem; background: rgba(0,107,71,0.05);
  border-bottom-left-radius: 100%;
  transform: translate(30%, -30%); pointer-events: none;
}
.wf-stat-label {
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em;
  color: var(--wf-on-surface-variant); text-transform: uppercase; margin: 0 0 0.35rem 0;
}
.wf-stat-value {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.75rem; font-weight: 700;
  color: var(--wf-on-surface); margin: 0;
  display: inline-block;
}
.wf-stat-delta {
  font-size: 0.875rem; font-weight: 500;
  color: var(--wf-primary); margin-left: 0.5rem;
}
.wf-main-grid { display: grid; grid-template-columns: 1fr; gap: 1.25rem; }
@media (min-width: 1024px) {
  .wf-main-grid { grid-template-columns: minmax(0, 8fr) minmax(0, 4fr); }
}
.wf-panel {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  display: flex;
  flex-direction: column;
  min-height: 420px;
  max-height: 520px;
}
.wf-panel-head {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--wf-outline-variant);
  background: var(--wf-surface-low);
  border-radius: var(--wf-radius-lg) var(--wf-radius-lg) 0 0;
  display: flex; justify-content: space-between; align-items: center;
}
.wf-panel-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.05rem; font-weight: 600;
  margin: 0; color: var(--wf-on-surface);
}
.wf-panel-body { flex: 1; overflow: auto; }
.wf-table { width: 100%; border-collapse: collapse; text-align: left; }
.wf-table thead th {
  position: sticky; top: 0; z-index: 2;
  background: var(--wf-surface-low);
  border-bottom: 1px solid var(--wf-outline-variant);
  padding: 0.5rem 1rem;
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em;
  color: var(--wf-secondary);
}
.wf-table tbody td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--wf-outline-variant);
  font-size: 0.875rem;
}
.wf-table tbody tr:hover { background: #fafbff; }
.wf-mono { font-variant-numeric: tabular-nums; font-family: "Inter", monospace; }
.wf-badge {
  display: inline-block; padding: 0.2rem 0.45rem; border-radius: 0.125rem;
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em;
}
.wf-badge-paid { background: #d1fae5; color: #065f46; }
.wf-badge-partial { background: #fef3c7; color: #92400e; }
.wf-badge-unpaid { background: #fee2e2; color: #991b1b; }
.wf-badge-other { background: #e5e7eb; color: #374151; }
.wf-timeline { position: relative; padding-left: 1.5rem; margin-left: 0.35rem;
  border-left: 2px solid rgba(189, 202, 192, 0.45); }
.wf-tl-item { position: relative; padding-bottom: 1rem; }
.wf-tl-dot {
  position: absolute; left: -1.55rem; top: 0.2rem;
  width: 0.9rem; height: 0.9rem; border-radius: 9999px;
  border: 2px solid #fff;
}
.wf-tl-step { font-size: 0.75rem; font-weight: 600; color: var(--wf-on-surface-variant); margin: 0; }
.wf-tl-tool { font-size: 0.875rem; font-weight: 500; margin: 0.15rem 0 0 0; color: var(--wf-on-surface); }
.wf-tl-out { font-size: 0.8125rem; font-weight: 500; margin: 0.2rem 0 0 0; }
.wf-export-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.05rem; font-weight: 600;
  margin: 1.5rem 0 0.75rem 0;
}
.wf-export-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
@media (max-width: 900px) { .wf-export-grid { grid-template-columns: 1fr; } }
.wf-export-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  padding: 0.75rem;
  min-height: 7.5rem;
  display: flex; flex-direction: column; justify-content: space-between;
  transition: border-color 0.15s;
}
.wf-export-card:hover { border-color: var(--wf-primary); }
.wf-export-head { display: flex; align-items: center; gap: 0.35rem; }
.wf-export-head h4 { margin: 0; font-size: 0.875rem; font-weight: 500; }
.wf-header-bar {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 0.75rem;
  background: var(--wf-surface);
  border-bottom: 1px solid var(--wf-outline-variant);
  padding: 0.65rem 0 1rem 0;
  margin-bottom: 1rem;
  position: sticky; top: 0; z-index: 20;
}
.wf-pill {
  display: inline-flex; align-items: center; gap: 0.35rem;
  background: var(--wf-surface-low);
  border: 1px solid var(--wf-outline-variant);
  border-radius: 0.125rem;
  padding: 0.2rem 0.45rem;
  font-size: 0.75rem; font-weight: 600;
  color: var(--wf-on-surface-variant);
}
.wf-pill-dot { width: 8px; height: 8px; border-radius: 9999px; background: var(--wf-primary); }
.wf-top-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.1rem; font-weight: 700;
  color: var(--wf-primary);
}
.wf-help-btn-wrap { margin-top: auto; padding-top: 1.25rem; border-top: 1px solid var(--wf-outline-variant); }
</style>
"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def mock_mode_banner_html(cfg: RuntimeConfig) -> str:
    if cfg.llm_mode != "mock" and cfg.payment_mode != "mock":
        return ""
    parts = []
    if cfg.llm_mode == "mock":
        parts.append("LLM Mode: MOCK (API key missing or LLM_MODE=mock)")
    if cfg.payment_mode == "mock":
        parts.append("Payment Mode: MOCK")
    inner = ""
    for i, p in enumerate(parts):
        if i:
            inner += '<span class="wf-dot"></span>'
        inner += f"<span>{_esc(p)}</span>"
    return f"""
<div class="wf-banner-mock">
  <div class="wf-banner-icon"><span class="wf-ms">warning</span></div>
  <div>
    <h3 class="wf-banner-title">System Health: Mock Mode Active</h3>
    <p class="wf-banner-body">{inner}</p>
  </div>
</div>
"""


def stat_cards_html(health_score: int, collection_rate: float) -> str:
    return f"""
<div class="wf-stat-grid">
  <div class="wf-stat-card">
    <p class="wf-stat-label">Cashflow Health</p>
    <div>
      <span class="wf-stat-value">{health_score}/100</span>
      <span class="wf-stat-delta wf-mono" style="font-size:0.75rem;color:var(--wf-on-surface-variant);">this run</span>
    </div>
  </div>
  <div class="wf-stat-card">
    <p class="wf-stat-label">Total Reconciliation</p>
    <div>
      <span class="wf-stat-value">{collection_rate:.0f}%</span>
      <span class="wf-stat-delta wf-mono" style="font-size:0.75rem;color:var(--wf-on-surface-variant);">collection</span>
    </div>
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
        v = int(n)
    except (TypeError, ValueError):
        return "—"
    return f"{v:,}"


def reconciliation_table_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="wf-panel-body"><p style="padding:1rem;color:var(--wf-on-surface-variant);">No rows yet.</p></div>'
    body = ""
    for r in rows:
        stt = r.get("status") or ""
        body += f"""<tr>
<td class="wf-mono">{_esc(r.get("customer"))}</td>
<td class="wf-mono" style="text-align:right">{_esc(_fmt_amount_table(r.get("amount")))}</td>
<td style="text-align:center"><span class="{_badge_class(stt)}">{_esc(stt)}</span></td>
<td class="wf-mono" style="text-align:right;font-size:0.8rem;color:var(--wf-secondary)">{_esc(r.get("order_id",""))}</td>
</tr>"""
    return f"""
<div class="wf-panel-body">
<table class="wf-table">
<thead><tr>
<th>Customer</th>
<th style="text-align:right">Amount (IDR)</th>
<th style="text-align:center">Status</th>
<th style="text-align:right">Order</th>
</tr></thead>
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
        status = str(r.get("status") or "")
        amt = r.get("matched_amount")
        if amt in (None, 0) and o.get("amount_expected") is not None:
            amt = o.get("amount_expected")
        out.append(
            {
                "customer": customer,
                "amount": amt,
                "status": status,
                "order_id": oid,
            }
        )
    return out


def trace_timeline_html(steps: list[ExecutionStep], max_items: int = 24) -> str:
    if not steps:
        return '<div class="wf-panel-body"><p style="padding:1rem;">No trace yet.</p></div>'
    lines: list[str] = []
    for t in steps[:max_items]:
        color = {"ok": "#10b981", "warn": "#f59e0b", "error": "#ef4444"}.get(t.status, "#64748b")
        label = t.status.upper()
        extra = _esc(t.output_summary[:96])
        if len(t.output_summary) > 96:
            extra += "…"
        lines.append(f"""
<div class="wf-tl-item">
  <div class="wf-tl-dot" style="background:{color};"></div>
  <p class="wf-tl-step">Step {t.step_number}</p>
  <h4 class="wf-tl-tool">{_esc(t.tool_called)}</h4>
  <p class="wf-tl-out wf-mono" style="color:{color}">{label} <span style="color:var(--wf-on-surface-variant);font-weight:400;">({extra})</span></p>
</div>
""")
    return f'<div class="wf-panel-body" style="padding:1rem;"><div class="wf-timeline">{"".join(lines)}</div></div>'


EXPORT_LABELS: dict[str, tuple[str, str]] = {
    "daily_report.md": ("Daily Business Report", "assessment"),
    "payment_reminders.md": ("Payment Reminders", "notifications_active"),
    "financing_readiness.md": ("Financing Readiness", "account_balance"),
    "validation_report.md": ("Validation Report", "fact_check"),
    "reconciliation_result.csv": ("Reconciliation CSV", "table_chart"),
    "execution_trace.csv": ("Execution Trace CSV", "timeline"),
}
