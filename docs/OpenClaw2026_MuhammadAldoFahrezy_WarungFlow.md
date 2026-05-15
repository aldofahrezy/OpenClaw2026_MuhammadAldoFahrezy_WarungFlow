# OpenClaw2026_MuhammadAldoFahrezy_WarungFlow

**Team:** Muhammad Aldo Fahrezy · **Project:** WarungFlow

---

## Slide 1 — Problem Statement

- Indonesian UMKM and warung owners take orders via **WhatsApp**, accept **QRIS / transfer / cash**, and track expenses manually.
- At close of day they often cannot answer: who paid, who owes, partial payments, or net profit.
- Matching chat orders to bank mutations is slow, error-prone, and blocks financing conversations.

---

## Slide 2 — Solution Overview

- **WarungFlow** — autonomous finance operations agent for Indonesian UMKM.
- Tagline: *From messy notes to bankable reports, autonomously.*
- Parses WhatsApp orders, reconciles QRIS-style payments, flags issues with **Sisa Rp …** / **Lebih Rp …**, scores cashflow, generates reminders and financing-readiness summaries.
- **Not a chatbot:** auto-runs a full tool loop on open; **Langkah yang disarankan** guides next actions.

---

## Slide 3 — AI Agent Workflow / Architecture

```mermaid
flowchart TD
    A[Messy WhatsApp Orders] --> B[Parse + Catalogue]
    C[QRIS / Mock Payments] --> D[Reconciliation Agent]
    B --> D
  W[WhatsApp Bot Events] --> B
    D --> E[Cashflow Analyst]
    E --> F[Advisor Agent]
    F --> G[Validator Agent]
    G --> H[Exported Reports + Streamlit UI]
```

- **Orchestrator:** state-driven `decide_next_action()` loop (max **24** steps).
- **Memory:** `AgentState` + `execution_trace` with `run_id`.
- **Tools:** 20 registered handlers (load, catalogue, bot sync, reconcile, cashflow, validate, export).
- **Payment:** Mock provider by default; optional DOKU Sandbox adapter.

---

## Slide 4 — Key Features & Tech Stack

| Feature | Benefit |
|---------|---------|
| QRIS-style reconciliation | Fuzzy names + order-ID priority |
| Payment issues | UNPAID, PARTIAL, OVERPAID + sisa/lebih bayar |
| Recommendations | Langkah yang disarankan on key pages |
| Product catalogue | CRUD + CSV + pricing for orders |
| WhatsApp bot | Mock order intake for demo |
| Health score | 0–100 cashflow signal |
| Mock mode | Runs without API keys |

**Stack:** Python 3.11+, Streamlit, pandas, rapidfuzz, Altair, FastAPI (bot), python-dotenv.

**Live:** http://43.157.208.68:8501

---

## Slide 5 — Future Development / Impact

- WhatsApp Business API for live order intake.
- Live QRIS / DOKU webhook sync.
- POS integration and bank-ready ledger exports.
- **Impact:** financial inclusion and daily clarity for millions of UMKM.

---

*Export to PDF: `pandoc docs/OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.md -o docs/OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf`*
