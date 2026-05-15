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

WarungFlow is an autonomous finance operations agent. Given messy WhatsApp orders, expense records, and QRIS-style transaction logs, it:

1. Parses and structures informal chat orders (deterministic + catalog pricing).
2. Reconciles payments with fuzzy Indonesian name matching and order-ID priority in bank notes.
3. Flags UNPAID, PARTIALLY_PAID, OVERPAID, and NEEDS_REVIEW orders.
4. Optionally creates DOKU Sandbox payment requests (mock fallback without credentials).
5. Calculates cashflow, net profit, and a health score.
6. Generates Bahasa Indonesia payment reminders and financing-readiness text.
7. Validates and exports markdown/CSV reports.

## How we built it

- **Not a chatbot:** state-driven orchestrator (`decide_next_action`) runs up to 20 tool steps per click.
- **Memory:** `AgentState` + `execution_trace` visible in Streamlit.
- **Tools:** 18 real Python handlers (load, parse, reconcile, cashflow, advise, validate, export).
- **Workspace:** `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`, `MEMORY.md` for OpenClaw/QwenPaw.
- **Payment:** QRIS CSV reconciliation + `MockPaymentProvider` / optional `DokuSandboxProvider`.

## Challenges

- Preventing wrong payment-to-order matches ("Joko paradox") when bank notes mention multiple names but include an `order_id`.
- Indonesian honorifics and bank display names vs WhatsApp customer names.
- Keeping financial logic deterministic while still demonstrating agentic autonomy.

## Accomplishments

- One-button autonomous run from sample data to exported reports without API keys.
- Full execution trace for judges (tool name, decision, I/O summary per step).
- End-to-end demo merchant Warung Bu Sari with 10 WhatsApp orders.

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

Public repository with README install instructions. Judges: see README → smoke test → Streamlit → **Run WarungFlow Agent**.
