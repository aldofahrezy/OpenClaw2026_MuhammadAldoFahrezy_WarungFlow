# Pitch Deck Outline
**OpenClaw2026_[TEAM_NAME]_WarungFlow**

## Slide 1: Problem Statement
- Indonesian UMKM use WhatsApp, QRIS, cash, and manual notes.
- Daily cashflow is hard to understand because orders and payments exist in separate, unlinked silos.
- Unpaid orders are easy to miss, resulting in lost revenue.

## Slide 2: Solution Overview
- **WarungFlow** is an autonomous finance operations agent.
- From messy notes to bankable reports, autonomously.
- Cleans WhatsApp orders, reconciles payments deterministically, calculates cashflow, and generates actions.

## Slide 3: AI Agent Workflow / Architecture
- **Orchestrator**: Controls the autonomous loop (while not done).
- **Tool calls**: True "tangan" via function calling.
- **Autonomous loop**: Perceives state → Acts → Evaluates.
- **DOKU Sandbox/MCP**: Optional payment tools to create and check payment links.
- **Validator**: Ensures final outputs are reliable.

## Slide 4: Key Features & Tech Stack
- **Features**: QRIS-style reconciliation, payment issue detection, cashflow health score, payment reminders, financing-readiness summary.
- **Tech Stack**: Streamlit, Python, pandas, pydantic, DOKU adapter.
- Deterministic-first fallback means it always works, even offline.

## Slide 5: Future Development / Impact
- **WhatsApp Business Integration**: Direct message intake.
- **Live QRIS/DOKU Transaction Sync**: Real-time matching.
- **Micro-financing readiness**: Providing banks with automated, reliable ledger data.
- **Impact**: Financial inclusion and operational clarity for millions of UMKM.
