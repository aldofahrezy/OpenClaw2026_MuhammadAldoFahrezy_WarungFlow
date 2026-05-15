# Devpost Submission
**OpenClaw2026_[TEAM_NAME]_WarungFlow**

## Inspiration
Indonesian UMKM and warung owners rely heavily on informal WhatsApp messaging and scattered payment methods (QRIS, bank transfers, cash). Checking who has paid and calculating daily profit is a massive manual chore. We wanted to build an AI that does this tedious back-office work autonomously.

## What it does
WarungFlow is an autonomous finance operations agent. Given messy WhatsApp orders, expense records, and QRIS-style transaction logs, it enters an autonomous loop to:
1. Parse and extract structured data from informal chat messages.
2. Reconcile expected payments against actual bank/QRIS transactions using fuzzy logic.
3. Flag unpaid, partially paid, or suspicious orders.
4. Optionally use DOKU Sandbox tools to generate payment links for unpaid orders.
5. Calculate cashflow, net profit, and assign a business health score.
6. Generate actionable outputs like payment reminders and financing-readiness reports.

## How we built it
We built it strictly as a multi-agent system rather than a conversational chatbot. 
- **Tech Stack**: Python, Streamlit, Pandas.
- **Agent Architecture**: A state-driven Orchestrator Agent runs a `while` loop, continuously evaluating an `AgentState` object to determine the next required tool call. It coordinates specialized agents (Data Cleaner, Reconciliation, Analyst, Advisor, Validator).
- **Payment Use Case**: We integrated the DOKU Sandbox API to dynamically generate payment links when the agent identifies an unpaid order. It elegantly falls back to a deterministic Mock Mode if credentials are missing.

## Challenges we ran into
Building a robust reconciliation engine that doesn't blindly match the wrong payment to the wrong order. We had to implement a global confidence-sorted matching algorithm rather than a naive greedy loop. Handling the ambiguity of Indonesian WhatsApp "kasbon" culture was also a unique challenge.

## Accomplishments that we're proud of
We successfully built a true agentic loop. The user only clicks "Run Agent" once, and the Orchestrator autonomously plans and executes up to 20 tool calls, logging its entire execution trace clearly on the dashboard. The system works completely end-to-end.

## What we learned
We learned that deterministic tools are far better for critical financial logic (like exact matching and arithmetic) than LLMs. The best architecture uses deterministic Python functions for the heavy lifting and LLMs for parsing messy text and generating empathetic natural language.

## What's next for WarungFlow
Direct integration with the WhatsApp Business API to ingest orders in real-time, live syncing with DOKU webhooks, and creating standardized report templates for micro-financing applications at Indonesian banks.

## AI tools/models used
- Used Gemini for code generation, structuring the agent loop, and generating dummy data.
