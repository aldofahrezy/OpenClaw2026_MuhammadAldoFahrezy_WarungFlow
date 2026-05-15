# Devpost Submission

**Team:** OpenClaw2026_MuhammadAldoFahrezy  
**Project:** OpenClaw2026_MuhammadAldoFahrezy_WarungFlow  
**Track:** Best Payment Use Case  
**Devpost:** https://openclawagenthon.devpost.com/

## Tagline

From messy notes to bankable reports, autonomously.

## Inspiration

Indonesian UMKM and warung owners rely on informal WhatsApp messaging and scattered payment methods (QRIS, bank transfers, cash). Checking who has paid and calculating daily profit is a massive manual chore. We built an agent that does this back-office work autonomously.

## What it does

WarungFlow is an autonomous finance operations agent. Given messy WhatsApp orders, a product catalogue, expense records, and QRIS-style transaction logs, it:

1. Parses and structures informal chat orders (deterministic + catalogue pricing).
2. Reconciles payments with fuzzy Indonesian name matching and order-ID priority in bank notes.
3. Flags UNPAID, PARTIALLY_PAID, OVERPAID, and NEEDS_REVIEW — with **Sisa Rp …** / **Lebih Rp …** in the dashboard.
4. Creates mock or DOKU Sandbox payment requests (mock fallback without credentials).
5. Calculates cashflow, net profit, and a health score.
6. Generates Bahasa Indonesia payment reminders and financing-readiness text.
7. Validates and exports markdown/CSV reports.

**Plus:** product catalogue CRUD, mock WhatsApp bot for order intake, and **Langkah yang disarankan** action recommendations on Beranda, Rekonsiliasi, and Laporan.

## How we built it

- **Not a chatbot:** state-driven orchestrator (`decide_next_action`) runs up to **24** tool steps per run; auto-runs on first load and on input-hash changes.
- **Memory:** `AgentState` + `execution_trace` (with `run_id`) on **Jejak agen**.
- **Tools:** 20 registered handlers in `TOOL_REGISTRY` (load, catalogue, bot sync, parse, reconcile, cashflow, advise, validate, export).
- **Live Data Sandbox:** add orders, payments, expenses with idempotent fingerprints.
- **UI:** Streamlit pages with bordered section cards, human-readable tables, recommendations engine (`build_action_recommendations`).
- **Bot:** FastAPI `bot_server.py` + mock WhatsApp provider; dashboard page hides tokens/URLs on main view.
- **Workspace:** `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`, `MEMORY.md` for OpenClaw/QwenPaw.
- **Payment:** QRIS-style reconciliation in Mock Mode; `PaymentProvider` adapter for mock + optional DOKU Sandbox.

## Challenges

- Preventing wrong payment-to-order matches when bank notes mention multiple names but include an `order_id`.
- Indonesian honorifics and bank display names vs WhatsApp customer names.
- Avoiding infinite `CHECK_PAYMENT_STATUS` loops when reusing payment request state across runs.
- Keeping financial logic deterministic while demonstrating agentic autonomy and a merchant-friendly UI.

## Accomplishments

- Auto-run from sample data to exported reports without API keys; reactive sandbox for Kevin UNPAID→PAID and expense shocks.
- Full execution trace for judges (tool name, decision, I/O summary per step).
- End-to-end demo merchant Warung Bu Sari with 10 WhatsApp orders, catalogue, and mock bot flow.
- Live deployment: http://43.157.208.68:8501

## What we learned

Deterministic tools should own money matching and arithmetic; the agent loop should own planning, sequencing, and validation. LLMs are optional enrichments, not the critical path.

## What's next

WhatsApp Business API ingestion, live DOKU webhooks, POS hooks, and bank-ready financing packets.

## AI tools/models used

- Cursor IDE agent
- Google Gemini (development assistance for structure and sample content)

## Autonomous agent proof

| Requirement | Implementation |
|-------------|----------------|
| Tool calls | `TOOL_REGISTRY` in `agents/tool_handlers.py` |
| Autonomous loop | `run_agent_stream()` in `agents/orchestrator.py` |
| Memory/state | `state.py` → `AgentState` |
| Validation | `VALIDATE_OUTPUTS` tool |
| Runnable locally | `python smoke_test.py` + `streamlit run app.py` |

## GitHub

https://github.com/aldofahrezy/Warung-Flow — README install instructions. Judges: smoke test → Streamlit (auto-loads sample data) → Live Data Sandbox → Katalog / WhatsApp Bot pages.

## Live deployment

| Option | URL |
|--------|-----|
| VPS (current) | http://43.157.208.68:8501 |
| Streamlit Cloud (optional) | https://warungflow-muhammadaldofahrezy.streamlit.app |

Paste a live URL in Devpost **Live Deployment Link (Optional)** for bonus points. See `DEPLOY.md`.
