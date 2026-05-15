# Demo Script

**OpenClaw2026_MuhammadAldoFahrezy_WarungFlow** (max 2 minutes)

## 0:00–0:15 Problem

"Many Indonesian UMKM sellers take orders via WhatsApp and accept payments via QRIS, but reconciling them at the end of the day is a manual nightmare. Unpaid orders slip through the cracks."

## 0:15–0:30 Solution

"Meet WarungFlow — not a chatbot, but an autonomous finance operations agent. One click runs the full back-office workflow."

## 0:30–1:20 Live demo

1. `streamlit run app.py`
2. Sidebar: **Mock Mode** (no API keys required)
3. Click **Run WarungFlow Agent**
4. Show execution trace (18+ tool steps)
5. Show reconciliation: PAID, UNPAID, PARTIALLY_PAID, OVERPAID
6. Show Bahasa payment reminders and health score
7. Download exports from Reports tab

## 1:20–1:45 Architecture

- State-driven orchestrator (`decide_next_action`)
- `workspace/AGENTS.md`, `HEARTBEAT.md`, `TOOLS.md` for OpenClaw
- Deterministic reconciliation + optional DOKU sandbox

## 1:45–2:00 Impact

"WarungFlow gives warung owners daily cashflow clarity and payment follow-ups — a step toward financing readiness for Indonesian UMKM."

**Video title:** `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`
