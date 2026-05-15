# Demo Script

**OpenClaw2026_MuhammadAldoFahrezy_WarungFlow** (max 2 minutes)

Full judge flows: [judge_testing_guide.md](judge_testing_guide.md)

## 0:00–0:15 Problem

"Many Indonesian UMKM sellers take orders via WhatsApp and accept payments via QRIS, but reconciling them at the end of the day is a manual nightmare. Unpaid orders slip through the cracks."

## 0:15–0:30 Solution

"Meet WarungFlow — not a chatbot, but an autonomous finance operations agent. Open the app: sample Warung Bu Sari data loads and the first analysis runs automatically. Six pages: Beranda, Simulasi, Katalog, Jejak agen, Rekonsiliasi, and Laporan."

## 0:30–1:25 Live reactive demo

1. Open http://43.157.208.68:8501 (or `streamlit run app.py`).
2. **Beranda** — KPIs and **Langkah yang disarankan** after auto-run.
3. **Simulasi** → **Mode pembayaran: Mock**.
4. **Pesanan WhatsApp** — send `nasi goreng 2 - Kevin`; show chat room and **Pesanan dari bot** (Menunggu bayar).
5. Click `mock_pay` link or **Tandai sudah bayar** → status **Lunas**; Beranda updates.
6. (Optional, 15s) Switch **DOKU Sandbox** → new order → open staging checkout → **Cek status pembayaran DOKU** on simulator page.
7. **Jejak agen** — grouped execution trace.
8. **Katalog** — quick price edit.
9. **Laporan** — charts and export downloads.

## 1:25–1:45 Architecture

- State-driven orchestrator (`decide_next_action`, max 24 steps)
- 20 tools + execution trace with `run_id`
- Product catalogue + bot events (`runtime/*.jsonl`)
- Payment: Mock deep links + DOKU Checkout API + Check Status poll
- Deterministic reconciliation; LLM optional for reminders

## 1:45–2:00 Impact

"From messy notes to bankable reports, autonomously — daily cashflow clarity and payment follow-ups for Indonesian UMKM."

**Video title:** `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`

**Backup:** **Paksa refresh analisis** on Simulasi; **Reset riwayat demo** in sidebar.
