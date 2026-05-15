# Demo Script

**OpenClaw2026_MuhammadAldoFahrezy_WarungFlow** (max 2 minutes)

## 0:00–0:15 Problem

"Many Indonesian UMKM sellers take orders via WhatsApp and accept payments via QRIS, but reconciling them at the end of the day is a manual nightmare. Unpaid orders slip through the cracks."

## 0:15–0:30 Solution

"Meet WarungFlow — not a chatbot, but an autonomous finance operations agent. Open the app: it loads sample Warung Bu Sari data and runs the first analysis automatically. Six pages: Beranda, Katalog, WhatsApp Bot, Jejak agen, Rekonsiliasi, and Laporan."

## 0:30–1:25 Live reactive demo

1. Open http://43.157.208.68:8501 (or `streamlit run app.py`).
2. **Beranda** loads after the first auto-run — no manual start click.
3. Show **Langkah yang disarankan** (unpaid/partial/overpaid guidance).
4. **Jejak agen** — execution trace grouped by run.
5. Sidebar **Live Data Sandbox** → **Kevin unpaid order** (or paste WhatsApp line).
6. Auto-refresh runs → Kevin **UNPAID**; reconciliation shows **Sisa Rp …**.
7. **Kevin matching payment** (Kevin, Rp 44.000, QRIS, note with order id).
8. Auto-refresh → Kevin **PAID**; KPIs update.
9. **Add expense shock** → net profit and health score update.
10. **Katalog** — quick product edit or CSV import.
11. **WhatsApp Bot** — send a mock customer message; show new order in table.
12. **Laporan** — charts and export downloads.
13. Mention mock payment mode: QRIS reconciliation, partial/overpaid detection, optional DOKU adapter.

## 1:25–1:45 Architecture

- State-driven orchestrator (`decide_next_action`, max 24 steps)
- 20 tools + execution trace with `run_id`
- Product catalogue + bot event sync
- Input hashing + idempotent sandbox inserts
- `PaymentProvider` abstraction (mock + DOKU sandbox)
- Deterministic reconciliation; LLM optional for reminders

## 1:45–2:00 Impact

"From messy notes to bankable reports, autonomously — daily cashflow clarity and payment follow-ups for Indonesian UMKM."

**Video title:** `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`

**Backup controls:** **Force Refresh Analysis** and **Reset Demo** in the sidebar.
