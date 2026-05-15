"""WarungFlow dashboard: design tokens + HTML fragments."""

from __future__ import annotations

import html
from typing import Any

from config import RuntimeConfig
from state import AgentState, ExecutionStep
from tools.parsers import strip_internal_meta


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
.wf-kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
@media (min-width: 640px) { .wf-kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.wf-kpi-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg);
  padding: 0.85rem 1rem;
  min-width: 0;
}
.wf-kpi-label {
  font-size: 0.72rem;
  color: var(--wf-secondary);
  margin: 0 0 0.35rem 0;
  line-height: 1.3;
}
.wf-kpi-value {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: clamp(0.9rem, 2.2vw, 1.4rem);
  letter-spacing: -0.02em;
  font-weight: 700;
  color: var(--wf-on-surface);
  margin: 0;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.25;
}
.wf-kpi-delta {
  font-size: 0.7rem;
  color: var(--wf-primary);
  margin: 0.35rem 0 0 0;
  font-weight: 600;
  white-space: normal;
}
/* Streamlit st.metric fallback — show full values on Reports page */
[data-testid="stMetricValue"] {
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
}
.wf-dashboard-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.wf-dashboard-stack .wf-panel-trace { margin-top: 0.25rem; }
.wf-reco-summary {
  display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
  padding: 0.85rem 1rem; margin-bottom: 1rem;
  background: var(--wf-surface-low); border-radius: var(--wf-radius-lg);
  border: 1px solid var(--wf-outline-variant);
}
.wf-reco-chip {
  display: inline-block; padding: 0.35rem 0.65rem; font-size: 0.82rem;
  background: var(--wf-surface); border: 1px solid var(--wf-outline-variant);
  border-radius: 999px; color: var(--wf-on-surface);
}
.wf-reco-summary-hint {
  flex: 1 1 100%; margin: 0.35rem 0 0 0; font-size: 0.82rem; color: var(--wf-secondary);
}
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
.wf-mono { font-family: ui-monospace, monospace; font-size: 0.82rem; }
.wf-logo {
  width: 2.35rem; height: 2.35rem; border-radius: var(--wf-radius);
  background: var(--wf-primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.wf-nav-brand { display: flex; gap: 0.65rem; align-items: center; }
.wf-section-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.15rem; font-weight: 700; color: var(--wf-primary); margin: 0 0 0.25rem 0;
}
.wf-section-sub { font-size: 0.88rem; color: var(--wf-on-surface-variant); margin: 0 0 1rem 0; line-height: 1.5; }
.wf-page-intro { margin-bottom: 1.25rem; }
.wf-empty { padding: 1.25rem 1rem; color: var(--wf-secondary); font-size: 0.9rem; line-height: 1.55; margin: 0; }
.wf-export-card {
  background: var(--wf-surface); border: 1px solid var(--wf-outline-variant);
  border-radius: var(--wf-radius-lg); padding: 0.85rem 1rem; margin-bottom: 0.5rem;
}
.wf-export-head { display: flex; align-items: center; gap: 0.5rem; }
.wf-export-head h4 { margin: 0; font-size: 0.9rem; font-weight: 600; color: var(--wf-on-surface); }
.wf-table th {
  font-size: 0.72rem; font-weight: 700; text-transform: none; letter-spacing: 0.01em;
  color: var(--wf-secondary); background: var(--wf-surface-low);
}
.wf-table td { color: var(--wf-on-surface); line-height: 1.45; }
.wf-tl-dot { flex-shrink: 0; margin-top: 0.35rem; }
.wf-tl-item { display: flex; gap: 0.5rem; align-items: flex-start; }
.wf-tl-body { flex: 1; min-width: 0; }
.wf-tl-run { font-size: 0.75rem; font-weight: 700; color: var(--wf-primary); margin: 0.85rem 0 0.4rem 0; }
.wf-tl-tool-human { font-size: 0.88rem; font-weight: 600; margin: 0.1rem 0 0.15rem 0; color: var(--wf-on-surface); }
.wf-tl-tool-code { font-size: 0.68rem; color: var(--wf-secondary); font-family: ui-monospace, monospace; margin: 0; }
.wf-kpi-delta-positive { color: var(--wf-on-ok); }
.wf-kpi-delta-neutral { color: var(--wf-secondary); }
.wf-kpi-delta-warn { color: var(--wf-on-warn); }
/* Streamlit component readability */
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
  line-height: 1.5 !important;
}
[data-testid="stSidebar"] .stButton button {
  font-weight: 600 !important; border-radius: var(--wf-radius-lg) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  font-weight: 600 !important; font-size: 0.92rem !important;
}
h1, h2, h3, h4, h5, h6 {
  font-family: "Plus Jakarta Sans", sans-serif !important;
  color: var(--wf-on-surface) !important;
  letter-spacing: -0.01em !important;
}
[data-testid="stCaptionContainer"] p, .stCaption { font-size: 0.85rem !important; line-height: 1.5 !important; }
[data-testid="stDataFrame"] { font-size: 0.88rem !important; }
div[data-testid="stMarkdownContainer"] p { line-height: 1.55; }
[data-testid="stStatusWidget"] { font-size: 0.9rem !important; }
.wf-page-stack { display: flex; flex-direction: column; gap: 1.35rem; }
.wf-section-header {
  display: flex; align-items: flex-start; gap: 0.75rem;
  padding: 0.9rem 1.1rem; margin-bottom: -1px;
  border: 1px solid var(--wf-outline-variant);
  border-radius: 12px 12px 0 0;
  background: var(--wf-surface-low);
}
.wf-section-header--accent {
  background: linear-gradient(135deg, #e8f5ef 0%, #d1fae5 100%);
  border-color: #a7d4bc;
}
.wf-section-header--muted {
  background: var(--wf-surface-container);
}
.wf-section-icon {
  width: 2.35rem; height: 2.35rem; border-radius: 10px;
  background: var(--wf-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.wf-section-header--accent .wf-section-icon { background: #00875a; }
.wf-section-header-text { flex: 1; min-width: 0; }
.wf-section-header-title {
  margin: 0; font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 1.05rem; font-weight: 700; color: var(--wf-on-surface);
}
.wf-section-header-sub {
  margin: 0.2rem 0 0; font-size: 0.85rem; color: var(--wf-secondary); line-height: 1.45;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--wf-surface) !important;
  border: 1px solid var(--wf-outline-variant) !important;
  border-radius: 0 0 12px 12px !important;
  border-top: none !important;
  padding: 1rem 1.1rem 1.1rem !important;
  margin-bottom: 1.35rem !important;
  box-shadow: 0 2px 8px rgba(11, 28, 48, 0.04);
}
.wf-section-header + [data-testid="stVerticalBlockBorderWrapper"] {
  margin-top: 0 !important;
}
.wf-standalone-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 1.35rem;
  box-shadow: 0 2px 8px rgba(11, 28, 48, 0.04);
}
.wf-pill-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0 0 0.5rem 0; }
.wf-status-pill {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.4rem 0.8rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600;
  background: var(--wf-ok-container); color: var(--wf-on-ok);
  border: 1px solid #a7d4bc;
}
.wf-status-pill--muted {
  background: var(--wf-surface-container); color: var(--wf-on-surface);
  border-color: var(--wf-outline-variant);
}
.wf-hint-box {
  font-size: 0.88rem; line-height: 1.55; color: var(--wf-secondary);
  padding: 0.75rem 0.9rem; border-radius: 10px;
  background: var(--wf-surface-low); border: 1px dashed var(--wf-outline-variant);
  margin: 0 0 0.75rem 0;
}
hr, [data-testid="stMarkdownContainer"] hr { display: none !important; }
.stTabs [data-baseweb="tab-list"] { gap: 0.35rem; background: transparent; }
.stTabs [data-baseweb="tab"] {
  border-radius: 8px !important; font-weight: 600 !important;
  background: var(--wf-surface-low) !important;
}
.stTabs [aria-selected="true"] {
  background: var(--wf-primary) !important; color: #fff !important;
}
.wf-rec-list { display: flex; flex-direction: column; gap: 0.85rem; }
.wf-rec-card {
  background: var(--wf-surface);
  border: 1px solid var(--wf-outline-variant);
  border-radius: 10px;
  padding: 0.85rem 1rem 0.95rem 1rem;
}
.wf-rec-cat {
  margin: 0 0 0.25rem 0; font-size: 0.72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--wf-secondary);
}
.wf-rec-title { margin: 0 0 0.35rem 0; font-size: 0.98rem; font-weight: 700; color: var(--wf-on-surface); }
.wf-rec-why { margin: 0 0 0.5rem 0; font-size: 0.85rem; color: var(--wf-secondary); line-height: 1.45; }
.wf-rec-steps {
  margin: 0; padding-left: 1.15rem; font-size: 0.86rem; line-height: 1.55; color: var(--wf-on-surface);
}
</style>
"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


STATUS_LABELS: dict[str, str] = {
    "PAID": "Lunas",
    "UNPAID": "Belum lunas",
    "PARTIALLY_PAID": "Bayar sebagian",
    "OVERPAID": "Lebih bayar",
    "UNKNOWN": "Tidak diketahui",
    "NEEDS_REVIEW": "Perlu ditinjau",
}

TOOL_LABELS: dict[str, str] = {
    "LOAD_MERCHANT_PROFILE": "Muat profil warung",
    "LOAD_ORDERS": "Muat pesanan WhatsApp",
    "PARSE_ORDERS": "Urai pesanan",
    "LOAD_PAYMENTS": "Muat pembayaran QRIS",
    "LOAD_EXPENSES": "Muat pengeluaran",
    "LOAD_CUSTOMERS": "Muat data pelanggan",
    "RECONCILE_PAYMENTS": "Cocokkan pembayaran",
    "DETECT_PAYMENT_ISSUES": "Deteksi masalah pembayaran",
    "RESOLVE_PAYMENT_REQUESTS": "Buat permintaan bayar",
    "CHECK_PAYMENT_STATUS": "Cek status pembayaran",
    "CALCULATE_CASHFLOW": "Hitung arus kas",
    "SCORE_CASHFLOW_HEALTH": "Skor kesehatan kas",
    "GENERATE_REMINDERS": "Buat pengingat WhatsApp",
    "GENERATE_FINANCING_READINESS": "Kesiapan pembiayaan",
    "GENERATE_DAILY_REPORT": "Laporan harian",
    "VALIDATE_OUTPUTS": "Validasi laporan",
    "EXPORT_REPORTS": "Ekspor file",
    "ORCHESTRATOR": "Orkestrator agen",
    "ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS": "Estimasi nominal kosong",
    "DOKU_WEBHOOK_SIMULATOR": "Simulasi webhook DOKU",
    "LOAD_PRODUCT_CATALOGUE": "Muat katalog produk",
    "SYNC_BOT_EVENTS": "Sinkronkan event WhatsApp bot",
}


def human_status(status: str | None) -> str:
    if not status:
        return "—"
    return STATUS_LABELS.get(str(status).upper(), str(status).replace("_", " ").title())


def human_tool(tool: str) -> str:
    return TOOL_LABELS.get(tool, tool.replace("_", " ").title())


ISSUE_NOTE_LABELS: dict[str, str] = {
    "no_confident_match": "Belum ada pembayaran yang cocok di mutasi QRIS/transfer",
    "no_payments_in_pool": "Belum ada mutasi pembayaran untuk dicocokkan",
}


def humanize_payment_note(note: str | None) -> str:
    if not note:
        return "—"
    key = str(note).strip().lower()
    if key in ISSUE_NOTE_LABELS:
        return ISSUE_NOTE_LABELS[key]
    if key.startswith("bot-wh-"):
        return "Pembayaran dari simulasi WhatsApp Bot"
    return str(note).strip()


def confidence_label(conf: Any) -> str:
    try:
        c = float(conf)
    except (TypeError, ValueError):
        return "—"
    if c >= 90:
        return "Tinggi"
    if c >= 70:
        return "Sedang"
    if c > 0:
        return "Rendah"
    return "Belum cocok"


def section_heading_html(title: str, subtitle: str | None = None) -> str:
    sub = f'<p class="wf-section-sub">{_esc(subtitle)}</p>' if subtitle else ""
    return f'<div class="wf-page-intro"><p class="wf-section-title">{_esc(title)}</p>{sub}</div>'


def page_intro_html(title: str, subtitle: str) -> str:
    return section_heading_html(title, subtitle)


def section_header_html(
    title: str,
    subtitle: str = "",
    *,
    icon: str = "widgets",
    variant: str = "default",
) -> str:
    """Colored header — place immediately above st.container(border=True)."""
    var_class = f" wf-section-header--{variant}" if variant != "default" else ""
    sub = (
        f'<p class="wf-section-header-sub">{_esc(subtitle)}</p>' if subtitle else ""
    )
    return f"""
<div class="wf-section-header{var_class}">
  <span class="wf-section-icon"><span class="wf-ms" style="color:#fff;font-size:20px;">{_esc(icon)}</span></span>
  <div class="wf-section-header-text">
    <p class="wf-section-header-title">{_esc(title)}</p>
    {sub}
  </div>
</div>
"""


def page_stack_open_html() -> str:
    return '<div class="wf-page-stack">'


def page_stack_close_html() -> str:
    return "</div>"


def status_pills_html(pills: list[tuple[str, str]]) -> str:
    parts = []
    for label, variant in pills:
        cls = "wf-status-pill" if variant == "ok" else "wf-status-pill wf-status-pill--muted"
        parts.append(f'<span class="{cls}">{_esc(label)}</span>')
    return f'<div class="wf-pill-row">{"".join(parts)}</div>'


def hint_box_html(text: str) -> str:
    return f'<div class="wf-hint-box">{_esc(text)}</div>'


BOT_STATUS_LABELS: dict[str, str] = {
    "AWAITING_PAYMENT": "Menunggu bayar",
    "PAID": "Lunas",
    "PENDING": "Menunggu",
    "COMPLETED": "Selesai",
}


def human_bot_status(status: str | None) -> str:
    if not status:
        return "—"
    return BOT_STATUS_LABELS.get(str(status).upper(), human_status(status))


def _fmt_idr_table(n: Any) -> str:
    if n is None:
        return "—"
    try:
        return f"Rp {int(n):,}"
    except (TypeError, ValueError):
        return "—"


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
        title = "Menyiapkan analisis pertama"
        parts = ["Memuat data contoh Warung Bu Sari…"]
    elif data_stale:
        css = "wf-status-warn"
        title = "Data berubah — perlu refresh"
        parts = [ui_detail or "Klik Force Refresh Analysis di sidebar."]
    elif agent and agent.final_status == "ERROR":
        css = "wf-status-error"
        title = "Critical Error"
        parts = list(agent.errors[:2]) if agent.errors else [ui_detail or "Agent run failed"]
    elif ui_status.startswith("Error"):
        css = "wf-status-error"
        title = "Critical Error"
        parts = [ui_detail] if ui_detail else ["Agent could not complete"]
    elif ui_status.startswith("Last run needs") or (
        agent and agent.final_status == "NEEDS_REVIEW"
    ):
        css = "wf-status-warn"
        title = "Perlu ditinjau"
        review = collect_review_items(agent) if agent else {"reasons": [], "actions": []}
        if review.get("reasons"):
            parts = list(review["reasons"][:2])
        else:
            parts = [ui_detail or "Ada item yang perlu Anda putuskan sebelum ekspor ke bank."]
        if cfg.llm_mode == "mock":
            parts.append("LLM opsional (template mock aktif)")
        if cfg.payment_mode == "mock":
            parts.append("DOKU opsional (mode mock aktif)")
    elif ui_status.startswith("Auto-refresh"):
        css = "wf-status-ok"
        title = "Memperbarui analisis"
        parts = [ui_detail or "Menghitung ulang setelah data berubah."]
    elif agent and agent.final_status in {"COMPLETE", None}:
        css = "wf-status-ok"
        title = "Siap dipakai"
        parts = []
        if cfg.payment_mode == "mock":
            parts.append("Mode pembayaran mock — aman untuk demo")
        else:
            parts.append("DOKU Sandbox siap (adapter)")
        if cfg.llm_mode == "mock":
            parts.append("LLM opsional — tanpa API key")
        else:
            parts.append("LLM aktif (Groq)")
        if cfg.payment_mode == "doku_sandbox" and cfg.warnings:
            parts.append("Kredensial DOKU opsional untuk demo")
        parts.append(ui_detail or f"Analisis run #{agent.current_run_id} selesai")
    elif agent is None and ui_status.startswith("Last run completed"):
        css = "wf-status-ok"
        title = "System Ready"
        parts = [ui_detail] if ui_detail else ["Analysis complete"]
    else:
        css = "wf-status-ok"
        title = ui_status or "System Ready"
        parts = [ui_detail] if ui_detail else []
        if cfg.payment_mode == "mock":
            parts.append("Running in Mock Payment Mode")
        if cfg.llm_mode == "mock":
            parts.append("LLM optional")

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
    <p class="wf-stat-label">Skor kesehatan kas</p>
    <span class="wf-stat-value">{health_score}<span style="font-size:1rem;font-weight:600;color:var(--wf-secondary)">/100</span></span>
    <p class="wf-kpi-delta wf-kpi-delta-neutral" style="margin-top:0.4rem">{"Sangat baik" if health_score >= 80 else "Cukup stabil" if health_score >= 60 else "Perlu perhatian"}</p>
  </div>
  <div class="wf-stat-card">
    <p class="wf-stat-label">Tingkat penagihan</p>
    <span class="wf-stat-value">{collection_rate:.0f}%</span>
    <p class="wf-kpi-delta wf-kpi-delta-neutral" style="margin-top:0.4rem">Dari omzet yang diharapkan</p>
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


def _settlement_cell(status: str, settlement: str | None) -> str:
    if not settlement:
        return '<td style="text-align:right;color:#64748b">—</td>'
    st = status.upper()
    color = (
        "#b45309"
        if st in {"UNPAID", "PARTIALLY_PAID"}
        else "#0d9488"
        if st == "OVERPAID"
        else "#64748b"
    )
    weight = "600" if st in {"UNPAID", "PARTIALLY_PAID", "OVERPAID"} else "500"
    return (
        f'<td style="text-align:right;font-weight:{weight};color:{color}">'
        f"{_esc(settlement)}</td>"
    )


def reconciliation_table_html(
    rows: list[dict[str, Any]], *, show_order_id: bool = True
) -> str:
    if not rows:
        return '<div class="wf-panel-body"><p class="wf-empty">Belum ada data. Analisis pertama akan mengisi tabel ini.</p></div>'
    body = ""
    for r in rows:
        stt = str(r.get("status") or "")
        oid_col = (
            f'<td class="wf-mono" style="text-align:right">{_esc(r.get("order_id", ""))}</td>'
            if show_order_id
            else ""
        )
        body += f"""<tr>
<td>{_esc(r.get("customer"))}</td>
<td style="text-align:right;font-weight:600">{_esc(_fmt_idr_table(r.get("amount_expected")))}</td>
<td style="text-align:right">{_esc(_fmt_idr_table(r.get("amount_paid")))}</td>
<td style="text-align:center"><span class="{_badge_class(stt)}">{_esc(human_status(stt))}</span></td>
{_settlement_cell(stt, r.get("settlement"))}
{oid_col}
</tr>"""
    oid_header = (
        '<th style="text-align:right">Order ID</th>' if show_order_id else ""
    )
    return f"""
<div class="wf-panel-body">
<table class="wf-table">
<thead><tr>
<th>Pelanggan</th>
<th style="text-align:right">Tagihan</th>
<th style="text-align:right">Terbayar</th>
<th>Status</th>
<th style="text-align:right">Sisa / kelebihan</th>
{oid_header}
</tr></thead>
<tbody>{body}</tbody>
</table>
</div>
"""


def reconciliation_summary_html(state: AgentState) -> str:
    rows = reconciliation_rows_from_state(state)
    if not rows:
        return ""
    counts: dict[str, int] = {}
    for r in rows:
        label = human_status(str(r.get("status") or ""))
        counts[label] = counts.get(label, 0) + 1
    chips = [
        f'<span class="wf-reco-chip">{_esc(label)}: <strong>{n}</strong></span>'
        for label, n in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return f"""
<div class="wf-reco-summary">
  {"".join(chips)}
  <p class="wf-reco-summary-hint">Ringkasan {len(rows)} pesanan WhatsApp dicocokkan dengan mutasi QRIS/transfer.</p>
</div>
"""


def payment_issues_rows_from_state(state: AgentState) -> list[dict[str, Any]]:
    by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
    by_reco = {str(r.get("order_id")): r for r in (state.reconciliation_results or [])}
    out: list[dict[str, Any]] = []
    for issue in state.payment_issues or []:
        oid = str(issue.get("order_id") or "")
        o = by_order.get(oid, {})
        r = by_reco.get(oid, {})
        status = str(issue.get("issue_type") or r.get("status") or "")
        expected_raw = o.get("amount_expected")
        expected = int(expected_raw) if isinstance(expected_raw, int) else None
        paid_raw = r.get("matched_amount")
        paid = int(paid_raw) if isinstance(paid_raw, (int, float)) else 0
        out.append(
            {
                "customer": strip_internal_meta(
                    str(o.get("customer_name") or "Pelanggan")
                ),
                "issue": human_status(status),
                "status": status,
                "amount_expected": expected,
                "amount_paid": paid,
                "settlement": _settlement_label(status, expected, paid),
                "note": humanize_payment_note(
                    str(issue.get("detail") or r.get("notes") or "")
                ),
                "confidence": confidence_label(issue.get("confidence")),
                "order_id": oid,
            }
        )
    return out


def payment_issues_table_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="wf-panel-body"><p class="wf-empty">Semua pesanan sudah lunas atau tidak ada masalah.</p></div>'
    body = ""
    for r in rows:
        stt = str(r.get("status") or "")
        body += f"""<tr>
<td>{_esc(r.get("customer"))}</td>
<td style="text-align:center"><span class="{_badge_class(stt)}">{_esc(r.get("issue"))}</span></td>
<td style="text-align:right">{_esc(_fmt_idr_table(r.get("amount_expected")))}</td>
<td style="text-align:right">{_esc(_fmt_idr_table(r.get("amount_paid")))}</td>
{_settlement_cell(stt, r.get("settlement"))}
<td>{_esc(r.get("note"))}</td>
<td style="text-align:center">{_esc(r.get("confidence"))}</td>
</tr>"""
    return f"""
<div class="wf-panel-body">
<table class="wf-table">
<thead><tr>
<th>Pelanggan</th>
<th>Status</th>
<th style="text-align:right">Tagihan</th>
<th style="text-align:right">Terbayar</th>
<th style="text-align:right">Sisa / kelebihan</th>
<th>Keterangan</th>
<th style="text-align:center">Keyakinan cocok</th>
</tr></thead>
<tbody>{body}</tbody>
</table>
</div>
"""


def build_action_recommendations(
    state: AgentState,
    cfg: RuntimeConfig | None = None,
) -> list[dict[str, Any]]:
    """Actionable steps to fix warnings, payment issues, or improve health score."""
    items: list[dict[str, Any]] = []
    cfg = cfg or RuntimeConfig.load()
    cs = state.cashflow_summary or {}
    hs = state.health_score or {}
    reco = state.reconciliation_results or []
    by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}

    coll_rate = float(cs.get("collection_rate") or 0)
    net = int(cs.get("net_cash_position") or 0)
    health_i = int(hs.get("score") or 0)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in reco:
        st = str(r.get("status") or "").upper()
        if st in {"UNPAID", "PARTIALLY_PAID", "OVERPAID", "UNKNOWN", "NEEDS_REVIEW"}:
            grouped.setdefault(st, []).append(r)

    if grouped.get("UNPAID"):
        rows = grouped["UNPAID"]
        names = []
        total_sisa = 0
        for r in rows:
            o = by_order.get(str(r.get("order_id")), {})
            names.append(strip_internal_meta(str(o.get("customer_name") or "Pelanggan")))
            exp = o.get("amount_expected")
            paid = int(r.get("matched_amount") or 0)
            if isinstance(exp, int):
                total_sisa += max(0, exp - paid)
        items.append(
            {
                "category": "Isu pembayaran",
                "priority": "high",
                "title": f"Tagih {len(rows)} pesanan belum lunas",
                "why": (
                    f"Pelanggan: {', '.join(names[:4])}"
                    + ("…" if len(names) > 4 else "")
                    + (f" · total sisa sekitar Rp {total_sisa:,}" if total_sisa else "")
                ),
                "steps": [
                    "Buka **Rekonsiliasi** → cek kolom Sisa untuk nominal yang harus dibayar.",
                    "Kirim pengingat WhatsApp (lihat **Laporan** → Pengingat pembayaran).",
                    "Setelah pelanggan transfer, pastikan mutasi QRIS masuk — lalu **Paksa refresh analisis**.",
                    "Demo cepat: sidebar → **Bayar Kevin (cocok)** atau **WhatsApp Bot** → simulasi bayar.",
                ],
            }
        )

    if grouped.get("PARTIALLY_PAID"):
        rows = grouped["PARTIALLY_PAID"]
        items.append(
            {
                "category": "Isu pembayaran",
                "priority": "high",
                "title": f"Lunasi sisa {len(rows)} pesanan (bayar sebagian)",
                "why": "Pembayaran masuk tetapi belum mencapai total tagihan.",
                "steps": [
                    "Cocokkan catatan transfer dengan sisa tagihan di tabel Rekonsiliasi.",
                    "Hubungi pelanggan untuk melunasi kekurangan — gunakan draft di Laporan.",
                    "Jika sudah bayar, tambahkan mutasi di sidebar **Sandbox** → Tambah pembayaran.",
                ],
            }
        )

    if grouped.get("OVERPAID"):
        rows = grouped["OVERPAID"]
        items.append(
            {
                "category": "Isu pembayaran",
                "priority": "medium",
                "title": f"Cek {len(rows)} pembayaran lebih bayar",
                "why": "Nominal masuk melebihi tagihan — perlu dikembalikan atau dicatat.",
                "steps": [
                    "Buka **Rekonsiliasi** → kolom **Lebih Rp …** untuk selisih per pelanggan.",
                    "Kembalikan kelebihan ke pelanggan atau catat sebagai deposit untuk order berikutnya.",
                    "Perbarui catatan pembayaran agar analisis berikutnya konsisten.",
                ],
            }
        )

    unknown_rows = grouped.get("UNKNOWN", []) + grouped.get("NEEDS_REVIEW", [])
    if unknown_rows:
        items.append(
            {
                "category": "Isu pembayaran",
                "priority": "medium",
                "title": f"Tinjau {len(unknown_rows)} pesanan tanpa kecocokan jelas",
                "why": "Belum ada mutasi yang cocok dengan tagihan atau nominal tidak pasti.",
                "steps": [
                    "Cari mutasi QRIS/transfer dengan nama pelanggan atau nomor order di catatan bank.",
                    "Tambahkan pembayaran manual di sidebar jika uang sudah masuk.",
                    "Jika produk tidak dikenal, tambahkan ke **Katalog** lalu refresh analisis.",
                ],
            }
        )

    if health_i < 80:
        drivers: list[str] = []
        steps: list[str] = []
        if coll_rate < 70:
            drivers.append(f"penagihan baru {coll_rate:.0f}% dari target")
            steps.extend(
                [
                    "Prioritaskan pesanan **Belum lunas** dan **Bayar sebagian** (lihat Rekonsiliasi).",
                    "Gunakan pengingat WhatsApp dari halaman Laporan.",
                ]
            )
        if net < 0:
            drivers.append(f"laba bersih negatif (Rp {net:,})")
            steps.extend(
                [
                    "Tinjau pengeluaran per kategori di Laporan — kurangi biaya non-penting hari ini.",
                    "Kejar pelunasan pesanan yang masih terbuka untuk menutup minus.",
                ]
            )
        if health_i < 60 and not steps:
            steps.append("Lengkapi data pembayaran dan pesanan lalu jalankan refresh analisis.")
        if not steps:
            steps.append(
                "Pertahankan penagihan di atas 80% dan laba bersih positif untuk naik ke skor Sangat baik."
            )
        items.append(
            {
                "category": "Skor kesehatan kas",
                "priority": "medium" if health_i >= 60 else "high",
                "title": f"Naikkan skor dari {health_i}/100",
                "why": " · ".join(drivers) if drivers else "Penagihan dan arus kas bisa ditingkatkan.",
                "steps": steps,
            }
        )

    for w in cfg.warnings or []:
        step = "Tidak perlu tindakan — ini hanya info mode demo."
        if "LLM" in w:
            step = "Opsional: tambahkan API key LLM di .env jika ingin pengingat lebih natural."
        elif "DOKU" in w:
            step = "Opsional: lengkapi kredensial DOKU di .env, atau tetap pakai mode Mock untuk demo."
        items.append(
            {
                "category": "Peringatan sistem",
                "priority": "low",
                "title": "Peringatan konfigurasi",
                "why": w,
                "steps": [step],
            }
        )

    for w in state.catalogue_warnings or []:
        items.append(
            {
                "category": "Peringatan katalog",
                "priority": "medium",
                "title": "Perbaiki katalog produk",
                "why": w,
                "steps": [
                    "Buka **Katalog** → perbaiki harga, alias, atau SKU duplikat.",
                    "Klik **Paksa refresh analisis** setelah menyimpan.",
                ],
            }
        )

    val = state.validation_report or {}
    for c in val.get("checks") or []:
        if c.get("passed"):
            continue
        name = str(c.get("check", "")).replace("_", " ").title()
        items.append(
            {
                "category": "Validasi laporan",
                "priority": "medium",
                "title": f"Lengkapi: {name}",
                "why": "Agen belum menghasilkan output ini pada analisis terakhir.",
                "steps": [
                    "Klik **Paksa refresh analisis** di sidebar.",
                    "Buka **Laporan** → Validasi untuk memastikan semua pemeriksaan lulus.",
                ],
            }
        )

    if not items and health_i >= 80 and not grouped:
        items.append(
            {
                "category": "Semua baik",
                "priority": "low",
                "title": "Tidak ada tindakan wajib",
                "why": f"Skor {health_i}/100 · penagihan {coll_rate:.0f}% · tidak ada isu pembayaran aktif.",
                "steps": [
                    "Lanjutkan monitoring harian di Beranda.",
                    "Unduh laporan di Beranda atau Laporan jika perlu dibagikan ke bank.",
                ],
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: priority_order.get(str(x.get("priority")), 9))
    return items


def recommendations_html(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    cards: list[str] = []
    border = {"high": "#b45309", "medium": "#006b47", "low": "#64748b"}
    for it in items:
        pri = str(it.get("priority") or "medium")
        color = border.get(pri, "#64748b")
        steps = it.get("steps") or []
        step_lis = "".join(f"<li>{_esc(s)}</li>" for s in steps)
        cards.append(
            f"""
<div class="wf-rec-card" style="border-left:4px solid {color};">
  <p class="wf-rec-cat">{_esc(it.get("category", ""))}</p>
  <p class="wf-rec-title">{_esc(it.get("title", ""))}</p>
  <p class="wf-rec-why">{_esc(it.get("why", ""))}</p>
  <ol class="wf-rec-steps">{step_lis}</ol>
</div>"""
        )
    return f'<div class="wf-rec-list">{"".join(cards)}</div>'


def collect_review_items(state: AgentState) -> dict[str, Any]:
    """Human-readable reasons and next steps when the agent needs merchant attention."""
    reasons: list[str] = []
    actions: list[str] = []
    severity = "info"

    for err in state.errors or []:
        if "max_steps" in err.lower():
            reasons.append(
                "Agen berhenti karena terlalu banyak langkah berulang (biasanya cek status link bayar)."
            )
            actions.append(
                "Klik **Paksa refresh analisis** di sidebar — perbaikan terbaru mencegah loop ini."
            )
            severity = "warn"
        else:
            reasons.append(err)
            severity = "warn"

    unknown: list[str] = []
    for o in state.parsed_orders or []:
        unknown.extend(o.get("unknown_products") or [])
    unknown = sorted({str(u) for u in unknown if u})
    if unknown:
        reasons.append(
            f"Produk tidak ada di katalog: {', '.join(unknown[:5])}"
            + ("…" if len(unknown) > 5 else "")
        )
        actions.append("Buka **Katalog** → tambahkan produk atau alias, lalu refresh analisis.")
        severity = "warn"

    unpaid = [
        r
        for r in (state.reconciliation_results or [])
        if str(r.get("status") or "").upper() in {"UNPAID", "PARTIALLY_PAID"}
    ]
    if unpaid:
        names: list[str] = []
        by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
        for r in unpaid[:4]:
            o = by_order.get(str(r.get("order_id")), {})
            names.append(str(o.get("customer_name") or r.get("order_id")))
        reasons.append(
            f"{len(unpaid)} pesanan belum lunas"
            + (f" ({', '.join(names)})" if names else "")
        )
        actions.append(
            "Di **WhatsApp Bot** → simulasikan bayar, atau di sidebar **Bayar Kevin (cocok)** untuk demo."
        )
        if severity != "warn":
            severity = "info"

    open_links = [
        pr
        for pr in (state.payment_requests or [])
        if str(pr.get("status") or "").upper()
        in {"PENDING", "AWAITING_PAYMENT", "UNKNOWN", ""}
    ]
    if open_links and not unpaid:
        reasons.append(f"{len(open_links)} link pembayaran masih menunggu pelanggan.")
        actions.append("Ini normal di demo — lanjutkan ke **Laporan** atau tunggu pembayaran masuk.")

    if state.final_status == "COMPLETE" and not reasons:
        return {"severity": "ok", "reasons": [], "actions": []}

    if not reasons and state.final_status == "NEEDS_REVIEW":
        reasons.append("Validasi laporan meminta pengecekan manual sebelum ekspor ke bank.")
        actions.append("Buka **Laporan** → tab validasi, atau unduh file di bawah setelah yakin.")
        severity = "warn"

    if not actions:
        actions.append("Klik **Paksa refresh analisis** di sidebar setelah memperbaiki data.")

    return {"severity": severity, "reasons": reasons, "actions": actions}


def review_guidance_html(state: AgentState) -> str:
    """Actionable panel when status is Perlu ditinjau."""
    if state.final_status not in {"NEEDS_REVIEW", "ERROR"} and not state.errors:
        return ""
    info = collect_review_items(state)
    if not info.get("reasons") and state.final_status != "NEEDS_REVIEW":
        return ""

    reason_lis = "".join(f"<li>{_esc(r)}</li>" for r in info.get("reasons") or [])
    action_lis = "".join(f"<li>{_esc(a)}</li>" for a in info.get("actions") or [])
    sev = info.get("severity") or "warn"
    border = "#f59e0b" if sev == "warn" else "#006b47"
    bg = "#fffbeb" if sev == "warn" else "#f0fdf6"
    return f"""
<div class="wf-review-panel" style="border-left:4px solid {border};background:{bg};border-radius:12px;padding:1rem 1.15rem;margin:0 0 1rem 0;">
  <p style="margin:0 0 0.5rem 0;font-weight:700;font-size:1rem;color:#1a211c;">Apa yang perlu Anda lakukan?</p>
  <p style="margin:0 0 0.65rem 0;font-size:0.88rem;color:#3e4942;line-height:1.5;">
    <strong>Perlu ditinjau</strong> bukan berarti sistem rusak — artinya ada data yang perlu Anda putuskan
    (produk tidak dikenal, belum bayar, atau agen berhenti lebih awal).
  </p>
  {"<p style='margin:0.35rem 0 0.2rem;font-weight:600;font-size:0.82rem;'>Yang perlu dicek:</p><ul style='margin:0.2rem 0 0.65rem 1.1rem;font-size:0.88rem;line-height:1.5;'>" + reason_lis + "</ul>" if reason_lis else ""}
  {"<p style='margin:0.35rem 0 0.2rem;font-weight:600;font-size:0.82rem;'>Langkah berikutnya:</p><ol style='margin:0.2rem 0 0;font-size:0.88rem;line-height:1.55;'>" + action_lis + "</ol>" if action_lis else ""}
</div>
"""


def _settlement_label(status: str, expected: int | None, paid: int) -> str | None:
    st = status.upper()
    if expected is None:
        return None
    if st in {"UNPAID", "PARTIALLY_PAID"}:
        remainder = max(0, expected - paid)
        if remainder <= 0:
            return None
        return f"Sisa Rp {remainder:,}"
    if st == "OVERPAID":
        excess = max(0, paid - expected)
        if excess <= 0:
            return None
        return f"Lebih Rp {excess:,}"
    return None


def reconciliation_rows_from_state(state: AgentState) -> list[dict[str, Any]]:
    by_order = {str(o.get("order_id")): o for o in (state.parsed_orders or [])}
    out: list[dict[str, Any]] = []
    for r in state.reconciliation_results or []:
        oid = str(r.get("order_id"))
        o = by_order.get(oid, {})
        customer = strip_internal_meta(str(o.get("customer_name") or oid))
        status = str(r.get("status") or "")
        expected_raw = o.get("amount_expected")
        expected = int(expected_raw) if isinstance(expected_raw, int) else None
        paid_raw = r.get("matched_amount")
        paid = int(paid_raw) if isinstance(paid_raw, (int, float)) else 0
        out.append(
            {
                "customer": customer,
                "amount_expected": expected,
                "amount_paid": paid,
                "status": status,
                "settlement": _settlement_label(status, expected, paid),
                "order_id": oid,
            }
        )
    return out


def trace_timeline_html(steps: list[ExecutionStep], max_items: int = 24) -> str:
    if not steps:
        return '<div class="wf-panel-body"><p class="wf-empty">Jejak eksekusi muncul setelah agen selesai berjalan.</p></div>'
    recent = steps[-max_items:]
    lines: list[str] = []
    cur_run: int | None = None
    status_word = {"ok": "Berhasil", "warn": "Peringatan", "error": "Gagal"}
    for t in recent:
        if cur_run != t.run_id:
            cur_run = t.run_id
            lines.append(f'<p class="wf-tl-run">Analisis ke-{t.run_id}</p>')
        color = {"ok": "#10b981", "warn": "#f59e0b", "error": "#ef4444"}.get(t.status, "#64748b")
        extra = _esc((t.output_summary or "")[:120])
        sw = status_word.get(t.status, t.status)
        lines.append(f"""
<div class="wf-tl-item">
  <div class="wf-tl-dot" style="background:{color};width:9px;height:9px;border-radius:50%;"></div>
  <div class="wf-tl-body">
    <p class="wf-tl-step">Langkah {t.step_number} · {sw}</p>
    <p class="wf-tl-tool-human">{_esc(human_tool(t.tool_called))}</p>
    <p class="wf-tl-tool-code">{_esc(t.tool_called)}</p>
    <p class="wf-tl-out">{extra}</p>
  </div>
</div>""")
    html_block = "".join(lines)
    return f'<div class="wf-panel-body" style="padding:1rem 1rem 1.1rem;"><div class="wf-timeline">{html_block}</div></div>'


EXPORT_LABELS: dict[str, tuple[str, str]] = {
    "daily_report.md": ("Laporan harian", "assessment"),
    "payment_reminders.md": ("Pengingat pembayaran", "notifications_active"),
    "financing_readiness.md": ("Kesiapan pembiayaan", "account_balance"),
    "validation_report.md": ("Laporan validasi", "fact_check"),
    "reconciliation_result.csv": ("Rekonsiliasi (CSV)", "table_chart"),
    "execution_trace.csv": ("Jejak agen (CSV)", "timeline"),
}
