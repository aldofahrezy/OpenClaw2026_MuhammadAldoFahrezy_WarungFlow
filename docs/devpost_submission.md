# Devpost Submission

**Team:** OpenClaw2026_MuhammadAldoFahrezy  
**Project:** OpenClaw2026_MuhammadAldoFahrezy_WarungFlow  
**Track:** Best Payment Use Case  
**Devpost:** https://openclawagenthon.devpost.com/

## Tagline

From messy notes to bankable reports, autonomously.

## Inspiration

Indonesian UMKM and warung owners rely on informal WhatsApp messaging and scattered payment methods (QRIS, bank transfers, cash, DOKU). Checking who has paid and calculating daily profit is a massive manual chore. We built an agent that does this back-office work autonomously.

## What it does

WarungFlow is an autonomous finance operations agent. Given messy WhatsApp orders, a product catalogue, expense records, and QRIS-style transaction logs, it:

1. Parses and structures informal chat orders (deterministic + catalogue pricing).
2. Reconciles payments with fuzzy Indonesian name matching and order-ID priority in bank notes.
3. Flags UNPAID, PARTIALLY_PAID, OVERPAID, and NEEDS_REVIEW — with **Sisa Rp …** / **Lebih Rp …** in the dashboard.
4. Supports **Mock payments** (no API keys) and **DOKU Sandbox** (hosted checkout + Check Status API sync).
5. Calculates cashflow, net profit, and a health score.
6. Generates Bahasa Indonesia payment reminders and financing-readiness text.
7. Validates and exports markdown/CSV reports.

**Plus:** product catalogue CRUD, WhatsApp bot simulation (rooms per phone), and **Langkah yang disarankan** on Beranda, Rekonsiliasi, and Laporan.

## How we built it

- **Not a chatbot:** state-driven orchestrator (`decide_next_action`) runs up to **24** tool steps per run; auto-runs on first load and on input-hash changes.
- **Memory:** `AgentState` + `execution_trace` (with `run_id`) on **Jejak agen**.
- **Tools:** 20 registered handlers in `TOOL_REGISTRY`.
- **Simulasi page:** WhatsApp chat, QRIS payments, expenses, payment mode selector, auto-refresh.
- **Payment integration:** `tools/doku_sandbox_provider.py` (Checkout + Check Status), `tools/doku_payment_sync.py`, Midtrans-style simulator at `?doku_pay=`.
- **UI:** Streamlit with merchant-friendly tables and recommendations (`build_action_recommendations`).
- **Bot:** FastAPI `bot_server.py` + mock WhatsApp provider; in-process demo on Simulasi.
- **Workspace:** `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`, `MEMORY.md` for OpenClaw/QwenPaw.

## Challenges

- Syncing real DOKU sandbox payments back to WarungFlow without a public webhook URL on Streamlit-only deploy → solved with Check Status API poll on simulator return.
- Preventing wrong payment-to-order matches when bank notes mention multiple names but include an `order_id`.
- Indonesian honorifics and bank display names vs WhatsApp customer names.
- Session persistence without overwriting UI payment mode on every refresh.

## Accomplishments

- End-to-end demo merchant Warung Bu Sari with reactive UNPAID→PAID flows.
- Mock mode runs without any API keys; DOKU mode demonstrates real payment gateway integration.
- Full execution trace for judges; live deployment http://43.157.208.68:8501
- Documented judge paths: [judge_testing_guide.md](judge_testing_guide.md)

## What we learned

Deterministic tools should own money matching and arithmetic; the agent loop should own planning, sequencing, and validation. Payment gateways need explicit status sync — paying on a hosted page alone is not enough for back-office reconciliation.

## What's next

WhatsApp Business API ingestion, production DOKU HTTP notifications, POS hooks, and bank-ready financing packets.

## AI tools/models used

- Cursor IDE agent
- Google Gemini / Groq (optional LLM for reminders when `LLM_MODE=live`)

## Autonomous agent proof

| Requirement | Implementation |
|-------------|----------------|
| Tool calls | `TOOL_REGISTRY` in `agents/tool_handlers.py` |
| Autonomous loop | `run_agent_stream()` in `agents/orchestrator.py` |
| Memory/state | `state.py` → `AgentState` |
| Validation | `VALIDATE_OUTPUTS` tool |
| Runnable locally | `python smoke_test.py` + `streamlit run app.py` |

## GitHub

https://github.com/aldofahrezy/Warung-Flow

**Judges:** `smoke_test.py -v` → Streamlit → [judge_testing_guide.md](judge_testing_guide.md) (Mock ~8 min, DOKU ~12 min).

## Live deployment

| Option | URL |
|--------|-----|
| VPS (current) | http://43.157.208.68:8501 |
| Streamlit Cloud (optional) | https://warungflow-muhammadaldofahrezy.streamlit.app |

See [DEPLOY.md](../DEPLOY.md).
